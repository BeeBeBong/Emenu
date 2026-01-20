import os
import json
from datetime import timedelta
from django.utils import timezone
from django.conf import settings
from django.shortcuts import render, get_object_or_404
from django.contrib.auth import authenticate
from django.db.models import Sum
from django.db.models.functions import Coalesce
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.models import User

from rest_framework import viewsets, status
from rest_framework.decorators import api_view, permission_classes, authentication_classes
from rest_framework.permissions import AllowAny, IsAdminUser
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken

# Import Models & Serializers
from .models import Category, Item, Table, Order, OrderItem, Revenue, Booking, Notification
from .serializers import (
    CategorySerializer, ItemSerializer, TableSerializer,
    OrderSerializer, OrderItemSerializer, RevenueSerializer, 
    LoginSerializer, NotificationSerializer, UserSerializer
)

# ==========================================
# 1. CORE VIEWS (Template & Auth)
# ==========================================
def get_Emenu(request):
    """Render trang chủ React"""
    return render(request, 'Emenu.html')

@api_view(['POST'])
@permission_classes([AllowAny])
@authentication_classes([]) # Tắt check token để login được
@csrf_exempt
def login(request):
    """Đăng nhập lấy Token"""
    serializer = LoginSerializer(data=request.data)
    if serializer.is_valid():
        user = authenticate(
            username=serializer.validated_data['username'],
            password=serializer.validated_data['password']
        )
        if user:
            refresh = RefreshToken.for_user(user)
            role = 'ADMIN' if user.is_superuser else ('STAFF' if user.is_staff else 'CUSTOMER')
            name = user.first_name if user.first_name else user.username
            
            return Response({
                'status': 'success',
                'data': {
                    'token': str(refresh.access_token),
                    'userId': user.id,
                    'fullName': name,
                    'role': role
                }
            })
        return Response({'message': 'Sai tài khoản hoặc mật khẩu'}, status=401)
    return Response(serializer.errors, status=400)

@api_view(['GET'])
def get_current_user(request):
    """Lấy thông tin user hiện tại"""
    user = request.user
    if user.is_authenticated:
        role = 'ADMIN' if user.is_superuser else ('STAFF' if user.is_staff else 'CUSTOMER')
        return Response({
            'status': 'success',
            'data': {
                'userId': user.id,
                'fullName': user.first_name or user.username,
                'role': role,
                'email': user.email
            }
        })
    return Response({'message': 'Chưa đăng nhập'}, status=401)


# ==========================================
# 2. MENU & TABLE APIs
# ==========================================
class CategoryViewSet(viewsets.ModelViewSet):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer

class ItemViewSet(viewsets.ModelViewSet):
    queryset = Item.objects.all()
    serializer_class = ItemSerializer
    def get_serializer_context(self):
        return {'request': self.request}

class TableViewSet(viewsets.ModelViewSet):
    queryset = Table.objects.all().order_by('id')
    serializer_class = TableSerializer

@api_view(['GET'])
def get_menu(request):
    items = Item.objects.all()
    serializer = ItemSerializer(items, many=True, context={'request': request})
    return Response(serializer.data)

@api_view(['GET'])
def get_menu_by_category(request, id_danhmuc):
    items = Item.objects.filter(category_id=id_danhmuc)
    serializer = ItemSerializer(items, many=True, context={'request': request})
    return Response(serializer.data)

@api_view(['GET'])
def get_menu_data(request):
    """API lấy dữ liệu JSON (Backup)"""
    try:
        json_path = os.path.join(settings.BASE_DIR, 'menu.json')
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        categories = sorted(list(set(i['phan_loai'] for i in data)))
        products = [{
            'id': idx,
            'name': item['ten_mon'],
            'price': item['gia'],
            'img': item.get('img', ''),
            'category': item['phan_loai']
        } for idx, item in enumerate(data, 1)]
        
        return Response({'categories': categories, 'products': products})
    except Exception as e:
        return Response({'error': str(e)}, status=500)


# ==========================================
# 3. ORDER LOGIC
# ==========================================
class OrderViewSet(viewsets.ModelViewSet):
    queryset = Order.objects.all()
    serializer_class = OrderSerializer
    def create(self, request, *args, **kwargs):
        return create_order(request)

@api_view(['POST'])
def create_order(request):
    try:
        data = request.data
        table_id = data.get('table_id') or data.get('tableId')
        items_data = data.get('items')

        if not table_id or not items_data:
            return Response({'error': 'Thiếu tableId hoặc items'}, status=400)

        table = get_object_or_404(Table, id=table_id)
        order = Order.objects.filter(table=table).exclude(status__in=['paid', 'cancelled']).last()

        if not order:
            order = Order.objects.create(table=table, status='pending', total=0)
        
        if table.status == 'available':
            table.status = 'occupied'
            table.save()

        current_total = order.total
        
        for i in items_data:
            pid = i.get('id') or i.get('itemId') or i.get('product_id')
            qty = int(i.get('quantity', 1))
            note = i.get('note', '')

            if not pid: continue
            
            try:
                item = Item.objects.get(id=pid)
                exist = OrderItem.objects.filter(order=order, item=item, is_served=False).first()
                
                if exist:
                    exist.quantity += qty
                    if note: exist.note = note
                    exist.save()
                else:
                    OrderItem.objects.create(
                        order=order, 
                        item=item, 
                        quantity=qty, 
                        note=note, 
                        is_served=False
                    )
                current_total += (item.price * qty)
                
            except Item.DoesNotExist:
                continue

        order.total = current_total
        order.save()
        return Response(OrderSerializer(order, context={'request': request}).data, status=201)

    except Exception as e:
        return Response({'error': str(e)}, status=500)

@api_view(['GET'])
def get_order_by_table(request, table_id):
    try:
        order = Order.objects.filter(table_id=table_id).exclude(status__in=['paid', 'cancelled']).last()
        if not order: return Response([])
        return Response(OrderSerializer(order, context={'request': request}).data)
    except Exception as e:
        return Response({'error': str(e)}, status=500)


# ==========================================
# 4. ADMIN ACTIONS (Checkout, Booking, Noti)
# ==========================================
@api_view(['POST'])
@permission_classes([IsAdminUser])
def checkout(request, table_id):
    try:
        table = get_object_or_404(Table, id=table_id)
        order = Order.objects.filter(table=table).exclude(status__in=['paid', 'cancelled', 'served']).last()
        if not order:
             order = Order.objects.filter(table=table).exclude(status='paid').last()
        
        if not order:
             return Response({'error': 'Không tìm thấy đơn hàng để thanh toán'}, status=400)

        # Lưu doanh thu
        method = request.data.get('payment_method', 'cash')
        Revenue.objects.create(order=order, method=method, amount=order.total)

        # Update đơn & bàn
        order.status = 'paid'
        order.save()
        table.status = 'available'
        table.save()

        # Xóa thông báo
        Notification.objects.filter(table=table).delete()

        return Response({'message': 'Thanh toán thành công'})
    except Exception as e:
        return Response({'error': str(e)}, status=500)

@api_view(['POST'])
@permission_classes([IsAdminUser])
def cancel_order(request):
    try:
        table_id = request.data.get('table_id')
        if not table_id: 
            return Response({'error': 'Thiếu table_id'}, status=400)

        deleted_count, _ = Order.objects.filter(table_id=table_id).exclude(status='paid').delete()

        Table.objects.filter(id=table_id).update(
            status='available', reserved_at=None, expires_at=None
        )
        Notification.objects.filter(table_id=table_id).delete()

        if deleted_count > 0:
            return Response({'message': 'Đã hủy đơn và dọn bàn'})
        else:
            return Response({'message': 'Đã dọn bàn về trạng thái trống'})
    except Exception as e:
        return Response({'error': str(e)}, status=500)

@api_view(['POST'])
def reserve_table(request, id_ban):
    table = get_object_or_404(Table, id=id_ban)
    if table.status != 'available':
        return Response({'error': 'Bàn không trống'}, status=400)
    
    table.status = 'reserved'
    table.reserved_at = timezone.now()
    table.save()
    return Response(TableSerializer(table).data)

@api_view(['POST'])
def request_payment(request):
    try:
        table_id = request.data.get('table_id')
        table = Table.objects.get(id=table_id)
        
        Notification.objects.create(
            table=table, message=f"{table.number} yêu cầu thanh toán", is_read=False
        )
        return Response({'success': True, 'message': 'Đã gửi yêu cầu!'})
    except Exception as e:
        return Response({'error': str(e)}, status=500)

@api_view(['GET'])
def get_notifications(request):
    notifs = Notification.objects.all().order_by('-created_at')
    serializer = NotificationSerializer(notifs, many=True)
    return Response(serializer.data)


# ==========================================
# 5. DASHBOARD STATS & BOOKING
# ==========================================
@api_view(['GET'])
def get_dashboard_stats(request):
    try:
        # 1. Xử lý Time Range
        range_type = request.query_params.get('range', 'today')
        today = timezone.now().date()
        start_date = today
        filter_kwargs = {}

        if range_type == 'yesterday':
            start_date = today - timedelta(days=1)
            filter_kwargs = {'paid_at__date': start_date}
        elif range_type == 'month':
            start_date = today.replace(day=1)
            filter_kwargs = {'paid_at__date__gte': start_date}
        elif range_type == 'year':
            start_date = today.replace(month=1, day=1)
            filter_kwargs = {'paid_at__date__gte': start_date}
        else: # 'today'
            filter_kwargs = {'paid_at__date': today}

        # 2. Tính toán Doanh thu
        revenues = Revenue.objects.filter(**filter_kwargs)
        total_rev = revenues.aggregate(t=Coalesce(Sum('amount'), 0))['t']
        cash_rev = revenues.filter(method='cash').aggregate(t=Coalesce(Sum('amount'), 0))['t']
        transfer_rev = revenues.filter(method='transfer').aggregate(t=Coalesce(Sum('amount'), 0))['t']
        total_orders = revenues.count()

        # 3. Best Sellers (FIX LỖI ẢNH TẠI ĐÂY)
        top_items = OrderItem.objects.values('item').annotate(total=Sum('quantity')).order_by('-total')[:5]
        best_sellers_data = []
        
        for t in top_items:
            try:
                item = Item.objects.get(pk=t['item'])
                
                # --- 🔥 LOGIC XỬ LÝ ẢNH MỚI ---
                image_url = ""
                # ƯU TIÊN 1: Lấy từ file ảnh thật (FileField)
                if item.image:
                    image_url = request.build_absolute_uri(item.image.url)
                
                # ƯU TIÊN 2: Nếu không có file thật, mới xét đến trường text cũ (img)
                elif item.img:
                    if str(item.img).startswith('http'):
                        image_url = item.img
                    else:
                        # Tự động ghép domain vào nếu là link tương đối
                        # Xử lý trường hợp thừa/thiếu dấu /
                        clean_path = str(item.img).strip('/')
                        image_url = request.build_absolute_uri(f'/media/{clean_path}')
                
                # ƯU TIÊN 3: Ảnh mặc định
                else:
                    image_url = "https://via.placeholder.com/150?text=No+Image"

                best_sellers_data.append({
                    'id': item.id,
                    'name': item.name,
                    'price': item.price,
                    'img': image_url,  # Frontend luôn dùng key 'img'
                    'sold_count': t['total']
                })
                # -----------------------------
                
            except Item.DoesNotExist:
                continue

        # 4. Bookings
        recent_bookings = Booking.objects.filter(status='pending').order_by('-created_at')[:10]
        bookings_data = [{
            "id": b.id,
            "customer_name": b.customer_name,
            "phone": b.customer_phone,
            "time": b.booking_time,
            "guests": b.guest_count,
            "status": b.status
        } for b in recent_bookings]

        return Response({
            "revenue": {
                "total": total_rev,
                "cash": cash_rev,
                "transfer": transfer_rev,
                "orders": total_orders
            },
            "best_sellers": best_sellers_data,
            "bookings": bookings_data
        })
        
    except Exception as e:
        print("Lỗi Dashboard:", e)
        return Response({'error': str(e)}, status=500)

@api_view(['POST'])
@permission_classes([AllowAny])
def create_booking(request):
    try:
        data = request.data
        time_str = f"{data.get('date')} {data.get('time')}" if data.get('date') else data.get('booking_time')
        
        Booking.objects.create(
            customer_name=data.get('name') or data.get('ho_ten'),
            customer_phone=data.get('phone') or data.get('sdt'),
            booking_time=time_str,
            guest_count=data.get('guests', 1),
            note=data.get('note', ''),
            status='pending'
        )
        return Response({'success': True, 'message': 'Đặt bàn thành công!'}, status=201)
    except Exception as e:
        return Response({'error': str(e)}, status=500)

@api_view(['DELETE'])
@permission_classes([IsAdminUser])
def delete_booking(request, pk):
    booking = get_object_or_404(Booking, pk=pk)
    booking.delete()
    return Response({'success': True})


# ==========================================
# 6. EMPLOYEE API (Quản lý nhân viên)
# ==========================================
class EmployeeViewSet(viewsets.ViewSet):
    """
    API CRUD Nhân viên - Thao tác trực tiếp trên bảng 'auth_user'
    """
    permission_classes = [IsAdminUser]

    def list(self, request):
        users = User.objects.filter(is_staff=True).exclude(username='admin').order_by('id')
        data = []
        for u in users:
            data.append({
                "id": u.id,
                "name": u.first_name if u.first_name else u.username,
                "user": u.username,
                "role": "admin" if u.is_superuser else "staff"
            })
        return Response(data)

    def create(self, request):
        try:
            data = request.data
            username = data.get('user')
            password = data.get('pass')
            name = data.get('name')
            role = data.get('role', 'staff')

            if User.objects.filter(username=username).exists():
                return Response({'error': 'Tên đăng nhập đã tồn tại!'}, status=400)

            user = User.objects.create(
                username=username,
                first_name=name,
                is_staff=True,
                is_active=True
            )
            if password:
                user.set_password(password)

            if role == 'admin':
                user.is_superuser = True
            else:
                user.is_superuser = False
            
            user.save()
            return Response({'message': 'Tạo nhân viên thành công', 'id': user.id}, status=201)
        except Exception as e:
            return Response({'error': str(e)}, status=500)

    def update(self, request, pk=None):
        try:
            user = User.objects.get(pk=pk)
            data = request.data

            if 'user' in data and data['user'] != user.username:
                if User.objects.filter(username=data['user']).exists():
                     return Response({'error': 'Tên đăng nhập đã tồn tại'}, status=400)
                user.username = data['user']
            
            if 'name' in data: user.first_name = data['name']

            new_pass = data.get('pass')
            if new_pass and str(new_pass).strip() != "":
                user.set_password(new_pass)

            role = data.get('role')
            if role == 'admin': user.is_superuser = True
            elif role == 'staff': user.is_superuser = False

            user.save()
            return Response({'message': 'Cập nhật thành công'})
        except User.DoesNotExist:
            return Response({'error': 'Không tìm thấy nhân viên'}, status=404)
        except Exception as e:
            return Response({'error': str(e)}, status=500)

    def destroy(self, request, pk=None):
        try:
            user = User.objects.get(pk=pk)
            if request.user.id == user.id:
                 return Response({'error': 'Không thể xóa tài khoản đang đăng nhập!'}, status=400)
            user.delete()
            return Response({'message': 'Đã xóa nhân viên'})
        except User.DoesNotExist:
            return Response({'error': 'User không tồn tại'}, status=404)
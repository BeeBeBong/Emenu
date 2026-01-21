import os
import json
import base64
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
    LoginSerializer, NotificationSerializer, UserSerializer,
    ProductFormSerializer
)

# ==========================================
# 1. CORE VIEWS
# ==========================================
def get_Emenu(request):
    return render(request, 'Emenu.html')

@api_view(['POST'])
@permission_classes([AllowAny])
@authentication_classes([])
@csrf_exempt
def login(request):
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
                'data': {'token': str(refresh.access_token), 'userId': user.id, 'fullName': name, 'role': role}
            })
        return Response({'message': 'Sai tài khoản hoặc mật khẩu'}, status=401)
    return Response(serializer.errors, status=400)

@api_view(['GET'])
def get_current_user(request):
    user = request.user
    if user.is_authenticated:
        role = 'ADMIN' if user.is_superuser else ('STAFF' if user.is_staff else 'CUSTOMER')
        return Response({
            'status': 'success',
            'data': {'userId': user.id, 'fullName': user.first_name or user.username, 'role': role, 'email': user.email}
        })
    return Response({'message': 'Chưa đăng nhập'}, status=401)

# ==========================================
# 2. QUẢN LÝ MENU (ĐÃ FIX QUYỀN TRUY CẬP)
# ==========================================
class CategoryViewSet(viewsets.ModelViewSet):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    
    # Cho phép khách xem danh mục, Admin mới được sửa
    def get_permissions(self):
        if self.action in ['list', 'retrieve']:
            return [AllowAny()]
        return [IsAdminUser()]

class ItemViewSet(viewsets.ModelViewSet):
    """
    ViewSet thông minh: 
    - Khách xem (list) -> Không cần login, dùng ItemSerializer (Base64)
    - Admin sửa (create/update) -> Cần login, dùng ProductFormSerializer
    """
    queryset = Item.objects.all().order_by('-id')
    
    # 🔥 QUAN TRỌNG: Cấu hình quyền truy cập động
    def get_permissions(self):
        if self.action in ['list', 'retrieve']:
            return [AllowAny()] # <--- MỞ CỬA CHO KHÁCH XEM
        return [IsAdminUser()]  # <--- KHÓA CỬA KHI SỬA/XÓA

    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update']:
            return ProductFormSerializer
        return ItemSerializer

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        serializer = ItemSerializer(queryset, many=True, context={'request': request})
        return Response(serializer.data)

# --- Các API lẻ (Backup) ---

@api_view(['GET'])
@permission_classes([AllowAny]) # <--- Cho phép khách xem
@authentication_classes([])
def get_menu(request):
    try:
        items = Item.objects.all().order_by('category', 'id')
        serializer = ItemSerializer(items, many=True, context={'request': request})
        return Response(serializer.data)
    except Exception as e:
        print("Lỗi get_menu:", e)
        return Response([], status=200)

@api_view(['GET'])
@permission_classes([AllowAny])
@authentication_classes([])
def get_menu_by_category(request, id_danhmuc):
    try:
        items = Item.objects.filter(category_id=id_danhmuc)
        serializer = ItemSerializer(items, many=True, context={'request': request})
        return Response(serializer.data)
    except Exception:
        return Response([], status=200)

@api_view(['GET'])
@permission_classes([AllowAny])
@authentication_classes([])
def get_menu_data(request):
    try:
        json_path = os.path.join(settings.BASE_DIR, 'menu.json')
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        categories = sorted(list(set(i['phan_loai'] for i in data)))
        products = [{'id': idx, 'name': item['ten_mon'], 'price': item['gia'], 'img': '', 'category': item['phan_loai']} for idx, item in enumerate(data, 1)]
        return Response({'categories': categories, 'products': products})
    except Exception:
        return Response({'error': 'File error'}, status=500)

# ==========================================
# 3. ORDER & TABLES
# ==========================================
class OrderViewSet(viewsets.ModelViewSet):
    queryset = Order.objects.all()
    serializer_class = OrderSerializer
    def create(self, request, *args, **kwargs):
        return create_order(request)

class TableViewSet(viewsets.ModelViewSet):
    queryset = Table.objects.all().order_by('id')
    serializer_class = TableSerializer

@api_view(['GET'])
def get_order_by_table(request, table_id):
    try:
        # Lấy đơn hàng cuối chưa thanh toán của bàn (id_ban)
        order = Order.objects.filter(table=table_id).exclude(status__in=['paid', 'cancelled']).last()
        
        if not order:
            return Response([], status=200) # Frontend mong đợi mảng rỗng nếu chưa có đơn
            
        # QUAN TRỌNG: Thêm context={'request': request} để lấy link ảnh món ăn
        serializer = OrderSerializer(order, context={'request': request})
        return Response(serializer.data)
    except Exception as e:
        return Response({'error': str(e)}, status=500)
@api_view(['POST'])
def create_order(request):
    try:
        data = request.data
        table_id = data.get('table_id') or data.get('tableId')
        items_data = data.get('items')
        
        table = get_object_or_404(Table, id=table_id)
        # Sửa filter tương tự get_order_by_table
        order = Order.objects.filter(table=table).exclude(status__in=['paid', 'cancelled']).last()
        
        if not order:
            order = Order.objects.create(table=table, status='pending', total=0)
        
        table.status = 'occupied'
        table.save()

        current_total = order.total
        for i in items_data:
            pid = i.get('id') or i.get('itemId')
            qty = int(i.get('quantity', 1))
            note = i.get('note', '')
            
            try:
                item = Item.objects.get(id=pid)
                # Sửa filter: order=order
                exist = OrderItem.objects.filter(order=order, item=item, is_served=False).first()
                if exist:
                    exist.quantity += qty
                    if note: exist.note = note
                    exist.save()
                else:
                    OrderItem.objects.create(order=order, item=item, quantity=qty, note=note)
                current_total += (item.price * qty)
            except Item.DoesNotExist:
                continue

        order.total = current_total
        order.save()
        return Response(OrderSerializer(order, context={'request': request}).data, status=201)
    except Exception as e:
        return Response({'error': str(e)}, status=500)

# ==========================================
# 4. ADMIN ACTIONS
# ==========================================
@api_view(['POST'])
@permission_classes([IsAdminUser])
def checkout(request, table_id):
    try:
        table = get_object_or_404(Table, id=table_id)
        order = Order.objects.filter(table=table).exclude(status__in=['paid', 'cancelled', 'served']).last()
        if not order: order = Order.objects.filter(table=table).exclude(status='paid').last()
        if not order: return Response({'error': 'Không có đơn'}, status=400)

        method = request.data.get('payment_method', 'cash')
        Revenue.objects.create(order=order, method=method, amount=order.total)
        order.status = 'paid'; order.save()
        table.status = 'available'; table.save()
        Notification.objects.filter(table=table).delete()
        return Response({'message': 'Thanh toán thành công'})
    except Exception as e:
        return Response({'error': str(e)}, status=500)

@api_view(['POST'])
@permission_classes([IsAdminUser])
def cancel_order(request):
    try:
        table_id = request.data.get('table_id')
        if not table_id: return Response({'error': 'Thiếu ID'}, status=400)
        
        deleted, _ = Order.objects.filter(table_id=table_id).exclude(status='paid').delete()
        Table.objects.filter(id=table_id).update(status='available', reserved_at=None, expires_at=None)
        Notification.objects.filter(table_id=table_id).delete()
        return Response({'message': 'Đã hủy đơn'})
    except Exception as e:
        return Response({'error': str(e)}, status=500)

@api_view(['POST'])
def reserve_table(request, id_ban):
    table = get_object_or_404(Table, id=id_ban)
    if table.status != 'available': return Response({'error': 'Bàn bận'}, status=400)
    table.status = 'reserved'; table.reserved_at = timezone.now(); table.save()
    return Response(TableSerializer(table).data)

@api_view(['POST'])
def request_payment(request):
    try:
        table_id = request.data.get('table_id')
        table = Table.objects.get(id=table_id)
        Notification.objects.create(table=table, message=f"{table.number} yêu cầu thanh toán", is_read=False)
        return Response({'success': True})
    except Exception:
        return Response({'error': 'Lỗi'}, status=500)

@api_view(['GET'])
def get_notifications(request):
    notifs = Notification.objects.all().order_by('-created_at')
    return Response(NotificationSerializer(notifs, many=True).data)

@api_view(['GET'])
def get_dashboard_stats(request):
    try:
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
        else:
            filter_kwargs = {'paid_at__date': today}

        revenues = Revenue.objects.filter(**filter_kwargs)
        total_rev = revenues.aggregate(t=Coalesce(Sum('amount'), 0))['t']
        cash_rev = revenues.filter(method='cash').aggregate(t=Coalesce(Sum('amount'), 0))['t']
        transfer_rev = revenues.filter(method='transfer').aggregate(t=Coalesce(Sum('amount'), 0))['t']
        total_orders = revenues.count()

        top_items = OrderItem.objects.values('item').annotate(total=Sum('quantity')).order_by('-total')[:5]
        best_sellers_data = []
        for t in top_items:
            try:
                item = Item.objects.get(pk=t['item'])
                img_data = ""
                if item.image and hasattr(item.image, 'path') and os.path.exists(item.image.path):
                    with open(item.image.path, "rb") as f:
                        img_data = f"data:image/jpeg;base64,{base64.b64encode(f.read()).decode('utf-8')}"
                else:
                    img_data = "https://images.unsplash.com/photo-1579871494447-9811cf80d66c?q=80&w=200"

                best_sellers_data.append({
                    'id': item.id, 'name': item.name, 'price': item.price,
                    'img': img_data, 'sold_count': t['total']
                })
            except Item.DoesNotExist: continue

        recent_bookings = Booking.objects.filter(status='pending').order_by('-created_at')[:10]
        bookings_data = [{"id": b.id, "customer_name": b.customer_name, "phone": b.customer_phone, "time": b.booking_time, "guests": b.guest_count, "status": b.status} for b in recent_bookings]

        return Response({
            "revenue": {"total": total_rev, "cash": cash_rev, "transfer": transfer_rev, "orders": total_orders},
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
            booking_time=time_str, guest_count=data.get('guests', 1),
            note=data.get('note', ''), status='pending'
        )
        return Response({'success': True}, status=201)
    except Exception as e:
        return Response({'error': str(e)}, status=500)

@api_view(['DELETE'])
@permission_classes([IsAdminUser])
def delete_booking(request, pk):
    get_object_or_404(Booking, pk=pk).delete()
    return Response({'success': True})

# ==========================================
# 5. EMPLOYEE
# ==========================================
class EmployeeViewSet(viewsets.ViewSet):
    permission_classes = [IsAdminUser]
    
    def list(self, request):
        users = User.objects.filter(is_staff=True).exclude(username='admin').order_by('id')
        data = [{"id": u.id, "name": u.first_name or u.username, "user": u.username, "role": "admin" if u.is_superuser else "staff"} for u in users]
        return Response(data)

    def create(self, request):
        try:
            d = request.data
            if User.objects.filter(username=d.get('user')).exists(): return Response({'error': 'Trùng tên'}, 400)
            u = User.objects.create(username=d.get('user'), first_name=d.get('name'), is_staff=True, is_active=True)
            if d.get('pass'): u.set_password(d.get('pass'))
            u.is_superuser = (d.get('role') == 'admin')
            u.save()
            return Response({'message': 'OK', 'id': u.id}, 201)
        except Exception as e: return Response({'error': str(e)}, 500)

    def update(self, request, pk=None):
        try:
            u = User.objects.get(pk=pk)
            d = request.data
            if 'user' in d and d['user'] != u.username:
                if User.objects.filter(username=d['user']).exists(): return Response({'error': 'Trùng tên'}, 400)
                u.username = d['user']
            if 'name' in d: u.first_name = d['name']
            if d.get('pass'): u.set_password(d.get('pass'))
            if d.get('role'): u.is_superuser = (d.get('role') == 'admin')
            u.save()
            return Response({'message': 'OK'})
        except: return Response({'error': 'Lỗi'}, 500)

    def destroy(self, request, pk=None):
        try:
            u = User.objects.get(pk=pk)
            if request.user.id == u.id: return Response({'error': 'Không thể xóa chính mình'}, 400)
            u.delete()
            return Response({'message': 'OK'})
        except: return Response({'error': 'Lỗi'}, 500)
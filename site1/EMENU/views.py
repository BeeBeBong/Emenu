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

from rest_framework import viewsets, status
from rest_framework.decorators import api_view, permission_classes, authentication_classes
from rest_framework.permissions import AllowAny, IsAdminUser
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken

from .models import Category, Item, Table, Order, OrderItem, Revenue, Booking, Notification
from .serializers import (
    CategorySerializer, ItemSerializer, TableSerializer,
    OrderSerializer, OrderItemSerializer, RevenueSerializer, 
    LoginSerializer, NotificationSerializer 
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
    """Lấy thông tin user từ Token đang đăng nhập"""
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
# 2. MENU & TABLE APIs (Standard ViewSets)
# ==========================================
class CategoryViewSet(viewsets.ModelViewSet):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer

class ItemViewSet(viewsets.ModelViewSet):
    queryset = Item.objects.all()
    serializer_class = ItemSerializer
    # Thêm context request để Serializer tạo full link ảnh
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
# 3. ORDER LOGIC (Tối ưu hóa)
# ==========================================
class OrderViewSet(viewsets.ModelViewSet):
    """ViewSet cơ bản cho Order"""
    queryset = Order.objects.all()
    serializer_class = OrderSerializer
    
    def create(self, request, *args, **kwargs):
        # Chuyển hướng sang hàm create_order tùy biến
        return create_order(request)

@api_view(['POST'])
def create_order(request):
    """Tạo đơn hoặc Cộng dồn (Merge) món vào đơn cũ"""
    try:
        data = request.data
        table_id = data.get('table_id') or data.get('tableId')
        items_data = data.get('items')

        if not table_id or not items_data:
            return Response({'error': 'Thiếu tableId hoặc items'}, status=400)

        table = get_object_or_404(Table, id=table_id)

        # 1. Tìm đơn chưa thanh toán (để cộng dồn)
        order = Order.objects.filter(table=table).exclude(status__in=['paid', 'cancelled']).last()

        # 2. Nếu chưa có -> Tạo mới
        if not order:
            order = Order.objects.create(table=table, status='pending', total=0)
        
        # 👇 QUAN TRỌNG: Luôn cập nhật trạng thái bàn thành "Có người"
        # (Dù là tạo mới hay cộng dồn thì bàn cũng phải sáng đèn)
        if table.status == 'available':
            table.status = 'occupied'
            table.save()

        # 3. Xử lý thêm món
        current_total = order.total
        
        for i in items_data:
            pid = i.get('id') or i.get('itemId') or i.get('product_id')
            qty = int(i.get('quantity', 1))
            note = i.get('note', '')

            if not pid: continue
            
            try:
                item = Item.objects.get(id=pid)
                
                # Tìm món trùng trong đơn để cộng dồn (bỏ is_served=False để gộp tất cả)
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
                        # price=item.price, <--- ĐÃ BỎ DÒNG NÀY (Do DB không có cột price)
                        note=note, 
                        is_served=False
                    )
                
                # Cộng tiền của món mới gọi vào tổng bill
                current_total += (item.price * qty)
                
            except Item.DoesNotExist:
                continue

        # 4. Lưu tổng tiền & trả về
        order.total = current_total
        order.save()
        
        return Response(OrderSerializer(order, context={'request': request}).data, status=201)

    except Exception as e:
        return Response({'error': str(e)}, status=500)

@api_view(['GET'])
def get_order_by_table(request, table_id):
    """Lấy đơn hàng hiện tại của bàn (Cho F5 không mất đơn)"""
    try:
        # Lấy đơn chưa thanh toán gần nhất
        order = Order.objects.filter(table_id=table_id).exclude(status__in=['paid', 'cancelled']).last()
        
        if not order:
            return Response([]) # Bàn trống
            
        return Response(OrderSerializer(order, context={'request': request}).data)
    except Exception as e:
        return Response({'error': str(e)}, status=500)


# ==========================================
# 4. ADMIN ACTIONS (Checkout, Cancel, Booking)
# ==========================================
@api_view(['POST'])
@permission_classes([IsAdminUser]) # Chỉ Admin/Staff
def checkout(request, table_id):
    """Thanh toán và trả bàn"""
    try:
        table = get_object_or_404(Table, id=table_id)
        order = Order.objects.filter(table=table).exclude(status__in=['paid', 'cancelled', 'served']).last()
        
        if not order:
            # Check trường hợp đơn đã status='served' nhưng chưa trả tiền (nếu quy trình quán có bước này)
            # Hoặc đơn giản là lấy đơn chưa thanh toán cuối cùng
            order = Order.objects.filter(table=table).exclude(status='paid').last()
            if not order:
                return Response({'error': 'Không có đơn để thanh toán'}, status=400)

        # Tạo doanh thu
        method = request.data.get('payment_method', 'cash')
        Revenue.objects.create(order=order, method=method, amount=order.total)

        # Update trạng thái
        order.status = 'paid' # Đổi thành paid để API get_order không thấy nữa
        order.save()

        table.status = 'available'
        table.save()

        return Response({'message': 'Thanh toán thành công', 'amount': order.total})
    except Exception as e:
        return Response({'error': str(e)}, status=500)

@api_view(['POST'])
@permission_classes([IsAdminUser])
def cancel_order(request):
    """Hủy đơn, Reset bàn và Xóa thông báo"""
    try:
        table_id = request.data.get('table_id')
        if not table_id: 
            return Response({'error': 'Thiếu table_id'}, status=400)

        # 1. Xóa những đơn chưa thanh toán (giữ lại đơn đã paid để thống kê doanh thu)
        deleted_count, _ = Order.objects.filter(
            table_id=table_id
        ).exclude(status='paid').delete()

        # 2. Reset trạng thái bàn về 'available' (Trống)
        # Dùng .update() sẽ nhanh hơn get().save() và không cần try/except check bàn tồn tại
        Table.objects.filter(id=table_id).update(
            status='available',
            reserved_at=None, # Xóa giờ đặt bàn (nếu có)
            expires_at=None
        )

        # 3. ✅ QUAN TRỌNG: Xóa thông báo "Yêu cầu thanh toán" của bàn này
        # (Để cái chuông trên Admin tắt thông báo đi)
        Notification.objects.filter(table_id=table_id).delete()

        if deleted_count > 0:
            return Response({'message': 'Đã hủy đơn hàng và dọn bàn thành công'})
        else:
            return Response({'message': 'Đã dọn bàn về trạng thái trống (Không có đơn hàng nào)'})
            
    except Exception as e:
        return Response({'error': str(e)}, status=500)

@api_view(['POST'])
def reserve_table(request, id_ban):
    """Đặt trước bàn"""
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

        # ❌ BỎ DÒNG NÀY: table.status = 'payment_requested'
        
        # ✅ THÊM DÒNG NÀY: Tạo thông báo mới
        Notification.objects.create(
            table=table,
            message=f"{table.number} yêu cầu thanh toán",
            is_read=False
        )
        
        return Response({'success': True, 'message': 'Đã gửi yêu cầu!'})
    except Exception as e:
        return Response({'error': str(e)}, status=500)


# 2. SỬA HÀM CHECKOUT (THANH TOÁN)
@api_view(['POST'])
@permission_classes([IsAdminUser])
def checkout(request, table_id):
    try:
        # ... (Các logic tìm bàn, tìm order, tính tiền GIỮ NGUYÊN) ...
        table = Table.objects.get(id=table_id)
        order = Order.objects.filter(table=table).exclude(status__in=['paid', 'cancelled', 'served']).last()
        if not order:
             order = Order.objects.filter(table=table).exclude(status='paid').last()
        
        # ... (Logic tạo Revenue, save order... GIỮ NGUYÊN) ...
        Revenue.objects.create(order=order, method=request.data.get('payment_method', 'cash'), amount=order.total)
        order.status = 'paid'
        order.save()
        table.status = 'available'
        table.save()

        # ✅ THÊM DÒNG NÀY: Xóa thông báo yêu cầu thanh toán của bàn này (nếu có)
        Notification.objects.filter(table=table).delete()

        return Response({'message': 'Thanh toán thành công'})
    except Exception as e:
        return Response({'error': str(e)}, status=500)


# 3. THÊM API LẤY THÔNG BÁO (Cho cái chuông)
@api_view(['GET'])
def get_notifications(request):
    # Lấy các thông báo chưa đọc, mới nhất lên đầu
    notifs = Notification.objects.all().order_by('-created_at')
    serializer = NotificationSerializer(notifs, many=True)
    return Response(serializer.data)

# ==========================================
# 5. DASHBOARD & BOOKING (Giữ nguyên logic)
# ==========================================
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

@api_view(['GET'])
def get_dashboard_stats(request):
    # Logic thống kê Dashboard (Rút gọn cho dễ đọc - Giữ nguyên logic cũ của bạn ở đây)
    range_type = request.query_params.get('range', 'today')
    today = timezone.now().date()
    # ... (Giữ nguyên phần tính start_date/end_date của bạn) ...
    start_date = today # Mặc định
    
    # Doanh thu
    revs = Revenue.objects.filter(paid_at__date__gte=start_date) # Demo
    total = revs.aggregate(t=Coalesce(Sum('amount'), 0))['t']
    
    # Best seller
    best = Item.objects.annotate(sold=Coalesce(Sum('order_items__quantity'), 0)).order_by('-sold')[:5]
    best_data = [{
        'name': i.name, 
        'sold_count': i.sold, 
        'price': i.price,  # <--- THÊM DÒNG NÀY
        'image': request.build_absolute_uri(i.image.url) if i.image else ''
    } for i in best]

    return Response({
        'revenue': {'total': total, 'orders': revs.count()},
        'best_sellers': best_data,
        'bookings': [] # Thêm logic booking nếu cần
    })
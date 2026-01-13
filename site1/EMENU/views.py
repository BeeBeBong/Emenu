from email.utils import localtime
from rest_framework import viewsets
from rest_framework.decorators import api_view
from rest_framework.response import Response
from django.shortcuts import render
from .models import Category, Item, Table, Order, OrderItem, Revenue, Booking
from .serializers import (
    CategorySerializer, ItemSerializer, TableSerializer,
    OrderSerializer, OrderItemSerializer, RevenueSerializer, LoginSerializer
)
from rest_framework import status
from django.shortcuts import get_object_or_404
from django.contrib.auth.models import User
from django.contrib.auth import authenticate
from django.db.models import Sum
from rest_framework_simplejwt.tokens import RefreshToken
import json
import os
from django.conf import settings
from rest_framework.decorators import api_view, permission_classes
from django.db.models.functions import Coalesce
from datetime import date
from rest_framework.permissions import AllowAny, IsAdminUser
from django.views.decorators.csrf import csrf_exempt


# ========== Template View ==========
def get_Emenu(request):
    """Render template HTML cho eMenu"""
    return render(request, 'Emenu.html')

# ========== AUTH APIs ==========
@api_view(['POST'])
def login(request):
    """Dang nhap va lay token"""
    serializer = LoginSerializer(data=request.data)
    if serializer.is_valid():
        username = serializer.validated_data['username']
        password = serializer.validated_data['password']
        
        user = authenticate(username=username, password=password)
        if user is not None:
            refresh = RefreshToken.for_user(user)
            return Response({
                'status': 'success',
                'message': 'Dang nhap thanh cong',
                'data': {
                    'token': str(refresh.access_token),
                    'userId': user.id,
                    'fullName': user.get_full_name() or user.username,
                    'role': 'ADMIN' if user.is_superuser else ('STAFF' if user.is_staff else 'CUSTOMER')
                }
            }, status=status.HTTP_200_OK)
        else:
            return Response({
                'status': 'error',
                'message': 'Sai username hoac password'
            }, status=status.HTTP_401_UNAUTHORIZED)
    else:
        return Response({
            'status': 'error',
            'message': 'Thong tin dang nhap khong hop le',
            'errors': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)

@api_view(['GET'])
def get_current_user(request):
    """Lay thong tin user hien tai (role/permission)"""
    if request.user.is_authenticated:
        return Response({
            'id': request.user.id,
            'username': request.user.username,
            'email': request.user.email,
            'is_admin': request.user.is_superuser,
            'is_staff': request.user.is_staff,
            'role': 'admin' if request.user.is_superuser else ('staff' if request.user.is_staff else 'customer')
        }, status=status.HTTP_200_OK)
    else:
        return Response({
            'error': 'Chua dang nhap'
        }, status=status.HTTP_401_UNAUTHORIZED)

@api_view(['GET'])
def get_revenue(request):
    """
    API lấy dữ liệu cho Dashboard:
    1. Tổng doanh thu, Tiền mặt, Tài khoản khác
    2. Tổng số đơn hàng
    3. Top món bán chạy (Best Seller)
    """
    # Kiểm tra quyền (giữ nguyên logic cũ của bạn)
    if not request.user.is_staff:
        return Response({
            'error': 'Khong co quyen truy cap'
        }, status=status.HTTP_403_FORBIDDEN)
    
    # --- PHẦN 1: TÍNH TOÁN DOANH THU ---
    # Tính tổng doanh thu (dùng Coalesce để nếu không có đơn nào thì trả về 0 thay vì None)
    total_revenue = Revenue.objects.aggregate(
        total=Coalesce(Sum('amount'), 0)
    )['total']
    
    # Tính riêng Tiền mặt (Cash)
    cash_revenue = Revenue.objects.filter(method='cash').aggregate(
        total=Coalesce(Sum('amount'), 0)
    )['total']
    
    # Tính riêng Tài khoản khác (Banking, Momo, Card...) - Là tất cả trừ Cash
    banking_revenue = Revenue.objects.exclude(method='cash').aggregate(
        total=Coalesce(Sum('amount'), 0)
    )['total']
    
    # --- PHẦN 2: ĐẾM SỐ ĐƠN HÀNG ---
    total_orders = Order.objects.count()

    # --- PHẦN 3: TÍNH BEST SELLER (MÓN BÁN CHẠY) ---
    # Logic: Group by món ăn (Item) -> Sum số lượng từ bảng OrderItem -> Sắp xếp giảm dần
    best_sellers_query = Item.objects.annotate(
        total_sold=Coalesce(Sum('order_items__quantity'), 0) # Cộng dồn số lượng đã bán
    ).filter(total_sold__gt=0).order_by('-total_sold')[:5]   # Lấy top 5 món bán > 0

    # Format dữ liệu Best Seller để gửi về Frontend
    best_sellers_data = []
    for item in best_sellers_query:
        # Xử lý ảnh: nếu không có ảnh thì để chuỗi rỗng hoặc link ảnh mặc định
        img_url = request.build_absolute_uri(item.image.url) if item.image else ''
        
        best_sellers_data.append({
            'name': item.name,
            'price': item.price,
            'sold_count': item.total_sold, # Số lượng đã bán (hiện màu đỏ trong hình)
            'image': img_url
        })

    # --- TRẢ VỀ KẾT QUẢ ---
    return Response({
        'dashboard': {
            'total_revenue': total_revenue,   # Tổng doanh thu
            'cash_revenue': cash_revenue,     # Tiền mặt
            'banking_revenue': banking_revenue, # Tài khoản khác
            'total_orders': total_orders,     # Tổng đơn hàng
        },
        'best_sellers': best_sellers_data     # Danh sách món bán chạy
    }, status=status.HTTP_200_OK)

# ========== CATEGORY APIs ==========
class CategoryViewSet(viewsets.ModelViewSet):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer

# ========== ITEM APIs ==========
class ItemViewSet(viewsets.ModelViewSet):
    queryset = Item.objects.all()
    serializer_class = ItemSerializer
    
    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['request'] = self.request
        return context

@api_view(['GET'])
def get_menu(request):
    """Lấy tất cả món ăn"""
    items = Item.objects.all()
    serializer = ItemSerializer(items, many=True, context={'request': request})
    return Response(serializer.data)

@api_view(['GET'])
def get_menu_data(request):
    """Lấy dữ liệu menu đầy đủ từ file JSON: categories và products (format cho frontend)"""
    # Tìm đường dẫn file menu.json (nằm cùng thư mục với manage.py)
    base_dir = settings.BASE_DIR
    json_path = os.path.join(base_dir, 'menu.json')
    
    try:
        # Đọc file JSON
        with open(json_path, 'r', encoding='utf-8') as f:
            menu_data = json.load(f)
        
        # Lấy unique categories từ phan_loai
        categories = list(set(item['phan_loai'] for item in menu_data))
        categories.sort()  # Sắp xếp theo thứ tự alphabet
        
        # Format products theo cấu trúc frontend cần
        products = []
        for idx, item in enumerate(menu_data, start=1):
            products.append({
                'id': idx,
                'name': item['ten_mon'],
                'price': item['gia'],
                'img': item.get('img', ''),  # Lấy từ JSON, mặc định là rỗng nếu không có
                'category': item['phan_loai']
            })
        
        return Response({
            'categories': categories,
            'products': products
        }, status=status.HTTP_200_OK)
    except FileNotFoundError:
        return Response({
            'error': 'Không tìm thấy file menu.json',
            'detail': f'File không tồn tại tại: {json_path}'
        }, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        return Response({
            'error': 'Không thể tải dữ liệu menu',
            'detail': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['GET'])
def get_menu_by_category(request, id_danhmuc):
    """Lấy món ăn theo danh mục"""
    items = Item.objects.filter(category_id=id_danhmuc)
    serializer = ItemSerializer(items, many=True, context={'request': request})
    return Response(serializer.data)

# ========== TABLE APIs ==========
class TableViewSet(viewsets.ModelViewSet):
    queryset = Table.objects.all()
    serializer_class = TableSerializer

@api_view(['POST'])
def reserve_table(request, id_ban):
    """Đặt trước bàn (5 phút)"""
    table = get_object_or_404(Table, id=id_ban)
    if table.status != 'available':
        return Response({'error': 'Bàn không trống'}, status=status.HTTP_400_BAD_REQUEST)
    
    from django.utils import timezone
    from datetime import timedelta
    
    table.status = 'reserved'
    table.reserved_at = timezone.now()
    table.expires_at = timezone.now() + timedelta(minutes=5)
    table.save()
    
    serializer = TableSerializer(table)
    return Response(serializer.data, status=status.HTTP_200_OK)

# ========== ORDER APIs ==========
class OrderViewSet(viewsets.ModelViewSet):
    queryset = Order.objects.all()
    serializer_class = OrderSerializer
    
    def create(self, request, *args, **kwargs):
        """Override create method để xử lý tạo đơn hàng với items"""
        # Chuyển hướng đến function create_order để xử lý
        return create_order(request)

@api_view(['POST'])
def create_order(request):
    """Tạo đơn hàng mới"""
    try:
        data = request.data
        
        # Lấy thông tin bàn
        table_id = data.get('tableId')
        if not table_id:
            return Response({'error': 'Thiếu thông tin bàn (tableId)'}, status=status.HTTP_400_BAD_REQUEST)
        
        # Kiểm tra tableId có phải số không
        try:
            table_id = int(table_id)
        except (ValueError, TypeError):
            return Response({
                'error': 'tableId không hợp lệ',
                'detail': f'tableId phải là số nguyên, nhận được: {table_id}'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Kiểm tra bàn có tồn tại không
        try:
            table = Table.objects.get(id=table_id)
        except Table.DoesNotExist:
            return Response({
                'error': 'Bàn không tồn tại',
                'detail': f'Không tìm thấy bàn với ID: {table_id}. Vui lòng kiểm tra lại hoặc lấy danh sách bàn từ GET /api/tables/'
            }, status=status.HTTP_404_NOT_FOUND)
        
        # Lấy danh sách món ăn
        items_data = data.get('items', [])
        if not items_data:
            return Response({'error': 'Danh sách món ăn không được để trống'}, status=status.HTTP_400_BAD_REQUEST)
        
        # Tính tổng tiền
        total = 0
        for item_data in items_data:
            item_id = item_data.get('itemId') or item_data.get('id_mon')
            if not item_id:
                return Response({
                    'error': 'Thiếu itemId trong danh sách món ăn',
                    'detail': f'Món ăn: {item_data}'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            try:
                item_id = int(item_id)
            except (ValueError, TypeError):
                return Response({
                    'error': 'itemId không hợp lệ',
                    'detail': f'itemId phải là số nguyên, nhận được: {item_id}'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            quantity = item_data.get('quantity', 1)
            try:
                quantity = int(quantity)
                if quantity <= 0:
                    return Response({
                        'error': 'Số lượng không hợp lệ',
                        'detail': f'Số lượng phải lớn hơn 0, nhận được: {quantity}'
                    }, status=status.HTTP_400_BAD_REQUEST)
            except (ValueError, TypeError):
                return Response({
                    'error': 'Số lượng không hợp lệ',
                    'detail': f'Số lượng phải là số nguyên, nhận được: {quantity}'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            try:
                item = Item.objects.get(id=item_id)
            except Item.DoesNotExist:
                return Response({
                    'error': 'Món ăn không tồn tại',
                    'detail': f'Không tìm thấy món ăn với ID: {item_id}'
                }, status=status.HTTP_404_NOT_FOUND)
            
            total += item.price * quantity
        
        # Tạo đơn hàng
        order = Order.objects.create(
            table=table,
            total=total,
            status='pending'
        )
        
        # Tạo chi tiết đơn hàng
        for item_data in items_data:
            item_id = item_data.get('itemId') or item_data.get('id_mon')
            quantity = item_data.get('quantity', 1)
            note = item_data.get('note', '') or item_data.get('ghi_chu', '')
            
            # Đã validate ở trên, chỉ cần get lại
            item = Item.objects.get(id=item_id)
            
            OrderItem.objects.create(
                order=order,
                item=item,
                quantity=quantity,
                note=note
            )
        
        # Serialize và trả về đơn hàng đã tạo
        serializer = OrderSerializer(order)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
        
    except Exception as e:
        return Response({
            'error': 'Lỗi khi tạo đơn hàng',
            'detail': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    # --- API 1: KHÁCH GỬI YÊU CẦU ĐẶT BÀN (Public - Ai cũng gửi được) ---
# --- Thay thế hàm create_booking cũ bằng hàm này ---

@api_view(['POST'])
@csrf_exempt
@permission_classes([AllowAny])
def create_booking(request):
    """
    API đặt bàn: Hỗ trợ tự động ghép Ngày và Giờ từ Frontend
    """
    try:
        data = request.data
        
        # 1. Lấy dữ liệu cơ bản
        name = data.get('name') or data.get('ho_ten')
        phone = data.get('phone') or data.get('sdt')
        guests = data.get('guests', 1)
        note = data.get('note', '')

        # 2. Xử lý ghép Ngày + Giờ (Phần quan trọng nhất)
        raw_date = data.get('date') # Frontend gửi: "2026-01-14"
        raw_time = data.get('time') # Frontend gửi: "18:30"
        
        booking_time_final = ""

        # Logic ghép chuỗi
        if raw_date and raw_time:
            # Nếu gửi riêng -> Ghép lại thành "2026-01-14 18:30"
            booking_time_final = f"{raw_date} {raw_time}"
        elif raw_time and not raw_date:
            # Trường hợp gửi gộp (dự phòng)
            booking_time_final = raw_time
        elif data.get('booking_time'):
            booking_time_final = data.get('booking_time')
        else:
             return Response({'error': 'Vui lòng chọn đầy đủ Ngày và Giờ'}, status=status.HTTP_400_BAD_REQUEST)

        # 3. Validate bắt buộc
        if not name or not phone:
            return Response({'error': 'Vui lòng nhập Tên và SĐT'}, status=status.HTTP_400_BAD_REQUEST)

        # 4. Lưu vào Database
        booking = Booking.objects.create(
            customer_name=name,
            customer_phone=phone,
            booking_time=booking_time_final, # Lưu chuỗi đã ghép
            guest_count=guests,
            note=note,
            status='pending'
        )
        
        return Response({
            'success': True,
            'message': 'Hệ thống đã ghi nhận thông tin. Nhân viên sẽ liên hệ sớm!',
            'booking_id': booking.id
        }, status=status.HTTP_201_CREATED)

    except Exception as e:
        # In lỗi ra terminal để dễ debug nếu có sự cố
        print("Lỗi tạo booking:", str(e))
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# --- API 2: DASHBOARD CHO ADMIN (Lấy Booking + Doanh thu) ---
@api_view(['GET'])
def get_dashboard_stats(request):
    """
    API tổng hợp dữ liệu Dashboard:
    1. Revenue (Doanh thu)
    2. Best Sellers
    3. Bookings (Danh sách chờ xử lý cho Admin)
    """
    # Chỉ Staff/Admin mới xem được
    if not request.user.is_staff:
        return Response({'error': 'Unauthorized'}, status=status.HTTP_403_FORBIDDEN)

    # 1. TÍNH DOANH THU (Code cũ - giữ nguyên)
    total_revenue = Revenue.objects.aggregate(total=Coalesce(Sum('amount'), 0))['total']
    cash_revenue = Revenue.objects.filter(method='cash').aggregate(total=Coalesce(Sum('amount'), 0))['total']
    transfer_revenue = Revenue.objects.exclude(method='cash').aggregate(total=Coalesce(Sum('amount'), 0))['total']
    total_orders = Order.objects.count()

    # 2. LẤY LIST BOOKING (Mới cập nhật)
    # Lấy các booking sắp tới (tính từ hôm nay) để Admin gọi điện
    today = date.today()
    
    # Lấy cả 'pending' (để xử lý) và 'confirmed' (để theo dõi)
    bookings_query = Booking.objects.filter(
        booking_time__date__gte=today
    ).order_by('booking_time') # Sắp xếp theo giờ ăn sắp đến
    
    bookings_data = []
    for b in bookings_query:
        try:
            # Nếu field là DateTimeField
            local_time = localtime(b.booking_time)
            formatted_date = local_time.strftime('%Y-%m-%d') # Sẽ ra đúng ngày
            formatted_time = local_time.strftime('%H:%M')    # Sẽ ra đúng giờ
        except:
            # Nếu field là CharField (lưu dạng chuỗi) thì giữ nguyên hoặc cắt chuỗi
            # Tùy vào cách bạn lưu lúc khách đặt. 
            # Tốt nhất là lưu DateTimeField để dùng hàm trên.
            formatted_date = str(b.booking_time).split(' ')[0]
            formatted_time = str(b.booking_time).split(' ')[1] if ' ' in str(b.booking_time) else ''
        bookings_data.append({
            "id": b.id,
            "name": b.customer_name,      # Map với: name
            "phone": b.customer_phone,    # Map với: phone
            "time": formatted_time,       # Map với: time ("18:30")
            "date": formatted_date,       # Map với: date ("2026-01-14")
            "guests": b.guest_count,      # Map với: guests
            "status": b.status            # Map với: status ("pending"/"confirmed")
        })

    # 3. BEST SELLERS (Code cũ - giữ nguyên)
    best_sellers_query = Item.objects.annotate(
        total_sold=Coalesce(Sum('order_items__quantity'), 0)
    ).filter(total_sold__gt=0).order_by('-total_sold')[:5]

    best_sellers_data = []
    for item in best_sellers_query:
        img_url = request.build_absolute_uri(item.image.url) if item.image else ''
        best_sellers_data.append({
            'name': item.name,
            'price': item.price,
            'sold_count': item.total_sold,
            'image': img_url
        })

    return Response({
        'revenue': {
            'total': total_revenue,
            'cash': cash_revenue,
            'transfer': transfer_revenue,
            'orders': total_orders
        },
        'bookings': bookings_data, # Dữ liệu khớp với biến BOOKINGS ở frontend
        'best_sellers': best_sellers_data
    }, status=status.HTTP_200_OK)
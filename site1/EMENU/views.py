from email.utils import localtime
from rest_framework import viewsets
from rest_framework.decorators import api_view
from rest_framework.response import Response
from django.shortcuts import render
from .models import Category, Item, Table, Order, OrderItem, Revenue, Booking
from .serializers import (
    CategorySerializer, ItemSerializer, TableSerializer,
    OrderSerializer, OrderItemSerializer, RevenueSerializer, 
    LoginSerializer, UserSerializer 
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
from django.utils import timezone
from datetime import timedelta
from rest_framework.decorators import authentication_classes, permission_classes
from rest_framework.permissions import AllowAny
from django.views.decorators.csrf import csrf_exempt


# ========== Template View ==========
def get_Emenu(request):
    """Render template HTML cho eMenu"""
    return render(request, 'Emenu.html')


@api_view(['GET'])
def get_current_user(request):
    """Lấy thông tin user hiện tại (Đã đồng bộ tên biến với Login)"""
    if request.user.is_authenticated:
        # Xác định Role giống hệt hàm Login
        role = 'ADMIN' if request.user.is_superuser else ('STAFF' if request.user.is_staff else 'CUSTOMER')
        
        # Lấy tên hiển thị ưu tiên
        display_name = request.user.first_name if request.user.first_name else request.user.username

        return Response({
            'status': 'success',
            'data': {
                # --- PHẦN QUAN TRỌNG NHẤT: ĐỔI TÊN BIẾN ---
                'userId': request.user.id,        # Đổi 'id' thành 'userId'
                'fullName': display_name,         # Đổi 'username' thành 'fullName'
                'role': role,                     # Gộp is_staff/superuser thành 'role'
                'email': request.user.email
            }
        }, status=status.HTTP_200_OK)
    else:
        return Response({
            'status': 'error',
            'message': 'Chưa đăng nhập'
        }, status=status.HTTP_401_UNAUTHORIZED)


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
        
        # 1. Lấy thông tin bàn
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
        
        # 2. Lấy danh sách món ăn
        items_data = data.get('items', [])
        if not items_data:
            return Response({'error': 'Danh sách món ăn không được để trống'}, status=status.HTTP_400_BAD_REQUEST)
        
        # 3. Tính tổng tiền
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
        
        # 4. Tạo đơn hàng (Order)
        order = Order.objects.create(
            table=table,
            total=total,
            status='pending'
        )

        # 👇 [QUAN TRỌNG] CẬP NHẬT TRẠNG THÁI BÀN NGAY TẠI ĐÂY 👇
        table.status = 'occupied'  # Chuyển sang màu vàng (đang có khách)
        table.save()               # Lưu lại vào database
        # 👆 -------------------------------------------------- 👆
        
        # 5. Tạo chi tiết đơn hàng (OrderItem)
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
    API Dashboard xử lý lọc theo range: 
    ?range=today (default) | yesterday | week | month | quarter | year
    """
    # 1. Lấy tham số range từ URL (Mặc định là today)
    range_type = request.query_params.get('range', 'today')
    
    # 2. Tính toán ngày bắt đầu (start_date) và kết thúc (end_date)
    today = timezone.now().date()
    start_date = today
    end_date = today

    if range_type == 'yesterday':
        start_date = today - timedelta(days=1)
        end_date = start_date
    elif range_type == 'week':
        # Tuần này (Thứ 2 -> Hôm nay)
        start_date = today - timedelta(days=today.weekday())
        end_date = today
    elif range_type == 'month':
        # Tháng này (Ngày 1 -> Hôm nay)
        start_date = today.replace(day=1)
        end_date = today
    elif range_type == 'quarter':
        # Quý này: (Tháng 1-3 -> Q1, 4-6 -> Q2...)
        quarter = (today.month - 1) // 3 + 1
        start_month = 3 * (quarter - 1) + 1
        start_date = today.replace(month=start_month, day=1)
        end_date = today
    elif range_type == 'year':
        # Năm nay
        start_date = today.replace(month=1, day=1)
        end_date = today

    # 3. Truy vấn dữ liệu theo khoảng thời gian (start_date -> end_date)
    
    # --- A. BOOKING (Lịch đặt bàn) ---
    # Lọc các đơn nằm trong khoảng thời gian đã chọn (cả quá khứ và tương lai)
    bookings_query = Booking.objects.filter(
        booking_time__date__range=[start_date, end_date]
    ).order_by('booking_time')
    
    bookings_data = []
    for b in bookings_query:
        # Xử lý format ngày giờ an toàn
        try:
            if timezone.is_aware(b.booking_time):
                local_time = timezone.localtime(b.booking_time)
            else:
                local_time = b.booking_time
            formatted_date = local_time.strftime('%Y-%m-%d')
            formatted_time = local_time.strftime('%H:%M')
        except:
            formatted_date = str(b.booking_time).split(' ')[0]
            formatted_time = str(b.booking_time).split(' ')[1] if ' ' in str(b.booking_time) else ''

        bookings_data.append({
            "id": b.id,
            "name": b.customer_name,
            "phone": b.customer_phone,
            "time": formatted_time,
            "date": formatted_date,
            "guests": b.guest_count,
            "status": b.status
        })

    # --- B. REVENUE (Doanh thu) ---
    # Lọc doanh thu theo ngày
    revenue_qs = Revenue.objects.filter(paid_at__date__range=[start_date, end_date])
    
    total_revenue = revenue_qs.aggregate(total=Coalesce(Sum('amount'), 0))['total']
    cash_revenue = revenue_qs.filter(method='cash').aggregate(total=Coalesce(Sum('amount'), 0))['total']
    transfer_revenue = revenue_qs.exclude(method='cash').aggregate(total=Coalesce(Sum('amount'), 0))['total']
    
    # Đếm số đơn đã thanh toán (Dựa trên bảng Doanh thu)
    total_orders = revenue_qs.count()

    # --- C. BEST SELLERS (Giữ nguyên logic cũ) ---
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
        'filter': range_type,
        'revenue': {
            'total': total_revenue,
            'cash': cash_revenue,
            'transfer': transfer_revenue,
            'orders': total_orders
        },
        'bookings': bookings_data,
        'best_sellers': best_sellers_data
    }, status=status.HTTP_200_OK)


@api_view(['DELETE'])
@permission_classes([IsAdminUser]) # Chỉ Admin mới được xóa
def delete_booking(request, pk):
    try:
        booking = Booking.objects.get(pk=pk)
        booking.delete()
        return Response({'success': True, 'message': 'Đã xóa thành công'}, status=status.HTTP_200_OK)
    except Booking.DoesNotExist:
        return Response({'error': 'Không tìm thấy đơn này'}, status=status.HTTP_404_NOT_FOUND)
    
@api_view(['POST'])
@permission_classes([AllowAny])      # Ai cũng được gọi
@authentication_classes([])          # <--- QUAN TRỌNG: Tắt kiểm tra xác thực cho API này
@csrf_exempt                         # Tắt bảo vệ CSRF (tránh lỗi 403 Forbidden)
def login(request):
    """Đăng nhập và lấy token"""
    print("LOG: Đang nhận request login...") # Dòng này để in ra terminal xem request có đến nơi không
    print("Data nhận được:", request.data)   # In ra xem Frontend gửi gì lên

    serializer = LoginSerializer(data=request.data)
    
    if serializer.is_valid():
        username = serializer.validated_data['username']
        password = serializer.validated_data['password']
        
        user = authenticate(username=username, password=password)
        
        if user is not None:
            refresh = RefreshToken.for_user(user)
            display_name = user.first_name if user.first_name else user.username
            role = 'ADMIN' if user.is_superuser else ('STAFF' if user.is_staff else 'CUSTOMER')

            return Response({
                'status': 'success',
                'message': 'Đăng nhập thành công',
                'data': {
                    'token': str(refresh.access_token),
                    'userId': user.id,
                    'fullName': display_name,
                    'role': role
                }
            }, status=status.HTTP_200_OK)
        else:
            print("LOG: Sai mật khẩu hoặc user không tồn tại")
            return Response({'status': 'error', 'message': 'Sai username hoặc password'}, status=status.HTTP_401_UNAUTHORIZED)
    else:
        print("LOG: Serializer lỗi:", serializer.errors)
        return Response({'status': 'error', 'message': 'Dữ liệu không hợp lệ', 'errors': serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

@api_view(['POST'])
def checkout(request, table_id):
    """
    API Thanh toán:
    1. Tìm đơn hàng chờ của bàn đó.
    2. Lưu doanh thu (Revenue) để hiện lên Dashboard.
    3. Chốt đơn hàng (status='completed').
    4. Trả bàn về trạng thái Trống (available).
    """
    try:
        # 1. Tìm bàn và đơn hàng chưa thanh toán
        table = Table.objects.get(pk=table_id)
        order = Order.objects.filter(table=table, status='pending').first()
        
        if not order:
            return Response({'error': 'Bàn này không có đơn nào chưa thanh toán'}, status=status.HTTP_400_BAD_REQUEST)

        # 2. Tính tổng tiền
        total_amount = order.total

        # 3. Lưu Doanh Thu (Quan trọng để hiện số liệu Dashboard)
        Revenue.objects.create(
        amount=total_amount,
        method=request.data.get('method', 'cash'),
        paid_at=timezone.now() # <--- ĐÚNG TÊN LÀ paid_at
        )

        # 4. Cập nhật trạng thái Đơn hàng -> Hoàn thành
        order.status = 'completed'
        order.save()

        # 5. Cập nhật trạng thái Bàn -> Trống (Màu trắng)
        table.status = 'available' 
        table.reserved_at = None
        table.expires_at = None
        table.save()

        return Response({'success': True, 'message': 'Thanh toán thành công!'}, status=status.HTTP_200_OK)

    except Table.DoesNotExist:
        return Response({'error': 'Bàn không tồn tại'}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['GET'])
def get_order_by_table(request, table_id):
    """
    API lấy đơn hàng đang chờ (pending) của một bàn cụ thể.
    Dùng khi bấm vào một bàn trên màn hình POS.
    """
    try:
        # Tìm đơn hàng chưa thanh toán của bàn này
        order = Order.objects.filter(table_id=table_id, status='pending').first()
        
        if order:
            serializer = OrderSerializer(order)
            return Response(serializer.data, status=status.HTTP_200_OK)
        else:
            # Quan trọng: Nếu bàn trống (chưa có đơn), trả về rỗng chứ đừng báo lỗi
            # Để Frontend biết đường mà reset giỏ hàng về 0
            return Response({
                'id': None, 
                'items': [], 
                'total': 0
            }, status=status.HTTP_200_OK)
            
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
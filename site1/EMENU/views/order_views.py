from django.shortcuts import get_object_or_404
from rest_framework import viewsets
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAdminUser
from rest_framework.response import Response
from ..models import Order, OrderItem, Table, Item, Revenue, Notification
from ..serializers import OrderSerializer, TableSerializer
import math
class OrderViewSet(viewsets.ModelViewSet):
    queryset = Order.objects.all().order_by('-id_donhang'); serializer_class = OrderSerializer
    def create(self, request, *args, **kwargs): return create_order(request)

class TableViewSet(viewsets.ModelViewSet):
    queryset = Table.objects.all().order_by('id'); serializer_class = TableSerializer

@api_view(['GET'])
def get_order_by_table(request, table_id):
    try:
        order = Order.objects.filter(table=table_id).exclude(status__in=['paid', 'cancelled']).last()
        return Response(OrderSerializer(order, context={'request': request}).data) if order else Response(None, 200)
    except Exception as e: return Response({'error': str(e)}, 500)

# --- HÀM PHỤ: TÍNH KHOẢNG CÁCH (Haversine) ---
def calculate_distance(lat1, lon1, lat2, lon2):
    R = 6371000 # Bán kính trái đất (mét)
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)

    a = math.sin(delta_phi / 2.0) ** 2 + \
        math.cos(phi1) * math.cos(phi2) * \
        math.sin(delta_lambda / 2.0) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c

# --- HÀM PHỤ: TÍNH KHOẢNG CÁCH (Haversine) ---
def calculate_distance(lat1, lon1, lat2, lon2):
    R = 6371000 # Bán kính trái đất (mét)
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)

    a = math.sin(delta_phi / 2.0) ** 2 + \
        math.cos(phi1) * math.cos(phi2) * \
        math.sin(delta_lambda / 2.0) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c

# --- API TẠO ĐƠN (ĐÃ GỘP CHECK VỊ TRÍ + CỘNG DỒN MÓN) ---
@api_view(['POST'])
def create_order(request):
    try:
        # ==================================================================
        # 🛡️ BƯỚC 1: BẢO MẬT VỊ TRÍ (GEOFENCING)
        # ==================================================================
        
        # Cấu hình tọa độ quán (Thay số thực tế của bạn vào đây)
        SHOP_LAT = 10.824682   
        SHOP_LON = 106.720029
        MAX_DISTANCE = 150    # Cho phép sai số 150 mét
        
        # Lấy tọa độ khách gửi lên từ Frontend
        user_lat = request.data.get('lat')
        user_lon = request.data.get('lon')

        # Debug xem khách gửi gì lên (xem trong Terminal)
        print(f"📡 Khách đang ở: {user_lat}, {user_lon}")

        if not user_lat or not user_lon:
            # Nếu khách dùng tool để order mà không gửi tọa độ -> CHẶN
            return Response({'error': 'Yêu cầu bật Vị trí (GPS) trên thiết bị để đặt món!'}, status=400)

        # Tính khoảng cách
        try:
            dist = calculate_distance(SHOP_LAT, SHOP_LON, float(user_lat), float(user_lon))
        except ValueError:
             return Response({'error': 'Tọa độ GPS không hợp lệ!'}, status=400)

        print(f"📏 Khoảng cách tới quán: {int(dist)} mét")

        if dist > MAX_DISTANCE:
            return Response({'error': f'Bạn đang cách quán {int(dist)}m. Vui lòng lại gần quán để đặt!'}, status=403)

        # ==================================================================
        # 🛒 BƯỚC 2: XỬ LÝ ĐƠN HÀNG (Logic cộng dồn món)
        # ==================================================================
        
        data = request.data
        table_id = data.get('table_id') or data.get('tableId')
        items_data = data.get('items') or []
        
        if not table_id: return Response({'error': 'Thiếu ID bàn'}, 400)
        
        table = get_object_or_404(Table, pk=table_id)
        
        # Tìm đơn hàng hiện tại của bàn (chưa thanh toán, chưa hủy)
        order = Order.objects.filter(table=table).exclude(status__in=['paid', 'cancelled']).last()
        if not order:
            order = Order.objects.create(table=table, status='pending', total=0)
        
        if table.status == 'available':
            table.status = 'occupied'; table.save()

        # --- XỬ LÝ MÓN ĂN ---
        for i in items_data:
            # 1. Lấy ID chuẩn
            pid = i.get('product_id') or i.get('itemId') or i.get('id') 
            if not pid: pid = i.get('id') # Fallback
            if not pid: continue 

            # 2. Tìm món trong Menu
            item = Item.objects.filter(pk=pid).first()
            if not item: 
                return Response({'error': f"Lỗi: Không tìm thấy món ID={pid}"}, 400)

            # 3. Lấy số lượng và ghi chú
            qty = int(i.get('quantity', 1))
            note = i.get('note', '')

            # 4. Kiểm tra món này đã có trong đơn chưa (và chưa ra món)
            exist = OrderItem.objects.filter(order=order, item=item, is_served=False).first()
            
            if exist:
                # 🔥 LOGIC QUAN TRỌNG: CỘNG DỒN SỐ LƯỢNG (+=)
                exist.quantity += qty 
                
                # Gộp ghi chú nếu có
                if note: 
                    exist.note = f"{exist.note}, {note}" if exist.note else note
                
                exist.save()
            else:
                # Nếu chưa có thì tạo mới
                OrderItem.objects.create(order=order, item=item, quantity=qty, note=note)

        # 5. Tính lại tổng tiền (Loop qua DB để chính xác tuyệt đối)
        total_price = 0
        current_items = OrderItem.objects.filter(order=order)
        for line in current_items:
            total_price += line.quantity * line.item.price

        order.total = total_price
        order.save()
        
        return Response(OrderSerializer(order, context={'request': request}).data, status=201)
        
    except Exception as e:
        return Response({'error': str(e)}, status=500)

@api_view(['POST'])
@permission_classes([IsAdminUser])
def checkout(request, table_id):
    try:
        table = get_object_or_404(Table, id=table_id)
        order = Order.objects.filter(table=table).exclude(status__in=['paid', 'cancelled', 'served']).last()
        if not order: order = Order.objects.filter(table=table).exclude(status='paid').last()
        if not order: return Response({'error': 'Không có đơn'}, 400)

        method = request.data.get('payment_method', 'cash')
        Revenue.objects.create(order=order, method=method, amount=order.total)
        order.status = 'paid'; order.save()
        table.status = 'available'; table.save()
        Notification.objects.filter(table=table).delete()
        return Response({'message': 'Thanh toán thành công'})
    except Exception as e: return Response({'error': str(e)}, 500)

@api_view(['POST'])
@permission_classes([IsAdminUser])
def cancel_order(request):
    try:
        table_id = request.data.get('table_id')
        if not table_id: return Response({'error': 'Thiếu ID'}, 400)
        Order.objects.filter(table_id=table_id).exclude(status='paid').delete()
        Table.objects.filter(id=table_id).update(status='available', reserved_at=None, expires_at=None)
        Notification.objects.filter(table_id=table_id).delete()
        return Response({'message': 'Đã hủy đơn'})
    except Exception as e: return Response({'error': str(e)}, 500)

@api_view(['POST'])
def request_payment(request):
    try:
        table = Table.objects.get(id=request.data.get('table_id'))
        Notification.objects.create(table=table, message=f"{table.number} yêu cầu thanh toán", is_read=False)
        return Response({'success': True})
    except: return Response({'error': 'Lỗi'}, 500)

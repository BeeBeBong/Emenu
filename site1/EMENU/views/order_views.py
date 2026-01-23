from django.shortcuts import get_object_or_404
from rest_framework import viewsets
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAdminUser
from rest_framework.response import Response
from ..models import Order, OrderItem, Table, Item, Revenue, Notification
from ..serializers import OrderSerializer, TableSerializer

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

@api_view(['POST'])
def create_order(request):
    try:
        data = request.data
        table_id = data.get('table_id') or data.get('tableId')
        items_data = data.get('items') or []
        
        if not table_id: return Response({'error': 'Thiếu ID bàn'}, 400)
        
        table = get_object_or_404(Table, pk=table_id)
        
        # Tìm đơn hàng hiện tại của bàn
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
                # Bỏ qua hoặc báo lỗi tùy logic, ở đây ta return lỗi để dễ debug
                return Response({'error': f"Lỗi: Không tìm thấy món ID={pid}"}, 400)

            # 3. Lấy số lượng gửi lên (thường là 1)
            qty = int(i.get('quantity', 1))
            note = i.get('note', '')

            # 4. Kiểm tra món này đã có trong đơn chưa (và chưa ra món)
            exist = OrderItem.objects.filter(order=order, item=item, is_served=False).first()
            
            if exist:
                # 🔥 SỬA QUAN TRỌNG: CỘNG DỒN SỐ LƯỢNG (+=) THAY VÌ GHI ĐÈ (=)
                exist.quantity += qty 
                
                # Gộp ghi chú nếu có (Ví dụ: "Không hành" + "Ít đá")
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
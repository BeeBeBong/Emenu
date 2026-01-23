import base64, os
from datetime import timedelta
from django.utils import timezone
from django.db.models import Sum
from django.db.models.functions import Coalesce
from django.shortcuts import get_object_or_404
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAdminUser, AllowAny
from rest_framework.response import Response
from ..models import Table, Revenue, OrderItem, Item, Booking, Notification
from ..serializers import NotificationSerializer, TableSerializer

@api_view(['POST'])
def reserve_table(request, id_ban):
    table = get_object_or_404(Table, id=id_ban)
    if table.status != 'available': return Response({'error': 'Bàn bận'}, 400)
    table.status = 'reserved'; table.reserved_at = timezone.now(); table.save()
    return Response(TableSerializer(table).data)

@api_view(['GET'])
def get_notifications(request):
    return Response(NotificationSerializer(Notification.objects.all().order_by('-created_at'), many=True).data)

@api_view(['GET'])
def get_dashboard_stats(request):
    try:
        range_type = request.query_params.get('range', 'today'); today = timezone.now().date()
        filter_kwargs = {'paid_at__date': today}
        if range_type == 'yesterday': filter_kwargs = {'paid_at__date': today - timedelta(days=1)}
        elif range_type == 'month': filter_kwargs = {'paid_at__date__gte': today.replace(day=1)}
        elif range_type == 'year': filter_kwargs = {'paid_at__date__gte': today.replace(month=1, day=1)}

        revenues = Revenue.objects.filter(**filter_kwargs)
        total_rev = revenues.aggregate(t=Coalesce(Sum('amount'), 0))['t']
        cash_rev = revenues.filter(method='cash').aggregate(t=Coalesce(Sum('amount'), 0))['t']
        transfer_rev = revenues.filter(method='transfer').aggregate(t=Coalesce(Sum('amount'), 0))['t']

        top = OrderItem.objects.values('item').annotate(total=Sum('quantity')).order_by('-total')[:5]
        best_sellers = []
        for t in top:
            try:
                i = Item.objects.get(pk=t['item'])
                img = ""
                if i.image and os.path.exists(i.image.path):
                    with open(i.image.path, "rb") as f:
                        img = f"data:image/jpeg;base64,{base64.b64encode(f.read()).decode('utf-8')}"
                else: img = "https://images.unsplash.com/photo-1579871494447-9811cf80d66c?q=80&w=200"
                best_sellers.append({'id': i.id, 'name': i.name, 'price': i.price, 'img': img, 'sold_count': t['total']})
            except: continue

        bookings = Booking.objects.filter(status='pending').order_by('-created_at')[:10]
        bookings_data = []
        
        for b in bookings:
            # 1. Format ngày giờ thành dd/mm/yyyy HH:MM
            # Lưu ý: Cần import method strftime nếu chưa có (thực ra nó thuộc về datetime object có sẵn)
            fmt_time = b.booking_time.strftime("%d/%m/%Y %H:%M") if b.booking_time else ""
            
            bookings_data.append({
                "id": b.id,
                "customer_name": b.customer_name,
                "name": b.customer_name,  # <--- THÊM DÒNG NÀY: Để Frontend hiển thị được cột "Tên khách"
                "phone": b.customer_phone,
                "time": fmt_time,         # <--- SỬA DÒNG NÀY: Trả về ngày giờ đã format dễ đọc
                "guests": b.guest_count,
                "status": b.status
            })
        # --------------------

        return Response({
            "revenue": {"total": total_rev, "cash": cash_rev, "transfer": transfer_rev, "orders": revenues.count()},
            "best_sellers": best_sellers, 
            "bookings": bookings_data # Trả về data mới đã sửa
        })
        
    except Exception as e:
        print("Lỗi Dashboard:", e)
        return Response({'error': str(e)}, status=500)

@api_view(['POST'])
@permission_classes([AllowAny])
def create_booking(request):
    try:
        d = request.data
        t = f"{d.get('date')} {d.get('time')}" if d.get('date') else d.get('booking_time')
        Booking.objects.create(customer_name=d.get('name') or d.get('ho_ten'), customer_phone=d.get('phone') or d.get('sdt'), booking_time=t, guest_count=d.get('guests', 1), note=d.get('note', ''))
        return Response({'success': True}, 201)
    except Exception as e: return Response({'error': str(e)}, 500)

@api_view(['DELETE'])
@permission_classes([IsAdminUser])
def delete_booking(request, pk):
    get_object_or_404(Booking, pk=pk).delete(); return Response({'success': True})
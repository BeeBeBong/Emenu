from rest_framework import serializers
from django.utils import timezone
from ..models import Order, OrderItem, Table

class OrderItemSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(source='id_chitiet', read_only=True)
    product_id = serializers.IntegerField(source='item.pk', read_only=True)
    name = serializers.CharField(source='item.name', read_only=True)
    price = serializers.IntegerField(source='item.price', read_only=True)
    image = serializers.SerializerMethodField()
    isServed = serializers.BooleanField(source='is_served', read_only=True)
    
    class Meta: 
        model = OrderItem
        fields = ['id', 'product_id', 'name', 'price', 'quantity', 'note', 'isServed', 'image']

    def get_img(self, obj):
        try:
            if obj.image:
                # Chỉ trả về '/media/menu/anh.jpg'
                # KHÔNG trả về http://localhost... hay http://ngrok...
                return obj.image.url 
        except: pass
        return ""
class OrderSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(source='id_donhang', read_only=True)
    tableId = serializers.IntegerField(source='table.pk', read_only=True)
    tableNumber = serializers.CharField(source='table.number', read_only=True)
    createdAt = serializers.DateTimeField(source='created_at', read_only=True)
    total = serializers.IntegerField(read_only=True)
    status = serializers.CharField(read_only=True)
    
    # 🔥 THAY ĐỔI: Dùng SerializerMethodField để tự xử lý logic gộp món
    items = serializers.SerializerMethodField()

    class Meta: 
        model = Order
        fields = ['id', 'tableId', 'tableNumber', 'total', 'status', 'createdAt', 'items']

    # 👇 HÀM MỚI: Tự động cộng dồn các món giống nhau
    def get_items(self, obj):
        all_items = obj.items.all()
        grouped = {} # Dictionary để gom nhóm: { product_id: {data...} }
        
        for item in all_items:
            pid = item.item.id
            
            # Nếu món này chưa có trong danh sách gộp -> Thêm mới
            if pid not in grouped:
                # Lấy link ảnh
                img_url = ""
                try:
                    if item.item.image:
                        req = self.context.get('request')
                        if req: img_url = req.build_absolute_uri(item.item.image.url)
                        else: img_url = item.item.image.url
                except: pass

                grouped[pid] = {
                    'id': item.id_chitiet,
                    'product_id': pid,
                    'name': item.item.name,
                    'price': item.item.price,
                    'quantity': item.quantity, # Khởi tạo số lượng
                    'note': item.note,
                    'isServed': item.is_served,
                    'image': img_url
                }
            else:
                # Nếu món này đã có -> CỘNG DỒN SỐ LƯỢNG
                grouped[pid]['quantity'] += item.quantity
                
                # Gộp luôn ghi chú (nếu có)
                if item.note:
                    if grouped[pid]['note']: 
                        grouped[pid]['note'] += f", {item.note}"
                    else: 
                        grouped[pid]['note'] = item.note
        
        # Trả về danh sách đã gộp gọn gàng
        return list(grouped.values())

class TableSerializer(serializers.ModelSerializer):
    current_order_total = serializers.SerializerMethodField()
    duration = serializers.SerializerMethodField()
    class Meta: model = Table; fields = '__all__'
    def get_current_order_total(self, obj):
        order = Order.objects.filter(table=obj, status='pending').last()
        return order.total if order else 0
    def get_duration(self, obj):
        order = Order.objects.filter(table=obj, status='pending').last()
        if order:
            delta = timezone.now() - order.created_at
            m = int(delta.total_seconds()) // 60
            h = m // 60
            return f"{h}h {m%60}p" if h > 0 else f"{m}p"
        return ""
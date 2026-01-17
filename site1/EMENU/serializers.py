from rest_framework import serializers
from django.contrib.auth.models import User
from .models import Category, Item, Table, Order, OrderItem, Revenue, Booking, Notification
from django.utils import timezone

# 1. USER
class UserSerializer(serializers.ModelSerializer):
    role = serializers.SerializerMethodField()
    name = serializers.SerializerMethodField()
    class Meta:
        model = User
        fields = ['id', 'username', 'name', 'role']
    def get_role(self, obj):
        if obj.is_superuser: return 'ADMIN'
        if obj.is_staff: return 'STAFF'
        return 'CUSTOMER'
    def get_name(self, obj):
        return obj.first_name if obj.first_name else obj.username

# 2. CATEGORY & ITEM
class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ['id', 'name']

class ItemSerializer(serializers.ModelSerializer):
    categoryName = serializers.CharField(source='category.name', read_only=True)
    img = serializers.SerializerMethodField() # <--- Giữ 'img' cho Menu bên phải chạy đúng

    class Meta:
        model = Item
        fields = ['id', 'name', 'price', 'categoryName', 'img']
    
    def get_img(self, obj):
        request = self.context.get('request')
        if obj.image:
            if request:
                return request.build_absolute_uri(obj.image.url)
            return obj.image.url
        return None

# 3. ORDER ITEM (QUAN TRỌNG: SỬA Ở ĐÂY)
class OrderItemSerializer(serializers.ModelSerializer):
    itemId = serializers.IntegerField(source='item.id', read_only=True)
    name = serializers.CharField(source='item.name', read_only=True)
    price = serializers.IntegerField(source='item.price', read_only=True)
    
    # 👇 TRẢ VỀ CẢ 2 TÊN ĐỂ FRONTEND KHÔNG BỊ LỖI
    image = serializers.SerializerMethodField() 
    img = serializers.SerializerMethodField()
    
    isServed = serializers.BooleanField(source='is_served', read_only=True)
    
    class Meta:
        model = OrderItem
        fields = ['id', 'itemId', 'name', 'price', 'quantity', 'note', 'isServed', 'image', 'img']

    def get_image(self, obj):
        return self.get_img_url(obj)

    def get_img(self, obj):
        return self.get_img_url(obj)

    # Hàm dùng chung để lấy link ảnh
    def get_img_url(self, obj):
        request = self.context.get('request')
        if obj.item and obj.item.image:
            if request:
                return request.build_absolute_uri(obj.item.image.url)
            return obj.item.image.url
        return None

# 4. ORDER & TABLE (Giữ nguyên)
class OrderSerializer(serializers.ModelSerializer):
    tableId = serializers.IntegerField(source='table.id', read_only=True)
    tableNumber = serializers.CharField(source='table.number', read_only=True)
    createdAt = serializers.DateTimeField(source='created_at', read_only=True)
    items = OrderItemSerializer(many=True, read_only=True)
    class Meta:
        model = Order
        fields = ['id', 'tableId', 'tableNumber', 'total', 'status', 'createdAt', 'items']

class TableSerializer(serializers.ModelSerializer):
    current_order_total = serializers.SerializerMethodField()
    duration = serializers.SerializerMethodField()
    class Meta:
        model = Table
        fields = '__all__'
    def get_current_order_total(self, obj):
        order = Order.objects.filter(table=obj, status='pending').last()
        return order.total if order else 0
    def get_duration(self, obj):
        order = Order.objects.filter(table=obj, status='pending').last()
        if order:
            delta = timezone.now() - order.created_at
            total_seconds = int(delta.total_seconds())
            hours = total_seconds // 3600
            minutes = (total_seconds % 3600) // 60
            if hours > 0: return f"{hours}h {minutes}p"
            return f"{minutes}p"
        return ""

# 5. OTHERS
class RevenueSerializer(serializers.ModelSerializer):
    orderId = serializers.IntegerField(source='order.id', read_only=True)
    paidAt = serializers.DateTimeField(source='paid_at', read_only=True)
    class Meta:
        model = Revenue
        fields = ['id', 'orderId', 'method', 'amount', 'paidAt']

class BookingSerializer(serializers.ModelSerializer):
    class Meta:
        model = Booking
        fields = '__all__'

class LoginSerializer(serializers.Serializer):
    username = serializers.CharField(max_length=150)
    password = serializers.CharField(write_only=True)

class NotificationSerializer(serializers.ModelSerializer):
    # Tự định nghĩa các trường để khớp với JSON Frontend yêu cầu
    tableName = serializers.SerializerMethodField()
    status = serializers.SerializerMethodField()
    type = serializers.SerializerMethodField()

    class Meta:
        model = Notification
        # Chỉ trả về đúng 4 trường Frontend cần
        fields = ['id', 'type', 'tableName', 'status', 'created_at'] 
        # (Mình giữ thêm created_at để Frontend có thể sắp xếp nếu cần, nếu họ cứng nhắc không cần thì bạn xóa đi)

    def get_tableName(self, obj):
        # Trả về chuỗi "Bàn số 5" thay vì chỉ trả về ID
        if obj.table:
            return f" {obj.table.number}" # Giả sử model Table có trường 'number'
        return "Không xác định"
    
    def get_status(self, obj):
        # Map từ boolean (True/False) sang string ("read"/"unread")
        return "read" if obj.is_read else "unread"

    def get_type(self, obj):
        # Hiện tại bạn chỉ có 1 loại thông báo là Yêu cầu thanh toán
        # Nên mình hardcode luôn. Sau này có thêm loại khác thì sửa Model sau.
        return "PAYMENT_REQUEST"
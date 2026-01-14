from rest_framework import serializers
from django.contrib.auth.models import User
from .models import Category, Item, Table, Order, OrderItem, Revenue, Booking
from django.utils import timezone

# ========== USER SERIALIZER ==========
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

# ========== TABLE SERIALIZER (QUAN TRỌNG NHẤT) ==========
class TableSerializer(serializers.ModelSerializer):
    current_order_total = serializers.SerializerMethodField()
    duration = serializers.SerializerMethodField() # <--- Thêm trường tính thời gian

    class Meta:
        model = Table
        fields = '__all__'

    def get_current_order_total(self, obj):
        # Logic lấy tiền (Đã test OK)
        last_order = Order.objects.filter(table=obj).order_by('-created_at').first()
        if last_order and str(last_order.status).lower() == 'pending':
            return last_order.total
        return 0

    def get_duration(self, obj):
        # Logic tính thời gian: Lấy giờ hiện tại trừ giờ tạo đơn
        last_order = Order.objects.filter(table=obj).order_by('-created_at').first()
        
        if last_order and str(last_order.status).lower() == 'pending':
            # Tính khoảng cách thời gian
            delta = timezone.now() - last_order.created_at
            total_seconds = int(delta.total_seconds())
            
            hours = total_seconds // 3600
            minutes = (total_seconds % 3600) // 60
            
            # Trả về chuỗi đẹp: "1h 30p" hoặc "45p"
            if hours > 0:
                return f"{hours}h {minutes}p"
            return f"{minutes}p"
            
        return "" # Bàn trống thì không hiện giờ

# ========== CÁC SERIALIZER KHÁC (GIỮ NGUYÊN) ==========
class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ['id', 'name']

class ItemSerializer(serializers.ModelSerializer):
    category = serializers.CharField(source='category.name', read_only=True)
    class Meta:
        model = Item
        fields = ['id', 'name', 'price', 'category', 'image']
    
    def to_representation(self, instance):
        data = super().to_representation(instance)
        img_url = ''
        if instance.image:
            request = self.context.get('request')
            if request:
                img_url = request.build_absolute_uri(instance.image.url)
            else:
                img_url = str(instance.image.url)
        return {
            'id': data['id'], 
            'name': data['name'], 
            'price': data['price'], 
            'img': img_url, 
            'category': data['category']
        }

class OrderItemSerializer(serializers.ModelSerializer):
    itemId = serializers.IntegerField(source='item.id', read_only=True)
    name = serializers.CharField(source='item.name', read_only=True)
    price = serializers.IntegerField(source='item.price', read_only=True)
    isServed = serializers.BooleanField(source='is_served', read_only=True)
    
    class Meta:
        model = OrderItem
        fields = ['id', 'itemId', 'name', 'price', 'quantity', 'note', 'isServed']

class OrderSerializer(serializers.ModelSerializer):
    tableId = serializers.IntegerField(source='table.id', read_only=True)
    tableNumber = serializers.CharField(source='table.number', read_only=True) # Sửa lại nếu cột tên bàn là tên khác
    createdAt = serializers.DateTimeField(source='created_at', read_only=True)
    items = OrderItemSerializer(many=True, read_only=True)
    
    class Meta:
        model = Order
        fields = ['id', 'tableId', 'tableNumber', 'total', 'status', 'createdAt', 'items']

class RevenueSerializer(serializers.ModelSerializer):
    orderId = serializers.IntegerField(source='order.id', read_only=True)
    paidAt = serializers.DateTimeField(source='paid_at', read_only=True)
    
    class Meta:
        model = Revenue
        fields = ['id', 'orderId', 'method', 'amount', 'paidAt']

class LoginSerializer(serializers.Serializer):
    username = serializers.CharField(max_length=150)
    password = serializers.CharField(write_only=True)
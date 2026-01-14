from rest_framework import serializers
from django.contrib.auth.models import User  # <--- Import thêm model User
from .models import Category, Item, Table, Order, OrderItem, Revenue

# ========== USER SERIALIZER (MỚI THÊM) ==========
class UserSerializer(serializers.ModelSerializer):
    """
    Serializer này giúp lọc dữ liệu User gọn gàng để trả về cho Frontend.
    Chỉ lấy: id, username, name (tên hiển thị), role (vai trò).
    Bỏ qua: password, email, last_login, date_joined...
    """
    role = serializers.SerializerMethodField()
    name = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ['id', 'username', 'name', 'role'] # Chỉ gửi 4 trường này

    def get_role(self, obj):
        # Tự động xác định vai trò dựa trên cờ is_superuser/is_staff
        if obj.is_superuser:
            return 'ADMIN'
        if obj.is_staff:
            return 'STAFF'
        return 'CUSTOMER'

    def get_name(self, obj):
        # Ưu tiên lấy Tên thật (First Name), nếu không có thì lấy Username
        return obj.first_name if obj.first_name else obj.username

# ========== CÁC SERIALIZER CŨ (GIỮ NGUYÊN) ==========

class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ['id', 'name']
    
    def to_representation(self, instance):
        data = super().to_representation(instance)
        return {
            'id': data['id'],
            'name': data['name']
        }

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

class TableSerializer(serializers.ModelSerializer):
    reservedAt = serializers.DateTimeField(source='reserved_at', read_only=True)
    expiresAt = serializers.DateTimeField(source='expires_at', read_only=True)
    
    class Meta:
        model = Table
        fields = ['id', 'number', 'status', 'reservedAt', 'expiresAt']
    
    def to_representation(self, instance):
        data = super().to_representation(instance)
        return {
            'id': data['id'],
            'number': data['number'],
            'status': data['status'],
            'reservedAt': data.get('reservedAt'),
            'expiresAt': data.get('expiresAt')
        }

class OrderItemSerializer(serializers.ModelSerializer):
    itemId = serializers.IntegerField(source='item.id', read_only=True)
    name = serializers.CharField(source='item.name', read_only=True)
    price = serializers.IntegerField(source='item.price', read_only=True)
    isServed = serializers.BooleanField(source='is_served', read_only=True)
    
    class Meta:
        model = OrderItem
        fields = ['id', 'itemId', 'name', 'price', 'quantity', 'note', 'isServed']
    
    def to_representation(self, instance):
        data = super().to_representation(instance)
        return {
            'id': data['id'],
            'itemId': data['itemId'],
            'name': data['name'],
            'price': data['price'],
            'quantity': data['quantity'],
            'note': data.get('note', ''),
            'isServed': data.get('isServed', False)
        }

class OrderSerializer(serializers.ModelSerializer):
    tableId = serializers.IntegerField(source='table.id', read_only=True)
    tableNumber = serializers.CharField(source='table.number', read_only=True)
    createdAt = serializers.DateTimeField(source='created_at', read_only=True)
    items = OrderItemSerializer(many=True, read_only=True)
    
    class Meta:
        model = Order
        fields = ['id', 'tableId', 'tableNumber', 'total', 'status', 'createdAt', 'items']
    
    def to_representation(self, instance):
        data = super().to_representation(instance)
        return {
            'id': data['id'],
            'tableId': data['tableId'],
            'tableNumber': data['tableNumber'],
            'total': data.get('total', 0),
            'status': data['status'],
            'createdAt': data['createdAt'],
            'items': data.get('items', [])
        }

class RevenueSerializer(serializers.ModelSerializer):
    orderId = serializers.IntegerField(source='order.id', read_only=True)
    paidAt = serializers.DateTimeField(source='paid_at', read_only=True)
    
    class Meta:
        model = Revenue
        fields = ['id', 'orderId', 'method', 'amount', 'paidAt']
    
    def to_representation(self, instance):
        data = super().to_representation(instance)
        return {
            'id': data['id'],
            'orderId': data['orderId'],
            'method': data['method'],
            'amount': data['amount'],
            'paidAt': data['paidAt']
        }

class LoginSerializer(serializers.Serializer):
    username = serializers.CharField(max_length=150)
    password = serializers.CharField(write_only=True)
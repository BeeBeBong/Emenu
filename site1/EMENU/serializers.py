from rest_framework import serializers
from .models import Category, Item, Table, Order, OrderItem, Revenue

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
        # Xử lý URL hình ảnh nếu có
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

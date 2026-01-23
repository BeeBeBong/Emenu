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
    class Meta: model = OrderItem; fields = ['id', 'product_id', 'name', 'price', 'quantity', 'note', 'isServed', 'image']
    def get_image(self, obj):
        try:
            if obj.item and obj.item.image:
                req = self.context.get('request')
                return req.build_absolute_uri(obj.item.image.url) if req else obj.item.image.url
        except: pass
        return ""

class OrderSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(source='id_donhang', read_only=True)
    tableId = serializers.IntegerField(source='table.pk', read_only=True)
    tableNumber = serializers.CharField(source='table.number', read_only=True)
    createdAt = serializers.DateTimeField(source='created_at', read_only=True)
    total = serializers.IntegerField(read_only=True)
    status = serializers.CharField(read_only=True)
    items = OrderItemSerializer(many=True, read_only=True)
    class Meta: model = Order; fields = ['id', 'tableId', 'tableNumber', 'total', 'status', 'createdAt', 'items']

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
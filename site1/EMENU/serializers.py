from rest_framework import serializers
from django.contrib.auth.models import User
from .models import Category, Item, Table, Order, OrderItem, Revenue, Booking, Notification
import base64
import uuid
import os
import requests 
from django.core.files.base import ContentFile
from urllib.parse import urlparse
from django.utils import timezone

# ==========================================
# 0. HELPER: BỘ XỬ LÝ ẢNH ĐA NĂNG (BẮT BUỘC CÓ)
# ==========================================
class FlexibleImageField(serializers.ImageField):
    """
    Field này giúp Django hiểu được ảnh dù gửi dưới dạng:
    1. File upload truyền thống.
    2. Chuỗi Base64 (từ Frontend Admin).
    3. Link Online (http://...).
    """
    def to_internal_value(self, data):
        # 1. Nếu là Link Online (http://...)
        if isinstance(data, str) and data.startswith('http'):
            try:
                response = requests.get(data, timeout=10)
                if response.status_code == 200:
                    parsed = urlparse(data)
                    file_name = os.path.basename(parsed.path) or f"{uuid.uuid4()}.jpg"
                    data = ContentFile(response.content, name=file_name)
                else:
                    raise serializers.ValidationError(f"Lỗi tải ảnh từ link: {response.status_code}")
            except Exception as e:
                raise serializers.ValidationError(f"Lỗi tải ảnh: {str(e)}")

        # 2. Nếu là Base64 (data:image/...) - Frontend gửi cái này!
        elif isinstance(data, str) and 'data:' in data and ';base64,' in data:
            try:
                header, img_str = data.split(';base64,')
                decoded_file = base64.b64decode(img_str)
                file_extension = header.split('/')[-1] if '/' in header else 'jpg'
                file_name = f"{uuid.uuid4()}.{file_extension}"
                data = ContentFile(decoded_file, name=file_name)
            except TypeError:
                self.fail('invalid_image')

        # 3. Trả về cho Django xử lý tiếp
        return super().to_internal_value(data)

# ==========================================
# 1. USER & AUTH
# ==========================================
class UserSerializer(serializers.ModelSerializer):
    role = serializers.SerializerMethodField()
    name = serializers.SerializerMethodField()
    class Meta:
        model = User
        fields = ['id', 'username', 'name', 'role']
    def get_role(self, obj):
        return 'ADMIN' if obj.is_superuser else ('STAFF' if obj.is_staff else 'CUSTOMER')
    def get_name(self, obj):
        return obj.first_name if obj.first_name else obj.username

class LoginSerializer(serializers.Serializer):
    username = serializers.CharField(max_length=150)
    password = serializers.CharField(write_only=True)

# ==========================================
# 2. CATEGORY & ITEM
# ==========================================
class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ['id', 'name']

# --- A. Serializer để XEM (Không đổi) ---
class ItemSerializer(serializers.ModelSerializer):
    category_name = serializers.SerializerMethodField()
    img = serializers.SerializerMethodField() 

    class Meta:
        model = Item
        fields = ['id', 'name', 'price', 'category_name', 'img', 'category']

    def get_category_name(self, obj):
        return obj.category.name if obj.category else "Khác"

    def get_img(self, obj):
        try:
            if obj.image and hasattr(obj.image, 'path') and os.path.exists(obj.image.path):
                with open(obj.image.path, "rb") as image_file:
                    encoded = base64.b64encode(image_file.read()).decode('utf-8')
                    return f"data:image/jpeg;base64,{encoded}"
            return "https://images.unsplash.com/photo-1579871494447-9811cf80d66c?q=80&w=400"
        except: return ""

# --- B. Serializer để THÊM/SỬA (Dùng FlexibleImageField) ---
class ProductFormSerializer(serializers.ModelSerializer):
    category = serializers.CharField(required=True)
    
    # 👇 QUAN TRỌNG NHẤT: Dùng cái này để nhận Base64
    image = FlexibleImageField(required=False, allow_null=True)

    class Meta:
        model = Item
        fields = ['id', 'name', 'price', 'category', 'image']

    def validate_category(self, value):
        if str(value).isdigit():
            try: return Category.objects.get(id=int(value))
            except Category.DoesNotExist: raise serializers.ValidationError(f"ID {value} không tồn tại.")
        try: return Category.objects.get(name=value)
        except Category.DoesNotExist:
            first = Category.objects.first()
            if first: return first
            raise serializers.ValidationError(f"Không tìm thấy nhóm: {value}")

# ==========================================
# 3. ORDER & TABLE
# ==========================================
class OrderItemSerializer(serializers.ModelSerializer):
    itemId = serializers.IntegerField(source='item.id', read_only=True)
    name = serializers.CharField(source='item.name', read_only=True)
    price = serializers.IntegerField(source='item.price', read_only=True)
    image = serializers.SerializerMethodField()
    img = serializers.SerializerMethodField()
    isServed = serializers.BooleanField(source='is_served', read_only=True)
    
    class Meta:
        model = OrderItem
        fields = ['id', 'itemId', 'name', 'price', 'quantity', 'note', 'isServed', 'image', 'img']

    def get_image_base64(self, obj):
        try:
            if obj.item and obj.item.image and hasattr(obj.item.image, 'path') and os.path.exists(obj.item.image.path):
                with open(obj.item.image.path, "rb") as f:
                    encoded = base64.b64encode(f.read()).decode('utf-8')
                    return f"data:image/jpeg;base64,{encoded}"
        except: pass
        return "https://images.unsplash.com/photo-1579871494447-9811cf80d66c?q=80&w=200"
    def get_image(self, obj): return self.get_image_base64(obj)
    def get_img(self, obj): return self.get_image_base64(obj)

class OrderSerializer(serializers.ModelSerializer):
    tableId = serializers.IntegerField(source='table.id', read_only=True)
    tableNumber = serializers.CharField(source='table.number', read_only=True)
    createdAt = serializers.DateTimeField(source='created_at', read_only=True)
    items = OrderItemSerializer(source='order_items', many=True, read_only=True)
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

# ==========================================
# 4. OTHERS
# ==========================================
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

class NotificationSerializer(serializers.ModelSerializer):
    tableName = serializers.SerializerMethodField()
    status = serializers.SerializerMethodField()
    type = serializers.SerializerMethodField()
    class Meta:
        model = Notification
        fields = ['id', 'type', 'tableName', 'status', 'created_at'] 
    def get_tableName(self, obj):
        if obj.table: return f" {obj.table.number}"
        return "Không xác định"
    def get_status(self, obj): return "read" if obj.is_read else "unread"
    def get_type(self, obj): return "PAYMENT_REQUEST"
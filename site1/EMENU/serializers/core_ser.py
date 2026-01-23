from rest_framework import serializers
from django.contrib.auth.models import User
from ..models import Category, Item
import base64, uuid, os, requests
from django.core.files.base import ContentFile
from urllib.parse import urlparse

class FlexibleImageField(serializers.ImageField):
    def to_internal_value(self, data):
        if isinstance(data, str) and data.startswith('http'):
            try:
                response = requests.get(data, timeout=10)
                if response.status_code == 200:
                    parsed = urlparse(data)
                    file_name = os.path.basename(parsed.path) or f"{uuid.uuid4()}.jpg"
                    data = ContentFile(response.content, name=file_name)
                else: raise serializers.ValidationError(f"Lỗi link: {response.status_code}")
            except Exception as e: raise serializers.ValidationError(str(e))
        elif isinstance(data, str) and 'data:' in data and ';base64,' in data:
            try:
                header, img_str = data.split(';base64,')
                ext = header.split('/')[-1] if '/' in header else 'jpg'
                data = ContentFile(base64.b64decode(img_str), name=f"{uuid.uuid4()}.{ext}")
            except: self.fail('invalid_image')
        return super().to_internal_value(data)

class UserSerializer(serializers.ModelSerializer):
    role = serializers.SerializerMethodField()
    name = serializers.SerializerMethodField()
    class Meta: model = User; fields = ['id', 'username', 'name', 'role']
    def get_role(self, obj): return 'ADMIN' if obj.is_superuser else ('STAFF' if obj.is_staff else 'CUSTOMER')
    def get_name(self, obj): return obj.first_name or obj.username

class LoginSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField(write_only=True)

class CategorySerializer(serializers.ModelSerializer):
    class Meta: model = Category; fields = ['id', 'name']

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
            if obj.image:
                # Chỉ trả về '/media/menu/anh.jpg'
                # KHÔNG trả về http://localhost... hay http://ngrok...
                return obj.image.url 
        except: pass
        return ""
class ProductFormSerializer(serializers.ModelSerializer):
    category = serializers.CharField()
    image = FlexibleImageField(required=False, allow_null=True)
    class Meta: model = Item; fields = ['id', 'name', 'price', 'category', 'image']
    def validate_category(self, value):
        if str(value).isdigit():
            try: return Category.objects.get(id=int(value))
            except: raise serializers.ValidationError(f"ID {value} lỗi.")
        try: return Category.objects.get(name=value)
        except: 
            first = Category.objects.first()
            if first: return first
            raise serializers.ValidationError(f"Không tìm thấy nhóm: {value}")
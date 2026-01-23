from django.shortcuts import render
from django.contrib.auth import authenticate
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.models import User
from rest_framework import viewsets
from rest_framework.decorators import api_view, permission_classes, authentication_classes
from rest_framework.permissions import AllowAny, IsAdminUser
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from ..models import Category, Item
from ..serializers import LoginSerializer, CategorySerializer, ItemSerializer, ProductFormSerializer
def get_Emenu(request): return render(request, 'Emenu.html')

@api_view(['POST'])
@permission_classes([AllowAny])
@authentication_classes([])
@csrf_exempt
def login(request):
    serializer = LoginSerializer(data=request.data)
    if serializer.is_valid():
        user = authenticate(username=serializer.validated_data['username'], password=serializer.validated_data['password'])
        if user:
            refresh = RefreshToken.for_user(user)
            role = 'ADMIN' if user.is_superuser else ('STAFF' if user.is_staff else 'CUSTOMER')
            name = user.first_name or user.username
            return Response({'status': 'success', 'data': {'token': str(refresh.access_token), 'userId': user.id, 'fullName': name, 'role': role}})
        return Response({'message': 'Sai thông tin'}, 401)
    return Response(serializer.errors, 400)

@api_view(['GET'])
def get_current_user(request):
    u = request.user
    if u.is_authenticated:
        role = 'ADMIN' if u.is_superuser else ('STAFF' if u.is_staff else 'CUSTOMER')
        return Response({'status': 'success', 'data': {'userId': u.id, 'fullName': u.first_name or u.username, 'role': role, 'email': u.email}})
    return Response({'message': 'Chưa đăng nhập'}, 401)

class CategoryViewSet(viewsets.ModelViewSet):
    queryset = Category.objects.all().order_by('id') # Sắp xếp để không bị lộn xộn
    serializer_class = CategorySerializer
    
    # 1. Phân quyền: Khách chỉ được xem, Admin mới được Thêm/Sửa/Xóa
    def get_permissions(self):
        if self.action in ['list', 'retrieve']:
            return [AllowAny()]
        return [IsAdminUser()]

    # 2. Custom hàm tạo để kiểm tra trùng tên
    def create(self, request, *args, **kwargs):
        try:
            name = request.data.get('name', '').strip()
            
            # Validate: Không để trống
            if not name:
                return Response({'error': 'Tên nhóm không được để trống!'}, status=400)
            
            # Validate: Kiểm tra trùng tên (không phân biệt hoa thường)
            if Category.objects.filter(name__iexact=name).exists():
                return Response({'error': f'Nhóm món "{name}" đã tồn tại!'}, status=400)

            # Tạo mới
            category = Category.objects.create(name=name)
            return Response(CategorySerializer(category).data, status=201)
            
        except Exception as e:
            return Response({'error': str(e)}, status=500)

class ItemViewSet(viewsets.ModelViewSet):
    queryset = Item.objects.all().order_by('-id')
    def get_permissions(self): return [AllowAny()] if self.action in ['list', 'retrieve'] else [IsAdminUser()]
    def get_serializer_class(self): return ProductFormSerializer if self.action in ['create', 'update', 'partial_update'] else ItemSerializer
    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        return Response(ItemSerializer(queryset, many=True, context={'request': request}).data)

@api_view(['GET'])
@permission_classes([AllowAny])
@authentication_classes([])
def get_menu(request):
    try: return Response(ItemSerializer(Item.objects.all().order_by('category', 'id'), many=True, context={'request': request}).data)
    except: return Response([], 200)

@api_view(['GET'])
@permission_classes([AllowAny])
@authentication_classes([])
def get_menu_data(request):
    try:
        items = Item.objects.select_related('category').all().order_by('category__id', 'id')
        categories = sorted(list(set(i.category.name for i in items if i.category)))
        products = []
        for i in items:
            img = request.build_absolute_uri(i.image.url) if i.image and request else (i.image.url if i.image else "")
            products.append({'id': i.id, 'name': i.name, 'price': i.price, 'img': img, 'category': i.category.name if i.category else "Khác"})
        return Response({'categories': categories, 'products': products})
    except Exception as e: return Response({'error': str(e)}, 500)

class EmployeeViewSet(viewsets.ViewSet):
    permission_classes = [IsAdminUser]
    def list(self, request):
        users = User.objects.filter(is_staff=True).exclude(username='admin').order_by('id')
        return Response([{"id": u.id, "name": u.first_name or u.username, "user": u.username, "role": "admin" if u.is_superuser else "staff"} for u in users])
    def create(self, request):
        try:
            d = request.data
            if User.objects.filter(username=d.get('user')).exists(): return Response({'error': 'Trùng tên'}, 400)
            u = User.objects.create(username=d.get('user'), first_name=d.get('name'), is_staff=True, is_active=True)
            if d.get('pass'): u.set_password(d.get('pass'))
            u.is_superuser = (d.get('role') == 'admin'); u.save()
            return Response({'message': 'OK', 'id': u.id}, 201)
        except Exception as e: return Response({'error': str(e)}, 500)
    def update(self, request, pk=None):
        try:
            u = User.objects.get(pk=pk); d = request.data
            if 'user' in d and d['user'] != u.username:
                if User.objects.filter(username=d['user']).exists(): return Response({'error': 'Trùng tên'}, 400)
                u.username = d['user']
            if 'name' in d: u.first_name = d['name']
            if d.get('pass'): u.set_password(d.get('pass'))
            if d.get('role'): u.is_superuser = (d.get('role') == 'admin')
            u.save(); return Response({'message': 'OK'})
        except: return Response({'error': 'Lỗi'}, 500)
    def destroy(self, request, pk=None):
        try:
            u = User.objects.get(pk=pk)
            if request.user.id == u.id: return Response({'error': 'Không thể xóa chính mình'}, 400)
            u.delete(); return Response({'message': 'OK'})
        except: return Response({'error': 'Lỗi'}, 500)
@api_view(['GET'])
@permission_classes([AllowAny])
@authentication_classes([])
def get_menu_by_category(request, id_danhmuc):
    try:
        items = Item.objects.filter(category_id=id_danhmuc)
        serializer = ItemSerializer(items, many=True, context={'request': request})
        return Response(serializer.data)
    except Exception:
        return Response([], status=200)
    

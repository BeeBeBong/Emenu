from rest_framework import viewsets
from rest_framework.decorators import api_view
from rest_framework.response import Response
from django.shortcuts import render
from .models import Category, Item, Table, Order, OrderItem, Payment
from .serializers import (
    CategorySerializer, ItemSerializer, TableSerializer,
    OrderSerializer, OrderItemSerializer, PaymentSerializer
)
from rest_framework import status
from django.shortcuts import get_object_or_404
import json
import os
from django.conf import settings

# ========== Template View ==========
def get_Emenu(request):
    """Render template HTML cho eMenu"""
    return render(request, 'Emenu.html')

# ========== CATEGORY APIs ==========
class CategoryViewSet(viewsets.ModelViewSet):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer

# ========== ITEM APIs ==========
class ItemViewSet(viewsets.ModelViewSet):
    queryset = Item.objects.all()
    serializer_class = ItemSerializer
    
    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['request'] = self.request
        return context

@api_view(['GET'])
def get_menu(request):
    """Lấy tất cả món ăn"""
    items = Item.objects.all()
    serializer = ItemSerializer(items, many=True, context={'request': request})
    return Response(serializer.data)

@api_view(['GET'])
def get_menu_data(request):
    """Lấy dữ liệu menu đầy đủ từ file JSON: categories và products (format cho frontend)"""
    # Tìm đường dẫn file menu.json (nằm cùng thư mục với manage.py)
    base_dir = settings.BASE_DIR
    json_path = os.path.join(base_dir, 'menu.json')
    
    try:
        # Đọc file JSON
        with open(json_path, 'r', encoding='utf-8') as f:
            menu_data = json.load(f)
        
        # Lấy unique categories từ phan_loai
        categories = list(set(item['phan_loai'] for item in menu_data))
        categories.sort()  # Sắp xếp theo thứ tự alphabet
        
        # Format products theo cấu trúc frontend cần
        products = []
        for idx, item in enumerate(menu_data, start=1):
            products.append({
                'id': idx,
                'name': item['ten_mon'],
                'price': item['gia'],
                'img': item.get('img', ''),  # Lấy từ JSON, mặc định là rỗng nếu không có
                'category': item['phan_loai']
            })
        
        return Response({
            'categories': categories,
            'products': products
        }, status=status.HTTP_200_OK)
    except FileNotFoundError:
        return Response({
            'error': 'Không tìm thấy file menu.json',
            'detail': f'File không tồn tại tại: {json_path}'
        }, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        return Response({
            'error': 'Không thể tải dữ liệu menu',
            'detail': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['GET'])
def get_menu_by_category(request, id_danhmuc):
    """Lấy món ăn theo danh mục"""
    items = Item.objects.filter(category_id=id_danhmuc)
    serializer = ItemSerializer(items, many=True, context={'request': request})
    return Response(serializer.data)

# ========== TABLE APIs ==========
class TableViewSet(viewsets.ModelViewSet):
    queryset = Table.objects.all()
    serializer_class = TableSerializer

@api_view(['POST'])
def reserve_table(request, id_ban):
    """Đặt trước bàn (5 phút)"""
    table = get_object_or_404(Table, id=id_ban)
    if table.status != 'available':
        return Response({'error': 'Bàn không trống'}, status=status.HTTP_400_BAD_REQUEST)
    
    from django.utils import timezone
    from datetime import timedelta
    
    table.status = 'reserved'
    table.reserved_at = timezone.now()
    table.expires_at = timezone.now() + timedelta(minutes=5)
    table.save()
    
    serializer = TableSerializer(table)
    return Response(serializer.data, status=status.HTTP_200_OK)

# ========== ORDER APIs ==========
class OrderViewSet(viewsets.ModelViewSet):
    queryset = Order.objects.all()
    serializer_class = OrderSerializer
    
    def create(self, request, *args, **kwargs):
        """Override create method để xử lý tạo đơn hàng với items"""
        # Chuyển hướng đến function create_order để xử lý
        return create_order(request)

@api_view(['POST'])
def create_order(request):
    """Tạo đơn hàng mới"""
    try:
        data = request.data
        
        # Lấy thông tin bàn
        table_id = data.get('tableId')
        if not table_id:
            return Response({'error': 'Thiếu thông tin bàn (tableId)'}, status=status.HTTP_400_BAD_REQUEST)
        
        # Kiểm tra tableId có phải số không
        try:
            table_id = int(table_id)
        except (ValueError, TypeError):
            return Response({
                'error': 'tableId không hợp lệ',
                'detail': f'tableId phải là số nguyên, nhận được: {table_id}'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Kiểm tra bàn có tồn tại không
        try:
            table = Table.objects.get(id=table_id)
        except Table.DoesNotExist:
            return Response({
                'error': 'Bàn không tồn tại',
                'detail': f'Không tìm thấy bàn với ID: {table_id}. Vui lòng kiểm tra lại hoặc lấy danh sách bàn từ GET /api/tables/'
            }, status=status.HTTP_404_NOT_FOUND)
        
        # Lấy danh sách món ăn
        items_data = data.get('items', [])
        if not items_data:
            return Response({'error': 'Danh sách món ăn không được để trống'}, status=status.HTTP_400_BAD_REQUEST)
        
        # Tính tổng tiền
        total = 0
        for item_data in items_data:
            item_id = item_data.get('itemId') or item_data.get('id_mon')
            if not item_id:
                return Response({
                    'error': 'Thiếu itemId trong danh sách món ăn',
                    'detail': f'Món ăn: {item_data}'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            try:
                item_id = int(item_id)
            except (ValueError, TypeError):
                return Response({
                    'error': 'itemId không hợp lệ',
                    'detail': f'itemId phải là số nguyên, nhận được: {item_id}'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            quantity = item_data.get('quantity', 1)
            try:
                quantity = int(quantity)
                if quantity <= 0:
                    return Response({
                        'error': 'Số lượng không hợp lệ',
                        'detail': f'Số lượng phải lớn hơn 0, nhận được: {quantity}'
                    }, status=status.HTTP_400_BAD_REQUEST)
            except (ValueError, TypeError):
                return Response({
                    'error': 'Số lượng không hợp lệ',
                    'detail': f'Số lượng phải là số nguyên, nhận được: {quantity}'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            try:
                item = Item.objects.get(id=item_id)
            except Item.DoesNotExist:
                return Response({
                    'error': 'Món ăn không tồn tại',
                    'detail': f'Không tìm thấy món ăn với ID: {item_id}'
                }, status=status.HTTP_404_NOT_FOUND)
            
            total += item.price * quantity
        
        # Tạo đơn hàng
        order = Order.objects.create(
            table=table,
            total=total,
            status='pending'
        )
        
        # Tạo chi tiết đơn hàng
        for item_data in items_data:
            item_id = item_data.get('itemId') or item_data.get('id_mon')
            quantity = item_data.get('quantity', 1)
            note = item_data.get('note', '') or item_data.get('ghi_chu', '')
            
            # Đã validate ở trên, chỉ cần get lại
            item = Item.objects.get(id=item_id)
            
            OrderItem.objects.create(
                order=order,
                item=item,
                quantity=quantity,
                note=note
            )
        
        # Serialize và trả về đơn hàng đã tạo
        serializer = OrderSerializer(order)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
        
    except Exception as e:
        return Response({
            'error': 'Lỗi khi tạo đơn hàng',
            'detail': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
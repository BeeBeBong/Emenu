"""
URL configuration for site1 project.
"""
from django.contrib import admin
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from EMENU.views import (
    CategoryViewSet, ItemViewSet, TableViewSet, OrderViewSet,
    get_menu, get_menu_data, get_menu_by_category, reserve_table, create_order
)
from EMENU.views import get_Emenu  # View render template HTML

# Router cho ViewSets
router = DefaultRouter()
router.register(r'categories', CategoryViewSet, basename='category')
router.register(r'items', ItemViewSet, basename='item')
router.register(r'tables', TableViewSet, basename='table')
router.register(r'orders', OrderViewSet, basename='order')

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', get_Emenu, name='get_Emenu'),
    
    # Order APIs - Phải đặt TRƯỚC router để không bị router chặn
    path('api/orders/create/', create_order, name='create_order'),  # POST tạo đơn
    
    # API endpoints
    path('api/', include(router.urls)),
    
    # Menu APIs
    path('api/menu/', get_menu, name='get_menu'),  # GET tất cả món
    path('api/menu/data/', get_menu_data, name='get_menu_data'),  # GET categories + products (format cho frontend)
    path('api/menu/category/<int:id_danhmuc>/', get_menu_by_category, name='get_menu_by_category'),  # GET theo category
    
    # Table APIs
    path('api/tables/<int:id_ban>/reserve/', reserve_table, name='reserve_table'),  # POST đặt trước bàn
]

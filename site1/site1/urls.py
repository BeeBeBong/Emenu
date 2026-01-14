"""
URL configuration for site1 project.
"""
from django.contrib import admin
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from EMENU.views import (
    CategoryViewSet, ItemViewSet, TableViewSet, OrderViewSet,
    get_menu, get_menu_data, get_menu_by_category, reserve_table, create_order,
    get_current_user, login, 
    # --- CẬP NHẬT MỚI: Import thêm 2 views này ---
    create_booking, get_dashboard_stats 
)
from EMENU.views import get_Emenu
from EMENU import views

# Router cho ViewSets
router = DefaultRouter()
router.register(r'categories', CategoryViewSet, basename='category')
router.register(r'items', ItemViewSet, basename='item')
router.register(r'tables', TableViewSet, basename='table')
router.register(r'orders', OrderViewSet, basename='order')

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', get_Emenu, name='get_Emenu'),
    
    # Auth APIs
    path('login/', login, name='login'),
    path('api/auth/me/', get_current_user, name='get_current_user'),
    
    # --- CẬP NHẬT MỚI: Thay api/revenue cũ bằng api dashboard mới ---
    # API này trả về cả Doanh thu + Booking + Best Seller
    path('api/dashboard/stats/', get_dashboard_stats, name='get_dashboard_stats'),
    path('api/booking/delete/<int:pk>/', views.delete_booking, name='delete_booking'),

    
    # --- CẬP NHẬT MỚI: API cho khách đặt bàn ---
    path('api/booking/create/', create_booking, name='create_booking'),

    # Order APIs
    path('api/orders/create/', create_order, name='create_order'),
    
    # API endpoints từ Router
    path('api/', include(router.urls)),
    
    # Menu APIs
    path('api/menu/', get_menu, name='get_menu'),
    path('api/menu/data/', get_menu_data, name='get_menu_data'),
    path('api/menu/category/<int:id_danhmuc>/', get_menu_by_category, name='get_menu_by_category'),
    
    # Table APIs
    path('api/tables/<int:id_ban>/reserve/', reserve_table, name='reserve_table'),
]
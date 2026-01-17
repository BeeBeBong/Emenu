"""
URL configuration for site1 project.
"""
from django.contrib import admin
from django.urls import path, include
# 👇 1. THÊM 2 DÒNG NÀY ĐỂ CẤU HÌNH MEDIA
from django.conf import settings
from django.conf.urls.static import static

from rest_framework.routers import DefaultRouter
from EMENU.views import (
    CategoryViewSet, ItemViewSet, TableViewSet, OrderViewSet,
    get_menu, get_menu_data, get_menu_by_category, reserve_table, create_order,
    get_current_user, login, 
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
    
    # Dashboard API
    path('api/dashboard/stats/', get_dashboard_stats, name='get_dashboard_stats'),
    path('api/booking/delete/<int:pk>/', views.delete_booking, name='delete_booking'),

    # Booking API
    path('api/booking/create/', create_booking, name='create_booking'),

    # Order APIs
    path('api/orders/create/', create_order, name='create_order'),
    path('api/orders/cancel/', views.cancel_order, name='cancel_order'),
    path('api/tables/request-payment/', views.request_payment, name='request_payment'),
    path('api/notifications/', views.get_notifications, name='get_notifications'),
    
    # API endpoints từ Router
    path('api/', include(router.urls)),
    
    # Menu APIs
    path('api/menu/', get_menu, name='get_menu'),
    path('api/menu/data/', get_menu_data, name='get_menu_data'),
    path('api/menu/category/<int:id_danhmuc>/', get_menu_by_category, name='get_menu_by_category'),
    
    # Table APIs
    path('api/tables/<int:id_ban>/reserve/', reserve_table, name='reserve_table'),
    path('api/tables/<int:table_id>/checkout/', views.checkout, name='checkout'),
    path('api/orders/table/<int:table_id>/', views.get_order_by_table, name='get_order_by_table'),
]

# 👇 2. ĐOẠN QUAN TRỌNG NHẤT: MỞ KHO ẢNH
# Nếu đang chạy DEBUG (Runserver) thì cho phép truy cập link /media/...
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
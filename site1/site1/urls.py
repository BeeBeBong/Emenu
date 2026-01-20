"""
URL configuration for site1 project.
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from rest_framework.routers import DefaultRouter

# Import module views từ app EMENU
from EMENU import views

# Router cho các ViewSets (CRUD chuẩn)
router = DefaultRouter()
router.register(r'categories', views.CategoryViewSet, basename='category')
router.register(r'items', views.ItemViewSet, basename='item')
router.register(r'tables', views.TableViewSet, basename='table')
router.register(r'orders', views.OrderViewSet, basename='order')
router.register(r'employees', views.EmployeeViewSet, basename='employees')

urlpatterns = [
    # 1. Admin & Trang chủ
    path('admin/', admin.site.urls),
    path('', views.get_Emenu, name='home'),
    
    # 2. Auth APIs (Đăng nhập)
    path('login/', views.login, name='login'),
    path('api/auth/me/', views.get_current_user, name='get_current_user'),
    
    # 3. Dashboard API (Thống kê)
    path('api/dashboard/stats/', views.get_dashboard_stats, name='get_dashboard_stats'),
    
    # 4. Booking API (Đặt bàn)
    path('api/booking/create/', views.create_booking, name='create_booking'),
    path('api/booking/delete/<int:pk>/', views.delete_booking, name='delete_booking'),

    # 5. Order & Table APIs (Gọi món & Thanh toán)
    path('api/orders/create/', views.create_order, name='create_order'),
    path('api/orders/cancel/', views.cancel_order, name='cancel_order'),
    path('api/orders/table/<int:table_id>/', views.get_order_by_table, name='get_order_by_table'),
    path('api/tables/request-payment/', views.request_payment, name='request_payment'),
    path('api/tables/<int:id_ban>/reserve/', views.reserve_table, name='reserve_table'),
    path('api/tables/<int:table_id>/checkout/', views.checkout, name='checkout'),
    
    # 6. Notification & Menu APIs
    path('api/notifications/', views.get_notifications, name='get_notifications'),
    path('api/menu/', views.get_menu, name='get_menu'),
    path('api/menu/data/', views.get_menu_data, name='get_menu_data'),
    path('api/menu/category/<int:id_danhmuc>/', views.get_menu_by_category, name='get_menu_by_category'),
    
    # 7. Include Router URLs (Các API tự động sinh ra từ Router)
    path('api/', include(router.urls)),
]

# ============================================================
# 🔥 QUAN TRỌNG: CẤU HÌNH ĐỂ HIỂN THỊ ẢNH (MEDIA)
# ============================================================
if settings.DEBUG:
    # Phục vụ Static files (CSS, JS)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    # Phục vụ Media files (Ảnh upload, Ảnh món ăn)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
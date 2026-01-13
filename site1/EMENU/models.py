from django.db import models
from django.utils import timezone
from datetime import timedelta
from django.db.models import Sum, Count, F
from django.db.models.functions import Coalesce

# 1. CATEGORIES - Danh mục món ăn
class Category(models.Model):
    id = models.AutoField(primary_key=True, db_column='id_danhmuc')
    name = models.CharField(max_length=100, db_column='ten_danhmuc')
    
    class Meta:
        db_table = 'categories'
        verbose_name = 'Danh mục'
        verbose_name_plural = 'Danh mục'
    
    def __str__(self):
        return self.name

# 2. ITEMS - Món ăn
class Item(models.Model):
    id = models.AutoField(primary_key=True, db_column='id_mon')
    category = models.ForeignKey(Category, on_delete=models.CASCADE, db_column='id_danhmuc', related_name='items')
    name = models.CharField(max_length=255, db_column='ten_mon')
    price = models.IntegerField(db_column='gia')
    image = models.ImageField(upload_to='menu/', null=True, blank=True, db_column='hinh_anh')
    
    class Meta:
        db_table = 'items'
        verbose_name = 'Món ăn'
        verbose_name_plural = 'Món ăn'
    
    def __str__(self):
        return self.name

# 3. TABLES - Bàn
class Table(models.Model):
    STATUS_CHOICES = [
        ('available', 'Trống'),
        ('reserved', 'Đã đặt trước'),
        ('occupied', 'Đang sử dụng'),
    ]
    
    id = models.AutoField(primary_key=True, db_column='id_ban')
    number = models.CharField(max_length=50, unique=True, db_column='so_ban')  # "Bàn 1", "Bàn 2"
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='available', db_column='trang_thai')
    reserved_at = models.DateTimeField(null=True, blank=True, db_column='thoi_gian_dat')  # Thời điểm đặt trước
    expires_at = models.DateTimeField(null=True, blank=True, db_column='thoi_gian_het_han')  # Thời điểm hết hạn (5 phút sau)
    
    class Meta:
        db_table = 'tables'
        verbose_name = 'Bàn'
        verbose_name_plural = 'Bàn'
    
    def __str__(self):
        return f"{self.number} - {self.get_status_display()}"
    
    def check_expired(self):
        """Kiểm tra xem đặt trước đã hết hạn chưa (>5 phút)"""
        if self.status == 'reserved' and self.expires_at:
            if timezone.now() > self.expires_at:
                self.status = 'available'
                self.reserved_at = None
                self.expires_at = None
                self.save()
                return True
        return False

# 4. ORDERS - Đơn hàng
class Order(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Chờ xử lý'),
        ('preparing', 'Đang làm'),
        ('ready', 'Đã xong'),
        ('served', 'Đã phục vụ'),
        ('cancelled', 'Đã hủy'),
    ]
    
    id = models.AutoField(primary_key=True, db_column='id_donhang')
    table = models.ForeignKey(Table, on_delete=models.CASCADE, db_column='id_ban', related_name='orders')
    total = models.IntegerField(default=0, db_column='tong_tien')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending', db_column='trang_thai_tt')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'orders'
        verbose_name = 'Đơn hàng'
        verbose_name_plural = 'Đơn hàng'
    
    def __str__(self):
        return f"Đơn #{self.id} - {self.table.number}"
    
    def save(self, *args, **kwargs):
        # Khi tạo đơn mới, cập nhật trạng thái bàn thành "occupied"
        if not self.pk:  # Đơn mới
            self.table.status = 'occupied'
            self.table.save()
        super().save(*args, **kwargs)

# 5. ORDER_ITEMS - Chi tiết đơn hàng
class OrderItem(models.Model):
    id = models.AutoField(primary_key=True, db_column='id_chitiet')
    order = models.ForeignKey(Order, on_delete=models.CASCADE, db_column='id_donhang', related_name='items')
    item = models.ForeignKey(Item, on_delete=models.CASCADE, db_column='id_mon', related_name='order_items')
    quantity = models.IntegerField(default=1, db_column='so_luong')
    note = models.TextField(null=True, blank=True, db_column='ghi_chu')
    is_served = models.BooleanField(default=False, db_column='da_ra_mon')  # Đã ra món chưa
    
    class Meta:
        db_table = 'order_items'
        verbose_name = 'Chi tiết đơn hàng'
        verbose_name_plural = 'Chi tiết đơn hàng'
    
    def __str__(self):
        return f"{self.order} - {self.item.name} x{self.quantity}"

# 6. REVENUE - Doanh thu
class Revenue(models.Model):
    METHOD_CHOICES = [
        ('cash', 'Tiền mặt'),
        ('card', 'Thẻ'),
        ('momo', 'MoMo'),
        ('zalopay', 'ZaloPay'),
        ('banking', 'Chuyển khoản'),
    ]
    
    id = models.AutoField(primary_key=True, db_column='id_tt')
    order = models.ForeignKey(Order, on_delete=models.CASCADE, db_column='id_donhang', related_name='revenues')
    method = models.CharField(max_length=20, choices=METHOD_CHOICES, db_column='phuong_thuc')
    amount = models.IntegerField(default=0, db_column='so_tien')  # Doanh thu (VND)
    paid_at = models.DateTimeField(auto_now_add=True, db_column='thoi_gian_tt')
    
    class Meta:
        db_table = 'revenues'
        verbose_name = 'Doanh thu'
        verbose_name_plural = 'Doanh thu'
    
    def __str__(self):
        return f"Doanh thu #{self.id} - Đơn #{self.order.id}"
    
    # 7. BOOKINGS - Yêu cầu đặt bàn
class Booking(models.Model):
    # Chỉ có 2 trạng thái: Chờ xử lý (Pending) và Đã xác nhận (Confirmed)
    STATUS_CHOICES = [
        ('pending', 'Chờ xử lý'),   # Mặc định khi khách gửi
        ('confirmed', 'Đã xác nhận'), # Khi admin đã gọi điện xong
    ]
    
    id = models.AutoField(primary_key=True)
    customer_name = models.CharField(max_length=100, db_column='ten_khach')
    customer_phone = models.CharField(max_length=15, db_column='sdt')
    booking_time = models.DateTimeField(db_column='thoi_gian_dat') # Thời gian khách muốn đến
    guest_count = models.IntegerField(default=1, db_column='so_nguoi')
    note = models.TextField(null=True, blank=True, db_column='ghi_chu')
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending', db_column='trang_thai')
    created_at = models.DateTimeField(auto_now_add=True) # Thời điểm gửi yêu cầu

    class Meta:
        db_table = 'bookings'
        ordering = ['-created_at'] # Đưa yêu cầu mới nhất lên đầu để Admin dễ thấy

    def __str__(self):
        return f"{self.customer_name} - {self.customer_phone} ({self.status})"
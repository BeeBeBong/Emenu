from django.db import models
from .order import Order, Table

class Revenue(models.Model):
    METHOD_CHOICES = [('cash', 'Tiền mặt'), ('card', 'Thẻ'), ('momo', 'MoMo'), ('zalopay', 'ZaloPay'), ('banking', 'CK')]
    id = models.AutoField(primary_key=True, db_column='id_tt')
    order = models.ForeignKey(Order, on_delete=models.CASCADE, db_column='id_donhang', related_name='revenues')
    method = models.CharField(max_length=20, choices=METHOD_CHOICES, db_column='phuong_thuc')
    amount = models.IntegerField(default=0, db_column='so_tien')
    paid_at = models.DateTimeField(auto_now_add=True, db_column='thoi_gian_tt')
    class Meta: db_table = 'revenues'

class Booking(models.Model):
    STATUS_CHOICES = [('pending', 'Chờ xử lý'), ('confirmed', 'Đã xác nhận')]
    id = models.AutoField(primary_key=True)
    customer_name = models.CharField(max_length=100, db_column='ten_khach')
    customer_phone = models.CharField(max_length=15, db_column='sdt')
    booking_time = models.DateTimeField(db_column='thoi_gian_dat')
    guest_count = models.IntegerField(default=1, db_column='so_nguoi')
    note = models.TextField(null=True, blank=True, db_column='ghi_chu')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending', db_column='trang_thai')
    created_at = models.DateTimeField(auto_now_add=True)
    class Meta: db_table = 'bookings'; ordering = ['-created_at']

class Notification(models.Model):
    table = models.ForeignKey(Table, on_delete=models.CASCADE, null=True)
    message = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)
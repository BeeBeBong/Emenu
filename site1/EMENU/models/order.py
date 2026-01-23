from django.db import models
from django.utils import timezone
from .core import Item

class Table(models.Model):
    STATUS_CHOICES = [('available', 'Trống'), ('reserved', 'Đã đặt'), ('occupied', 'Đang dùng')]
    id = models.AutoField(primary_key=True, db_column='id_ban')
    number = models.CharField(max_length=50, unique=True, db_column='so_ban')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='available', db_column='trang_thai')
    reserved_at = models.DateTimeField(null=True, blank=True, db_column='thoi_gian_dat')
    expires_at = models.DateTimeField(null=True, blank=True, db_column='thoi_gian_het_han')
    class Meta: db_table = 'tables'
    
    def check_expired(self):
        if self.status == 'reserved' and self.expires_at and timezone.now() > self.expires_at:
            self.status = 'available'; self.reserved_at = None; self.expires_at = None; self.save()
            return True
        return False

class Order(models.Model):
    id_donhang = models.AutoField(primary_key=True)
    table = models.ForeignKey(Table, on_delete=models.CASCADE, db_column='id_ban')
    total = models.IntegerField(db_column='tong_tien', default=0)
    status = models.CharField(max_length=20, db_column='trang_thai_tt', default='pending')
    created_at = models.DateTimeField(auto_now_add=True)
    class Meta: db_table = 'orders'

class OrderItem(models.Model):
    id_chitiet = models.AutoField(primary_key=True)
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items', db_column='id_donhang')
    item = models.ForeignKey(Item, on_delete=models.CASCADE, db_column='id_mon')
    quantity = models.IntegerField(db_column='so_luong', default=1)
    note = models.TextField(db_column='ghi_chu', null=True, blank=True)
    is_served = models.BooleanField(db_column='da_ra_mon', default=False)
    class Meta: db_table = 'order_items'
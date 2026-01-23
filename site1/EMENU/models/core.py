from django.db import models

class Category(models.Model):
    id = models.AutoField(primary_key=True, db_column='id_danhmuc')
    name = models.CharField(max_length=100, db_column='ten_danhmuc')
    class Meta: db_table = 'categories'; verbose_name = 'Danh mục'
    def __str__(self): return self.name

class Item(models.Model):
    id = models.AutoField(primary_key=True, db_column='id_mon')
    category = models.ForeignKey(Category, on_delete=models.CASCADE, db_column='id_danhmuc', related_name='items')
    name = models.CharField(max_length=255, db_column='ten_mon')
    price = models.IntegerField(db_column='gia')
    image = models.ImageField(upload_to='menu/', null=True, blank=True, db_column='hinh_anh')
    class Meta: db_table = 'items'; verbose_name = 'Món ăn'
    def __str__(self): return self.name
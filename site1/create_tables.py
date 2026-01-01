import os
import django
import sys

# Fix encoding cho Windows console
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

# 1. Cấu hình môi trường Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'site1.settings')
django.setup()

# 2. Import models
from EMENU.models import Table

def create_tables():
    """Tạo các bàn mẫu cho nhà hàng"""
    print("Đang tạo các bàn mẫu...")
    
    # Số lượng bàn muốn tạo
    num_tables = 30
    
    created_count = 0
    for i in range(1, num_tables + 1):
        table_number = f"Bàn {i}"
        table, created = Table.objects.get_or_create(
            number=table_number,
            defaults={
                'status': 'available'
            }
        )
        if created:
            created_count += 1
            print(f"✓ Đã tạo {table_number}")
        else:
            print(f"- {table_number} đã tồn tại")
    
    print(f"\nHoàn thành! Đã tạo {created_count} bàn mới.")
    print(f"Tổng số bàn trong database: {Table.objects.count()}")

if __name__ == '__main__':
    create_tables()


import os
import django
import json
import sys

# Fix encoding cho Windows console
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

# 1. Cấu hình môi trường Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'site1.settings')
django.setup()

# 2. Import models
from EMENU.models import Category, Item

def import_data():
    print("Dang xoa du lieu cu...")
    Item.objects.all().delete()
    Category.objects.all().delete()
    
    # Đọc file dữ liệu JSON
    file_path = 'menu.json'
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Tạo dictionary để lưu các category đã tạo
        categories_dict = {}
        
        for item_data in data:
            phan_loai = item_data['phan_loai']
            
            # Tạo category nếu chưa có
            if phan_loai not in categories_dict:
                category, created = Category.objects.get_or_create(
                    name=phan_loai
                )
                categories_dict[phan_loai] = category
            
            # Tạo item với category tương ứng
            Item.objects.create(
                category=categories_dict[phan_loai],
                name=item_data['ten_mon'],
                price=item_data['gia'],
                image=None  # Có thể thêm sau
            )
        
        print(f"Thanh cong! Da nap {len(data)} mon vao Database.")
        print(f"Da tao {len(categories_dict)} danh muc.")
    except FileNotFoundError:
        print(f"Loi: Khong tim thay file {file_path}")

if __name__ == '__main__':
    import_data()
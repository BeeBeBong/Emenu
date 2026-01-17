import os
import django
import json
import requests
from django.core.files.base import ContentFile
from urllib.parse import urlparse

# 1. Cấu hình để chạy được lệnh Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'site1.settings') # Sửa 'config' thành tên folder chứa settings.py nếu khác
django.setup()

from EMENU.models import Item

def import_images_from_json():
    # Đường dẫn đến file menu.json (Giả sử nằm cùng thư mục file này)
    # Nếu file nằm trong folder site1, hãy sửa thành 'site1/menu.json'
    json_path = 'menu.json' 
    
    if not os.path.exists(json_path):
        print(f"❌ Không tìm thấy file {json_path}. Hãy copy file menu.json ra nằm cạnh file manage.py")
        return

    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    print("🚀 Bắt đầu tải ảnh và cập nhật Database...")

    count = 0
    for entry in data:
        ten_mon = entry.get('ten_mon')
        img_url = entry.get('img')

        if not img_url:
            continue

        try:
            # Tìm món ăn trong DB theo tên
            item = Item.objects.get(name=ten_mon)
            
            # Nếu món này chưa có ảnh trong DB, thì tải về
            if not item.image:
                print(f"⬇️ Đang tải ảnh cho: {ten_mon}...")
                
                response = requests.get(img_url)
                if response.status_code == 200:
                    # Lấy tên file từ URL (ví dụ: sushi.jpg)
                    file_name = os.path.basename(urlparse(img_url).path)
                    
                    # Lưu file vào ImageField của Django
                    item.image.save(file_name, ContentFile(response.content), save=True)
                    count += 1
                    print(f"✅ Đã lưu: {file_name}")
                else:
                    print(f"⚠️ Link ảnh lỗi: {img_url}")
            else:
                print(f"⏩ {ten_mon} đã có ảnh, bỏ qua.")

        except Item.DoesNotExist:
            print(f"⚠️ Không tìm thấy món '{ten_mon}' trong Database (Hãy chắc chắn bạn đã import tên món trước)")
        except Exception as e:
            print(f"❌ Lỗi khi xử lý {ten_mon}: {e}")

    print(f"\n🎉 HOÀN TẤT! Đã cập nhật ảnh cho {count} món ăn.")

if __name__ == '__main__':
    import_images_from_json()
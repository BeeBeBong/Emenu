import os
import django
import requests
from django.core.files.base import ContentFile

# 1. Cấu hình Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'site1.settings')
django.setup()

from EMENU.models import Item

def fix_images_final():
    # Link ảnh mẫu đẹp (Sushi)
    DEMO_IMAGE_URL = "https://images.unsplash.com/photo-1579871494447-9811cf80d66c?q=80&w=600&auto=format&fit=crop"
    
    print("🚀 Đang tải ảnh mẫu về...")
    
    try:
        response = requests.get(DEMO_IMAGE_URL)
        if response.status_code == 200:
            image_content = ContentFile(response.content)
            
            items = Item.objects.all()
            print(f"📦 Đang cập nhật {items.count()} món ăn...")

            for item in items:
                # 1. Lưu ảnh vào file thật (image)
                # save=False để chưa lưu vội, chờ lệnh save() cuối cùng
                item.image.save('sushi_fix.jpg', image_content, save=False)
                
                # 2. QUAN TRỌNG: Xóa trường text cũ (img) để tránh xung đột
                # (Nếu model Item của bạn có trường 'img', ta sẽ xóa nó đi)
                if hasattr(item, 'img'):
                    item.img = '' 
                
                item.save()
                print(f"✅ Đã fix: {item.name}")

            print("\n🎉 HOÀN TẤT! Tất cả ảnh đã được đồng bộ.")
        else:
            print("❌ Không tải được ảnh mẫu.")
            
    except Exception as e:
        print(f"❌ Có lỗi: {e}")

if __name__ == '__main__':
    fix_images_final()
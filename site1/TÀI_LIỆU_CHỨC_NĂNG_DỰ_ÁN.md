# TÀI LIỆU MÔ TẢ CHỨC NĂNG CÁC FILE TRONG DỰ ÁN EMENU

## 1. TỔNG QUAN DỰ ÁN

Dự án **EMENU** là một hệ thống quản lý menu điện tử cho nhà hàng, được xây dựng bằng Django Framework. Hệ thống cung cấp các chức năng quản lý menu, đặt bàn, đặt hàng và thanh toán.

---

## 2. CẤU TRÚC THƯ MỤC

```
site1/
├── site1/              # Thư mục cấu hình chính của Django project
├── EMENU/              # Django app chính chứa logic nghiệp vụ
├── manage.py           # File quản lý Django
├── import_menu.py      # Script import dữ liệu menu
├── menu.json           # File dữ liệu menu (JSON)
└── db.sqlite3          # Database SQLite
```

---

## 3. CHI TIẾT CHỨC NĂNG TỪNG FILE

### 3.1. THƯ MỤC `site1/` (Cấu hình Django Project)

#### 3.1.1. `site1/urls.py`
**Chức năng:**
- File cấu hình URL routing chính của dự án
- Định nghĩa tất cả các đường dẫn (endpoints) của ứng dụng
- Kết nối các view với URL patterns

**Các endpoint được định nghĩa:**
- `/admin/` - Trang quản trị Django
- `/` - Trang chủ (render template Emenu.html)
- `/api/categories/` - API quản lý danh mục (ViewSet)
- `/api/items/` - API quản lý món ăn (ViewSet)
- `/api/tables/` - API quản lý bàn (ViewSet)
- `/api/orders/` - API quản lý đơn hàng (ViewSet)
- `/api/menu/` - API lấy tất cả món ăn
- `/api/menu/category/<id>/` - API lấy món ăn theo danh mục
- `/api/tables/<id>/reserve/` - API đặt trước bàn
- `/api/orders/create/` - API tạo đơn hàng mới

**Công nghệ sử dụng:**
- Django URL routing
- Django REST Framework Router (DefaultRouter)

---

#### 3.1.2. `site1/settings.py`
**Chức năng:**
- File cấu hình chính của Django project
- Chứa tất cả các thiết lập về database, middleware, apps, security, v.v.

**Các cấu hình quan trọng:**
- **Database:** Cấu hình MySQL (có thể chuyển sang SQLite)
  - Database name: `emenu`
  - Host: `127.0.0.1`
  - Port: `3306`
- **Installed Apps:**
  - `EMENU` - App chính
  - `rest_framework` - Django REST Framework
  - `corsheaders` - Xử lý CORS
- **Middleware:** 
  - CORS middleware
  - Security, Session, CSRF, Authentication, Messages
- **CORS Settings:** Cho phép truy cập từ localhost:3000, localhost:5173
- **REST Framework:** Cấu hình pagination (50 items/page), cho phép truy cập không cần authentication
- **Allowed Hosts:** localhost, 127.0.0.1, và ngrok domain

---

#### 3.1.3. `site1/asgi.py`
**Chức năng:**
- File cấu hình ASGI (Asynchronous Server Gateway Interface)
- Sử dụng cho các ứng dụng async và WebSocket
- Expose ASGI application để deploy với các server như Daphne, Uvicorn

**Mục đích:**
- Hỗ trợ WebSocket connections
- Xử lý async requests
- Tích hợp với các server async

---

#### 3.1.4. `site1/wsgi.py`
**Chức năng:**
- File cấu hình WSGI (Web Server Gateway Interface)
- Chuẩn giao tiếp giữa web server và Django application
- Expose WSGI application để deploy với các server như Gunicorn, uWSGI

**Mục đích:**
- Deploy ứng dụng với các web server truyền thống
- Xử lý HTTP requests/responses
- Tích hợp với Apache, Nginx

---

#### 3.1.5. `site1/__init__.py`
**Chức năng:**
- File khởi tạo Python package
- Đánh dấu thư mục `site1` là một Python package
- Có thể chứa code khởi tạo khi import package

---

### 3.2. THƯ MỤC `EMENU/` (Django App chính)

#### 3.2.1. `EMENU/models.py`
**Chức năng:**
- Định nghĩa các model (bảng database) cho ứng dụng
- Mô tả cấu trúc dữ liệu và quan hệ giữa các bảng

**Các Model được định nghĩa:**

**Lưu ý:** Tất cả các fields trong Python code đã được đổi sang tiếng Anh, nhưng tên cột trong database vẫn giữ nguyên tiếng Việt thông qua `db_column`. Điều này giúp code dễ đọc hơn mà không cần migrate database.

1. **Category (Danh mục)**
   - `id`: ID danh mục (AutoField, Primary Key, db_column='id_danhmuc')
   - `name`: Tên danh mục (CharField, max 100 ký tự, db_column='ten_danhmuc')
   - Bảng: `categories`

2. **Item (Món ăn)**
   - `id`: ID món ăn (AutoField, Primary Key, db_column='id_mon')
   - `category`: Foreign Key đến Category (db_column='id_danhmuc')
   - `name`: Tên món ăn (CharField, max 255 ký tự, db_column='ten_mon')
   - `price`: Giá món ăn (IntegerField, db_column='gia')
   - `image`: Hình ảnh món ăn (ImageField, upload vào 'menu/', db_column='hinh_anh')
   - Bảng: `items`

3. **Table (Bàn)**
   - `id`: ID bàn (AutoField, Primary Key, db_column='id_ban')
   - `number`: Số bàn (CharField, unique, max 50 ký tự, db_column='so_ban')
   - `status`: Trạng thái bàn (choices: available, reserved, occupied, db_column='trang_thai')
   - `reserved_at`: Thời điểm đặt trước (DateTimeField, nullable, db_column='thoi_gian_dat')
   - `expires_at`: Thời điểm hết hạn đặt trước (DateTimeField, nullable, db_column='thoi_gian_het_han')
   - Method: `check_expired()` - Kiểm tra và tự động giải phóng bàn nếu hết hạn (>5 phút)
   - Bảng: `tables`

4. **Order (Đơn hàng)**
   - `id`: ID đơn hàng (AutoField, Primary Key, db_column='id_donhang')
   - `table`: Foreign Key đến Table (db_column='id_ban')
   - `total`: Tổng tiền (IntegerField, default 0, db_column='tong_tien')
   - `status`: Trạng thái đơn hàng (choices: pending, preparing, ready, served, cancelled, db_column='trang_thai_tt')
   - `created_at`: Thời gian tạo (DateTimeField, auto_now_add)
   - `updated_at`: Thời gian cập nhật (DateTimeField, auto_now)
   - Method `save()`: Tự động cập nhật trạng thái bàn thành "occupied" khi tạo đơn mới
   - Bảng: `orders`

5. **OrderItem (Chi tiết đơn hàng)**
   - `id`: ID chi tiết (AutoField, Primary Key, db_column='id_chitiet')
   - `order`: Foreign Key đến Order (db_column='id_donhang')
   - `item`: Foreign Key đến Item (db_column='id_mon')
   - `quantity`: Số lượng (IntegerField, default 1, db_column='so_luong')
   - `note`: Ghi chú (TextField, nullable, db_column='ghi_chu')
   - `is_served`: Đã ra món chưa (BooleanField, default False, db_column='da_ra_mon')
   - Bảng: `order_items`

6. **Payment (Thanh toán)**
   - `id`: ID thanh toán (AutoField, Primary Key, db_column='id_tt')
   - `order`: Foreign Key đến Order (db_column='id_donhang')
   - `method`: Phương thức thanh toán (choices: cash, card, momo, zalopay, banking, db_column='phuong_thuc')
   - `paid_at`: Thời gian thanh toán (DateTimeField, auto_now_add, db_column='thoi_gian_tt')
   - Bảng: `payments`

---

#### 3.2.2. `EMENU/views.py`
**Chức năng:**
- Chứa các view functions và view classes xử lý logic nghiệp vụ
- Xử lý HTTP requests và trả về responses
- Cung cấp các API endpoints cho frontend

**Các View được định nghĩa:**

1. **get_Emenu(request)**
   - Function view render template HTML
   - Trả về trang chủ `Emenu.html`
   - URL: `/`

2. **CategoryViewSet**
   - ViewSet (Django REST Framework) quản lý Category
   - Cung cấp CRUD operations (Create, Read, Update, Delete)
   - URL: `/api/categories/`

3. **ItemViewSet**
   - ViewSet quản lý Item
   - Cung cấp CRUD operations
   - URL: `/api/items/`

4. **get_menu(request)**
   - API view (GET) lấy tất cả món ăn
   - Trả về danh sách items dưới dạng JSON
   - URL: `/api/menu/`

5. **get_menu_by_category(request, id_danhmuc)**
   - API view (GET) lấy món ăn theo danh mục
   - Nhận parameter `id_danhmuc`
   - Trả về danh sách items thuộc danh mục đó
   - URL: `/api/menu/category/<id_danhmuc>/`

6. **TableViewSet**
   - ViewSet quản lý Table
   - Cung cấp CRUD operations
   - URL: `/api/tables/`

7. **reserve_table(request, id_ban)**
   - API view (POST) đặt trước bàn
   - Kiểm tra bàn có trống không
   - Đặt trạng thái "reserved" và set thời gian hết hạn (5 phút)
   - URL: `/api/tables/<id_ban>/reserve/`

8. **OrderViewSet**
   - ViewSet quản lý Order
   - Cung cấp CRUD operations
   - URL: `/api/orders/`

9. **create_order(request)**
   - API view (POST) tạo đơn hàng mới
   - Nhận `tableId` và danh sách `items` từ request body
   - Tạo Order và các OrderItem tương ứng
   - Tính tổng tiền tự động
   - Trả về Order đã tạo với đầy đủ thông tin
   - URL: `/api/orders/create/`

---

#### 3.2.3. `EMENU/serializers.py`
**Chức năng:**
- Định nghĩa các Serializer classes để chuyển đổi dữ liệu model thành JSON
- Xử lý serialization (model → JSON) và deserialization (JSON → model)
- Định nghĩa các field được expose qua API

**Các Serializer được định nghĩa:**

**Lưu ý:** Serializers sử dụng tên fields tiếng Anh từ models và map sang format JSON cho frontend.

1. **CategorySerializer**
   - Serialize Category model
   - API Fields: `id`, `name`

2. **ItemSerializer**
   - Serialize Item model
   - API Fields: `id`, `name`, `price`, `img`, `category`
   - Bao gồm tên danh mục từ relationship và URL hình ảnh

3. **TableSerializer**
   - Serialize Table model
   - API Fields: `id`, `number`, `status`, `reservedAt`, `expiresAt`

4. **OrderItemSerializer**
   - Serialize OrderItem model
   - API Fields: `id`, `itemId`, `name`, `price`, `quantity`, `note`, `isServed`
   - Bao gồm thông tin món ăn từ relationship (itemId, name, price)

5. **OrderSerializer**
   - Serialize Order model
   - API Fields: `id`, `tableId`, `tableNumber`, `total`, `status`, `createdAt`, `items`
   - Bao gồm danh sách items (nested OrderItemSerializer) và thông tin bàn

6. **PaymentSerializer**
   - Serialize Payment model
   - API Fields: `id`, `orderId`, `method`, `paidAt`

---

#### 3.2.4. `EMENU/admin.py`
**Chức năng:**
- Cấu hình Django Admin interface
- Đăng ký các model để quản lý qua admin panel
- Hiện tại file này trống (chưa đăng ký model nào)

**Ghi chú:**
- Có thể đăng ký các model để quản lý qua `/admin/` interface
- Ví dụ: `admin.site.register(Category)`, `admin.site.register(Item)`, v.v.

---

#### 3.2.5. `EMENU/apps.py`
**Chức năng:**
- Cấu hình Django App
- Định nghĩa class `EmenuConfig` kế thừa `AppConfig`
- Chứa metadata của app (name, verbose_name, v.v.)

**Nội dung:**
- Class `EmenuConfig` với `name = 'EMENU'`

---

#### 3.2.6. `EMENU/__init__.py`
**Chức năng:**
- File khởi tạo Python package
- Đánh dấu thư mục `EMENU` là một Python package

---

#### 3.2.7. `EMENU/tests.py`
**Chức năng:**
- File chứa các unit tests cho app EMENU
- Hiện tại file này có thể trống hoặc chứa các test cases mẫu

**Ghi chú:**
- Có thể viết tests cho models, views, serializers
- Chạy tests bằng: `python manage.py test`

---

#### 3.2.8. `EMENU/Templates/Emenu.html`
**Chức năng:**
- Template HTML cho trang chủ của ứng dụng
- Được render bởi view `get_Emenu()`

**Nội dung hiện tại:**
- Template cơ bản với HTML5 structure
- Có placeholder "Hello world!" và "This is your first EMENU template."
- Có thể được mở rộng để hiển thị menu, đặt bàn, v.v.

---

#### 3.2.9. `EMENU/migrations/`
**Chức năng:**
- Thư mục chứa các migration files
- Migration files là các file Python mô tả các thay đổi database schema

**Các file migration:**
- `__init__.py`: Đánh dấu thư mục là Python package
- `0001_initial.py`: Migration khởi tạo đầu tiên
- `0002_category_customer_item_order_orderitem_payment_table_and_more.py`: Migration tạo các bảng chính
- `0003_remove_customer.py`: Migration xóa Customer model và foreign key

**Lưu ý:** Việc đổi tên fields sang tiếng Anh không cần migration vì sử dụng `db_column` để giữ nguyên tên cột trong database.

**Cách sử dụng:**
- Tạo migration: `python manage.py makemigrations`
- Áp dụng migration: `python manage.py migrate`

---

### 3.3. FILE GỐC CỦA PROJECT

#### 3.3.1. `manage.py`
**Chức năng:**
- File quản lý chính của Django project
- Command-line utility để thực hiện các tác vụ quản lý

**Các lệnh thường dùng:**
- `python manage.py runserver` - Chạy development server
- `python manage.py migrate` - Áp dụng migrations
- `python manage.py makemigrations` - Tạo migrations
- `python manage.py createsuperuser` - Tạo admin user
- `python manage.py shell` - Mở Django shell
- `python manage.py test` - Chạy tests

**Cách hoạt động:**
- Set environment variable `DJANGO_SETTINGS_MODULE` = `site1.settings`
- Gọi `execute_from_command_line()` để xử lý các lệnh

---

#### 3.3.2. `import_menu.py`
**Chức năng:**
- Script Python để import dữ liệu menu từ file JSON vào database
- Xử lý encoding UTF-8 cho Windows console

**Các bước thực hiện:**
1. Cấu hình môi trường Django
2. Xóa dữ liệu cũ (Category và Item)
3. Đọc file `menu.json`
4. Tạo các Category từ field `phan_loai` (sử dụng field `name` trong code)
5. Tạo các Item với thông tin: `name`, `price`, và liên kết với Category

**Cấu trúc dữ liệu JSON mong đợi:**
```json
[
  {
    "phan_loai": "Tên danh mục",
    "ten_mon": "Tên món",
    "gia": 50000
  }
]
```

**Cách sử dụng:**
- Chạy: `python import_menu.py` (từ thư mục `site1/`)

---

#### 3.3.3. `menu.json`
**Chức năng:**
- File dữ liệu JSON chứa thông tin menu
- Được sử dụng bởi script `import_menu.py` để import vào database

**Cấu trúc:**
- Array of objects
- Mỗi object chứa: `phan_loai`, `ten_mon`, `gia`

---

#### 3.3.4. `db.sqlite3`
**Chức năng:**
- File database SQLite (nếu sử dụng SQLite thay vì MySQL)
- Chứa toàn bộ dữ liệu của ứng dụng

**Ghi chú:**
- File này được tạo tự động khi chạy migrations với SQLite
- Có thể được thay thế bằng MySQL (theo cấu hình trong `settings.py`)

---

## 4. LUỒNG HOẠT ĐỘNG CỦA HỆ THỐNG

### 4.1. Luồng Request/Response
1. Client gửi HTTP request đến URL
2. Django routing (`urls.py`) xác định view tương ứng
3. View (`views.py`) xử lý request, tương tác với database qua Models
4. Serializer (`serializers.py`) chuyển đổi dữ liệu model thành JSON
5. Response trả về JSON cho client

### 4.2. Luồng Import Menu
1. Chạy script `import_menu.py`
2. Script đọc file `menu.json`
3. Tạo các Category và Item trong database
4. Dữ liệu sẵn sàng để sử dụng qua API

### 4.3. Luồng Đặt Bàn
1. Client gọi API `/api/tables/<id>/reserve/` (POST)
2. View `reserve_table()` kiểm tra bàn có trống không
3. Cập nhật trạng thái bàn thành "reserved"
4. Set thời gian hết hạn (5 phút)
5. Trả về thông tin bàn đã đặt

---

## 5. CÔNG NGHỆ SỬ DỤNG

- **Backend Framework:** Django 6.0
- **API Framework:** Django REST Framework
- **Database:** MySQL (có thể dùng SQLite)
- **CORS:** django-cors-headers
- **Language:** Python 3.x

---

## 6. GHI CHÚ QUAN TRỌNG

1. **Database:** Hiện tại cấu hình MySQL, có thể chuyển sang SQLite bằng cách uncomment trong `settings.py`
2. **CORS:** Đã cấu hình cho phép truy cập từ localhost:3000, localhost:5173, localhost:5174 và ngrok domains
3. **Authentication:** REST Framework được cấu hình `AllowAny` (không cần authentication)
4. **Admin:** File `admin.py` chưa đăng ký models, cần đăng ký để quản lý qua admin panel
5. **Field Naming:** Tất cả fields trong Python code đã đổi sang tiếng Anh, nhưng database columns vẫn giữ nguyên tiếng Việt thông qua `db_column`
6. **Customer Model:** Đã bị xóa khỏi hệ thống, không còn lưu trữ thông tin khách hàng

---

## 7. HƯỚNG DẪN SỬ DỤNG

### 7.1. Khởi động dự án
```bash
cd site1
python manage.py migrate
python manage.py runserver
```

### 7.2. Import dữ liệu menu
```bash
cd site1
python import_menu.py
```

### 7.3. Truy cập ứng dụng
- Trang chủ: http://localhost:8000/
- Admin panel: http://localhost:8000/admin/
- API: http://localhost:8000/api/

---

---

## 8. HƯỚNG DẪN VẼ ERD (ENTITY RELATIONSHIP DIAGRAM)

### 8.1. Tổng quan về ERD

ERD mô tả cấu trúc database và quan hệ giữa các bảng. Trong hệ thống EMENU, có 6 entities chính.

### 8.2. Các Entities và Attributes

#### 1. **CATEGORY** (Danh mục)
```
Entity Name: CATEGORY
Table Name: categories
Attributes:
  - id (PK, Integer, Auto) - Primary Key
    Database Column: id_danhmuc
  - name (Varchar(100), Not Null)
    Database Column: ten_danhmuc
```

#### 2. **ITEM** (Món ăn)
```
Entity Name: ITEM
Table Name: items
Attributes:
  - id (PK, Integer, Auto) - Primary Key
    Database Column: id_mon
  - category (FK, Integer, Not Null) - Foreign Key → CATEGORY.id
    Database Column: id_danhmuc
  - name (Varchar(255), Not Null)
    Database Column: ten_mon
  - price (Integer, Not Null)
    Database Column: gia
  - image (Varchar(255), Nullable)
    Database Column: hinh_anh
```

#### 3. **TABLE** (Bàn)
```
Entity Name: TABLE
Table Name: tables
Attributes:
  - id (PK, Integer, Auto) - Primary Key
    Database Column: id_ban
  - number (Varchar(50), Unique, Not Null)
    Database Column: so_ban
  - status (Varchar(20), Not Null)
    Database Column: trang_thai
    Values: 'available', 'reserved', 'occupied'
  - reserved_at (DateTime, Nullable)
    Database Column: thoi_gian_dat
  - expires_at (DateTime, Nullable)
    Database Column: thoi_gian_het_han
```

#### 4. **ORDER** (Đơn hàng)
```
Entity Name: ORDER
Table Name: orders
Attributes:
  - id (PK, Integer, Auto) - Primary Key
    Database Column: id_donhang
  - table (FK, Integer, Not Null) - Foreign Key → TABLE.id
    Database Column: id_ban
  - total (Integer, Default: 0)
    Database Column: tong_tien
  - status (Varchar(20), Not Null)
    Database Column: trang_thai_tt
    Values: 'pending', 'preparing', 'ready', 'served', 'cancelled'
  - created_at (DateTime, Auto)
  - updated_at (DateTime, Auto)
```

#### 5. **ORDER_ITEM** (Chi tiết đơn hàng)
```
Entity Name: ORDER_ITEM
Table Name: order_items
Attributes:
  - id (PK, Integer, Auto) - Primary Key
    Database Column: id_chitiet
  - order (FK, Integer, Not Null) - Foreign Key → ORDER.id
    Database Column: id_donhang
  - item (FK, Integer, Not Null) - Foreign Key → ITEM.id
    Database Column: id_mon
  - quantity (Integer, Default: 1)
    Database Column: so_luong
  - note (Text, Nullable)
    Database Column: ghi_chu
  - is_served (Boolean, Default: False)
    Database Column: da_ra_mon
```

#### 6. **PAYMENT** (Thanh toán)
```
Entity Name: PAYMENT
Table Name: payments
Attributes:
  - id (PK, Integer, Auto) - Primary Key
    Database Column: id_tt
  - order (FK, Integer, Not Null) - Foreign Key → ORDER.id
    Database Column: id_donhang
  - method (Varchar(20), Not Null)
    Database Column: phuong_thuc
    Values: 'cash', 'card', 'momo', 'zalopay', 'banking'
  - paid_at (DateTime, Auto)
    Database Column: thoi_gian_tt
```

### 8.3. Các Relationships (Quan hệ)

#### 1. **CATEGORY (1) → ITEM (N)**
- **Relationship Name:** "Thuộc danh mục"
- **Cardinality:** One-to-Many (1:N)
- **Foreign Key:** `ITEM.category` → `CATEGORY.id`
- **Database Column:** `items.id_danhmuc` → `categories.id_danhmuc`
- **On Delete:** CASCADE

#### 2. **TABLE (1) → ORDER (N)**
- **Relationship Name:** "Đặt tại bàn"
- **Cardinality:** One-to-Many (1:N)
- **Foreign Key:** `ORDER.table` → `TABLE.id`
- **Database Column:** `orders.id_ban` → `tables.id_ban`
- **On Delete:** CASCADE

#### 3. **ORDER (1) → ORDER_ITEM (N)**
- **Relationship Name:** "Chứa chi tiết"
- **Cardinality:** One-to-Many (1:N)
- **Foreign Key:** `ORDER_ITEM.order` → `ORDER.id`
- **Database Column:** `order_items.id_donhang` → `orders.id_donhang`
- **On Delete:** CASCADE

#### 4. **ITEM (1) → ORDER_ITEM (N)**
- **Relationship Name:** "Được đặt"
- **Cardinality:** One-to-Many (1:N)
- **Foreign Key:** `ORDER_ITEM.item` → `ITEM.id`
- **Database Column:** `order_items.id_mon` → `items.id_mon`
- **On Delete:** CASCADE

#### 5. **ORDER (1) → PAYMENT (N)**
- **Relationship Name:** "Thanh toán"
- **Cardinality:** One-to-Many (1:N)
- **Foreign Key:** `PAYMENT.order` → `ORDER.id`
- **Database Column:** `payments.id_donhang` → `orders.id_donhang`
- **On Delete:** CASCADE

### 8.4. Sơ đồ ERD

```
┌─────────────────┐
│    CATEGORY     │
├─────────────────┤
│ id (PK)         │
│ name            │
└────────┬────────┘
         │ 1
         │ "Thuộc danh mục"
         │
         │ N
┌────────▼────────┐
│      ITEM       │
├─────────────────┤
│ id (PK)         │
│ category (FK)   │ → CATEGORY.id
│ name            │
│ price           │
│ image           │
└────────┬────────┘
         │ 1
         │ "Được đặt"
         │
         │ N
┌────────▼──────────────┐
│     ORDER_ITEM        │
├───────────────────────┤
│ id (PK)               │
│ order (FK)            │ → ORDER.id
│ item (FK)             │ → ITEM.id
│ quantity              │
│ note                  │
│ is_served             │
└───────────────────────┘

┌─────────────────┐
│     TABLE       │
├─────────────────┤
│ id (PK)         │
│ number (UNIQUE) │
│ status          │
│ reserved_at     │
│ expires_at      │
└────────┬────────┘
         │ 1
         │ "Đặt tại bàn"
         │
         │ N
┌────────▼────────┐
│     ORDER       │
├─────────────────┤
│ id (PK)         │
│ table (FK)      │ → TABLE.id
│ total           │
│ status          │
│ created_at      │
│ updated_at      │
└────────┬────────┘
         │ 1
         │
         ├──────────────────┐
         │ N                │ N
         │ "Chứa chi tiết"  │ "Thanh toán"
         │                  │
┌────────▼────────┐        │  ┌──────────────┐
│  ORDER_ITEM     │        │  │   PAYMENT    │
│ (đã vẽ ở trên)  │        │  ├──────────────┤
└─────────────────┘        │  │ id (PK)      │
                           │  │ order (FK)   │ → ORDER.id
                           │  │ method       │
                           │  │ paid_at      │
                           │  └──────────────┘
```

### 8.5. Hướng dẫn vẽ ERD trong PowerDesigner

#### Bước 1: Tạo Entities
1. Chọn **Entity** tool từ Palette
2. Click vào canvas để tạo entity
3. Double-click entity để mở Properties
4. Đặt tên entity (ví dụ: CATEGORY, ITEM, TABLE, ORDER, ORDER_ITEM, PAYMENT)

#### Bước 2: Thêm Attributes
1. Trong Properties → **Attributes** tab
2. Thêm từng attribute với:
   - **Name**: Tên field trong Python code (tiếng Anh)
   - **Code**: Tên cột trong database (tiếng Việt) - Optional
   - **Data Type**: Integer, Varchar, DateTime, Boolean, Text
   - **Primary Key**: Đánh dấu PK cho field `id`
   - **Mandatory**: Not Null
   - **Unique**: Đánh dấu cho `TABLE.number`

#### Bước 3: Tạo Relationships
1. Chọn **Relationship** tool từ Palette
2. Click và kéo từ entity cha (1) đến entity con (N)
3. Double-click relationship để đặt tên
4. Trong Properties → **Cardinality**:
   - Entity cha: **One (1)**
   - Entity con: **Many (N)**

#### Bước 4: Đặt Foreign Keys
1. Khi tạo relationship, PowerDesigner tự động tạo FK trong entity con
2. Hoặc thêm thủ công trong Attributes của entity con:
   - Tên: `category`, `table`, `order`, `item`
   - Data Type: Integer (hoặc Reference đến entity cha)
   - Foreign Key: Đánh dấu FK

#### Bước 5: Thêm Constraints
1. **Unique Constraint**: `TABLE.number`
2. **Check Constraints**:
   - `TABLE.status`: IN ('available', 'reserved', 'occupied')
   - `ORDER.status`: IN ('pending', 'preparing', 'ready', 'served', 'cancelled')
   - `PAYMENT.method`: IN ('cash', 'card', 'momo', 'zalopay', 'banking')

### 8.6. Lưu ý quan trọng khi vẽ ERD

1. **Tên trong ERD:**
   - Entity names: Dùng tên tiếng Anh (CATEGORY, ITEM, TABLE, ORDER, ORDER_ITEM, PAYMENT)
   - Attribute names: Dùng tên field trong Python code (id, name, price, status, etc.)
   - Có thể thêm comment hoặc note về tên cột database nếu cần

2. **Cardinality:**
   - Tất cả relationships đều là **One-to-Many (1:N)**
   - Một Category có nhiều Item
   - Một Table có nhiều Order
   - Một Order có nhiều OrderItem
   - Một Item có trong nhiều OrderItem
   - Một Order có thể có nhiều Payment

3. **Foreign Keys:**
   - Tất cả FK đều là **Not Null** (trừ khi có ghi chú nullable)
   - Cascade delete: Khi xóa Category → xóa Item, xóa Order → xóa OrderItem và Payment

4. **Indexes:**
   - Tạo index cho các FK để tăng hiệu suất truy vấn
   - Index cho `TABLE.number` (đã unique)

5. **Export ERD:**
   - Có thể export ERD thành hình ảnh (PNG, JPG) hoặc PDF từ PowerDesigner
   - File → Export → Image/PDF

---

**Tài liệu được cập nhật vào:** 2025-12-29
**Phiên bản:** 2.0
**Dự án:** EMENU - Hệ thống quản lý menu điện tử


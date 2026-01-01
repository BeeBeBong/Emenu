# TÀI LIỆU FORMAT API CHO FRONTEND

## 1. LẤY DANH SÁCH BÀN

**Endpoint:** `GET /api/tables/`

**Response:**
```json
[
  {
    "id": 1,
    "number": "Bàn 1",
    "status": "available",
    "reservedAt": null,
    "expiresAt": null
  },
  {
    "id": 2,
    "number": "Bàn 2",
    "status": "occupied",
    "reservedAt": null,
    "expiresAt": null
  }
]
```

**Các trạng thái bàn:**
- `available`: Trống
- `reserved`: Đã đặt trước
- `occupied`: Đang sử dụng

---

## 2. TẠO ĐƠN HÀNG

**Endpoint:** `POST /api/orders/create/`

**Request Body:**
```json
{
  "tableId": 1,
  "items": [
    {
      "itemId": 1,
      "quantity": 2,
      "note": "Không cay"
    },
    {
      "itemId": 3,
      "quantity": 1,
      "note": ""
    }
  ]
}
```

**Request Fields:**
- `tableId` (required): ID của bàn (lấy từ `GET /api/tables/`)
- `items` (required): Mảng các món ăn
  - `itemId` (required): ID của món ăn
  - `quantity` (optional, default: 1): Số lượng
  - `note` (optional): Ghi chú cho món

**Response (Success - 201):**
```json
{
  "id": 1,
  "tableId": 1,
  "tableNumber": "Bàn 1",
  "total": 180000,
  "status": "pending",
  "createdAt": "2025-12-28T11:14:51.427Z",
  "items": [
    {
      "id": 1,
      "itemId": 1,
      "name": "Phở Bò",
      "price": 50000,
      "quantity": 2,
      "note": "Không cay",
      "isServed": false
    },
    {
      "id": 2,
      "itemId": 3,
      "name": "Bánh Mì",
      "price": 30000,
      "quantity": 1,
      "note": "",
      "isServed": false
    }
  ]
}
```

**Response (Error - 400):**
```json
{
  "error": "Thiếu thông tin bàn (tableId)"
}
```

hoặc

```json
{
  "error": "tableId không hợp lệ",
  "detail": "tableId phải là số nguyên, nhận được: null"
}
```

hoặc

```json
{
  "error": "Danh sách món ăn không được để trống"
}
```

hoặc

```json
{
  "error": "itemId không hợp lệ",
  "detail": "itemId phải là số nguyên, nhận được: undefined"
}
```

**Response (Error - 404):**
```json
{
  "error": "Bàn không tồn tại",
  "detail": "Không tìm thấy bàn với ID: 999. Vui lòng kiểm tra lại hoặc lấy danh sách bàn từ GET /api/tables/"
}
```

hoặc

```json
{
  "error": "Món ăn không tồn tại",
  "detail": "Không tìm thấy món ăn với ID: 999"
}
```

**Response (Error - 500):**
```json
{
  "error": "Lỗi khi tạo đơn hàng",
  "detail": "Chi tiết lỗi..."
}
```

---

## 3. LẤY DANH SÁCH MÓN ĂN

**Endpoint:** `GET /api/menu/data/`

**Response:**
```json
{
  "categories": ["Món chính", "Món phụ", "Đồ uống"],
  "products": [
    {
      "id": 1,
      "name": "Phở Bò",
      "price": 50000,
      "img": "http://localhost:8000/media/menu/pho-bo.jpg",
      "category": "Món chính"
    },
    {
      "id": 2,
      "name": "Bánh Mì",
      "price": 30000,
      "img": "",
      "category": "Món phụ"
    }
  ]
}
```

---

## 4. LẤY DANH SÁCH ĐƠN HÀNG

**Endpoint:** `GET /api/orders/`

**Response:**
```json
[
  {
    "id": 1,
    "tableId": 1,
    "tableNumber": "Bàn 1",
    "total": 180000,
    "status": "pending",
    "createdAt": "2025-12-28T11:14:51.427Z",
    "items": [
      {
        "id": 1,
        "itemId": 1,
        "name": "Phở Bò",
        "price": 50000,
        "quantity": 2,
        "note": "Không cay",
        "isServed": false
      }
    ]
  }
]
```

**Các trạng thái đơn hàng:**
- `pending`: Chờ xử lý
- `preparing`: Đang làm
- `ready`: Đã xong
- `served`: Đã phục vụ
- `cancelled`: Đã hủy

---

## 5. ĐẶT TRƯỚC BÀN

**Endpoint:** `POST /api/tables/<id_ban>/reserve/`

**Ví dụ:** `POST /api/tables/1/reserve/`

**Response (Success - 200):**
```json
{
  "id": 1,
  "number": "Bàn 1",
  "status": "reserved",
  "reservedAt": "2025-12-28T11:14:51.427Z",
  "expiresAt": "2025-12-28T11:19:51.427Z"
}
```

**Response (Error - 400):**
```json
{
  "error": "Bàn không trống"
}
```

---

## LƯU Ý QUAN TRỌNG

1. **tableId là bắt buộc** khi tạo đơn hàng. Frontend cần:
   - Lấy danh sách bàn từ `GET /api/tables/`
   - Cho người dùng chọn bàn
   - Gửi `tableId` trong request body khi tạo đơn
   - `tableId` phải là số nguyên (integer), không phải string

2. **itemId** trong items phải là ID thực từ database (lấy từ `GET /api/menu/data/`)
   - `itemId` phải là số nguyên (integer)
   - `quantity` phải là số nguyên lớn hơn 0

3. Tất cả các endpoint đều trả về JSON format

4. Base URL: `http://localhost:8000` (hoặc domain của server)

5. **Nếu database chưa có bàn**, chạy script:
   ```bash
   cd site1
   python create_tables.py
   ```
   Script này sẽ tạo 30 bàn mẫu (Bàn 1 đến Bàn 30)


# 🔐 API Authentication Guide

## 1. Login Endpoint

### Request
```
POST /api/auth/login/
Content-Type: application/json

{
    "username": "admin",
    "password": "admin123"
}
```

### Response (Success)
```json
{
    "status": "success",
    "message": "Dang nhap thanh cong",
    "data": {
        "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
        "userId": 1,
        "fullName": "admin",
        "role": "ADMIN"
    }
}
```

### Response (Error)
```json
{
    "status": "error",
    "message": "Sai username hoac password"
}
```

---

## 2. Frontend Implementation

### Step 1: Login
```javascript
async function login(username, password) {
    const response = await fetch('/api/auth/login/', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({ username, password })
    });
    
    const data = await response.json();
    
    if (data.status === 'success') {
        // Save token and role
        localStorage.setItem('token', data.data.token);
        localStorage.setItem('role', data.data.role);
        localStorage.setItem('userId', data.data.userId);
        
        // Navigate based on role
        if (data.data.role === 'ADMIN' || data.data.role === 'STAFF') {
            window.location.href = '/dashboard';
        } else {
            window.location.href = '/menu';
        }
    } else {
        alert(data.message);
    }
}
```

### Step 2: Add Token to API Requests
```javascript
async function apiRequest(endpoint, options = {}) {
    const token = localStorage.getItem('token');
    
    const headers = {
        'Content-Type': 'application/json',
        ...options.headers
    };
    
    if (token) {
        headers['Authorization'] = `Bearer ${token}`;
    }
    
    const response = await fetch(`/api${endpoint}`, {
        ...options,
        headers
    });
    
    return response.json();
}

// Usage:
const revenue = await apiRequest('/revenue/');
```

### Step 3: Check Role on Frontend
```javascript
function checkPermission() {
    const role = localStorage.getItem('role');
    
    if (!role) {
        window.location.href = '/login';
        return false;
    }
    
    return role;
}

function isAdmin() {
    return localStorage.getItem('role') === 'ADMIN';
}

function isStaff() {
    return localStorage.getItem('role') === 'STAFF';
}

// Show dashboard only for admin/staff
if (isAdmin() || isStaff()) {
    // Show admin panel
    document.getElementById('admin-panel').style.display = 'block';
}
```

---

## 3. Test Accounts

| Username | Password | Role |
|----------|----------|------|
| admin | admin123 | ADMIN |
| staff | staff123 | STAFF |

---

## 4. Endpoints Requiring Authentication

### Get Current User
```
GET /api/auth/me/
Authorization: Bearer {token}
```

### Get Revenue Report (Admin/Staff only)
```
GET /api/revenue/
Authorization: Bearer {token}
```

---

## 5. Error Handling

### 401 Unauthorized
- Token missing or invalid
- Action: Redirect to login

### 403 Forbidden
- User doesn't have permission for this resource
- Action: Show error message

```javascript
async function apiRequest(endpoint, options = {}) {
    const response = await fetch(`/api${endpoint}`, {
        headers: {
            'Authorization': `Bearer ${localStorage.getItem('token')}`
        },
        ...options
    });
    
    if (response.status === 401) {
        localStorage.clear();
        window.location.href = '/login';
    } else if (response.status === 403) {
        alert('Ban khong co quyen truy cap tai nguyen nay');
    }
    
    return response.json();
}
```

---

## 6. Logout
```javascript
function logout() {
    localStorage.removeItem('token');
    localStorage.removeItem('role');
    localStorage.removeItem('userId');
    window.location.href = '/login';
}
```

---

## 7. JWT Token Structure

JWT tokens contain 3 parts separated by dots:
```
header.payload.signature
```

- **Header**: Algorithm & token type
- **Payload**: User data (userId, exp, iat)
- **Signature**: Encrypted hash

Token expires automatically. Frontend should refresh page or re-login if expired.

---

## Summary

1. Call `POST /api/auth/login/` with credentials
2. Save `token` and `role` from response
3. Add `Authorization: Bearer {token}` header to all API requests
4. Check `role` to show/hide UI elements
5. Handle 401/403 errors by redirecting to login

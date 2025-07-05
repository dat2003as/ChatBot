from pydantic import BaseModel, field_validator, validator
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum
# ===== EXISTING MODELS =====
class ChatMessage(BaseModel):
    message: str
    session_id: Optional[str] = None

class PaymentMethod(str, Enum):
    CASH_ON_DELIVERY = "cash_on_delivery"
    BANK_TRANSFER = "bank_transfer"
    CREDIT_CARD = "credit_card"
    E_WALLET = "e_wallet"
    PAYPAL = "paypal"

class ChatResponse(BaseModel):
    response: str
    session_id: str
    user_profile: dict = {}
    is_profile_complete: bool = False
    suggested_products: List[dict] = []
    cart_items: List[dict] = []
    # ✅ THÊM CÁC FIELD IMAGES QUAN TRỌNG
    images: List[dict] = []
    has_images: bool = False
    image_count: int = 0
    html_content: Optional[str] = None
    image_gallery: Optional[str] = None  # Alias cho html_content
    order_status: Optional[str]  = None  # Thêm trạng thái đơn hàng

class UserProfile(BaseModel):
    name: Optional[str] = None
    age: Optional[int] = None
    gender: Optional[str] = None
    preferences: List[str] = []
    budget_range: Optional[str] = None
    phone: Optional[str] = None  # Thêm số điện thoại
    address: Optional[str] = None  # Thêm địa chỉ
    is_complete: bool = False
    conversation_count: int = 0
    payment_method: Optional[str] = None


class Product(BaseModel):
    id: int
    title: str
    price: float
    description: str
    category: str
    image: str
    rating: Dict[str, float]

class ProductSearchRequest(BaseModel):
    query: str
    gender: Optional[str] = None
    min_price: Optional[float] = None
    max_price: Optional[float] = None
    category: Optional[str] = None
    limit: Optional[int] = 10

# ===== NEW ORDER MODELS =====
class OrderRequest(BaseModel):
    session_id: str
    product_ids: List[int]
    phone: str
    address: str
    payment_method: PaymentMethod = PaymentMethod.CASH_ON_DELIVERY
    notes: Optional[str] = ""
    total_amount: Optional[float]


class OrderResponse(BaseModel):
    order_id: str
    status: str
    total_amount: float
    payment_method: str
    message: str

class OrderInfo(BaseModel):
    id: str
    user_id: str
    product_ids: List[str]
    total_amount: float
    status: str
    order_date: str
    phone: str
    address: str
    payment_method: str
    notes: Optional[str] = None

    @field_validator('phone')
    def validate_phone(cls, v):
        import re
        phone_pattern = r'^(0[3|5|7|8|9])[0-9]{8}$'
        clean_v = v.replace(' ', '').replace('-', '')
        if not re.match(phone_pattern, clean_v):
            raise ValueError('Số điện thoại không hợp lệ. Vui lòng nhập số điện thoại Việt Nam.')
        return clean_v
    
    @field_validator('address')
    def validate_address(cls, v):
        v = v.strip()
        if len(v) < 10:
            raise ValueError('Địa chỉ quá ngắn. Vui lòng nhập địa chỉ chi tiết.')
        return v
    
    @field_validator('status')
    def validate_status(cls, v):
        allowed_statuses = ['pending', 'confirmed', 'shipped', 'delivered', 'cancelled']
        if v not in allowed_statuses:
            raise ValueError(f'Trạng thái không hợp lệ. Cho phép: {", ".join(allowed_statuses)}')
        return v
    
class OrderResponse(BaseModel):
    order_id: str
    status: str
    total_amount: float
    message: str

class OrderInfo(BaseModel):
    id: str
    user_id: str
    product_ids: List[int]
    total_amount: float
    status: str
    order_date: str
    phone: str
    address: str
    notes: Optional[str] = ""

class OrderStatusUpdate(BaseModel):
    order_id: str
    status: str
    
   

class ContactInfo(BaseModel):
    phone: str
    address: str
    
  

# ===== STATISTICS MODELS =====
class SystemStats(BaseModel):
    total_users: int
    total_orders: int
    total_revenue: float
    orders_by_status: Dict[str, int]
    products_loaded: int
    active_sessions: int
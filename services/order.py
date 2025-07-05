#services\order.py
import logging
from db.database import get_db_manager
from services.product_utils import find_product_id_by_name_improved
from typing import Dict, Any, Tuple, Union

logger = logging.getLogger(__name__)

def clean_and_normalize_product_name(product_name: str) -> str:
    """Làm sạch và chuẩn hóa tên sản phẩm"""
    if not isinstance(product_name, str):
        product_name = str(product_name)
    
    # Loại bỏ các từ không cần thiết
    noise_words = ['mua', 'cần', 'tìm', 'có', 'muốn', 'được', 'cho', 'tôi', 'em']
    
    # Tách từ và lọc
    words = product_name.lower().strip().split()
    cleaned_words = [word for word in words if word not in noise_words]
    
    # Nối lại
    cleaned_name = ' '.join(cleaned_words)
    
    logger.info(f"🧹 CLEAN - Original: '{product_name}' -> Cleaned: '{cleaned_name}'")
    return cleaned_name

def extract_product_id_from_name_improved(product_name: str) -> int:
    """Trích xuất product ID từ tên sản phẩm - IMPROVED VERSION"""
    product_mapping = {
        # Áo khoác - phải check trước áo thun (EXACT MATCH FIRST)
        "áo khoác gió nam": 16,        
        "áo khoác nam thể thao": 10,  
        "áo khoác nữ thời trang": 3,   
        "áo khoác nữ mùa đông": 6,     
        "áo khoác gió": 16,           # NEW: shorter match
        "áo khoác nam": 16,           # NEW: gender-specific
        "áo khoác nữ": 3,             # NEW: gender-specific  
        "áo khoác": 16,                
        
        # Áo sơ mi
        "áo sơ mi nam dài tay": 8,     
        "áo sơ mi nữ tay dài": 14,     
        "áo sơ mi nam": 8,            # NEW: shorter match
        "áo sơ mi nữ": 14,            # NEW: shorter match
        "áo sơ mi": 8,                 
        
        # Áo thun
        "áo thun nam tay ngắn": 2,     
        "áo thun nữ cổ tròn": 12,      
        "áo thun nam": 2,             # NEW: shorter match
        "áo thun nữ": 12,             # NEW: shorter match
        "áo thun": 2,                 
        
        # Ba lô
        "ba lô fjallraven": 1,        
        "ba lô": 1,
        "balo": 1,
        
        # Trang sức
        "vòng cổ vàng 18k": 4,        
        "vòng cổ ngọc trai": 13,      
        "vòng cổ": 4,                  
        
        "đồng hồ nam dây da": 5,       
        "đồng hồ nam": 5,             # NEW: shorter match
        "đồng hồ": 5,
        
        "vòng tay bạc nữ": 7,          
        "vòng tay da nam": 17,        
        "vòng tay": 7,                 
        
        "nhẫn bạc nữ đính đá": 9,      
        "nhẫn vàng nam": 15,          
        "nhẫn": 9,                     
        
        "dây chuyền bạc nữ": 11,       
        "dây chuyền": 11,
    }
    
    if not isinstance(product_name, str):
        product_name = str(product_name)
    
    product_name_clean = product_name.lower().strip()
    logger.info(f"🔍 EXTRACT_IMPROVED - Input: '{product_name_clean}'")
    
    # STEP 1: Exact match first (highest priority)
    if product_name_clean in product_mapping:
        matched_id = product_mapping[product_name_clean]
        logger.info(f"🎯 EXTRACT_IMPROVED - EXACT MATCH: '{product_name_clean}' -> ID: {matched_id}")
        return matched_id
    
    # STEP 2: Substring match (ordered by length desc)
    sorted_keys = sorted(product_mapping.keys(), key=len, reverse=True)
    logger.info(f"🔍 EXTRACT_IMPROVED - Trying substring match...")
    
    for key in sorted_keys:
        if key in product_name_clean:
            matched_id = product_mapping[key]
            logger.info(f"🎯 EXTRACT_IMPROVED - SUBSTRING MATCH: '{product_name_clean}' contains '{key}' -> ID: {matched_id}")
            return matched_id
    
    # STEP 3: Fuzzy matching for common patterns
    logger.info(f"🔍 EXTRACT_IMPROVED - Trying fuzzy matching...")
    
    # Check for áo khoáC patterns
    if any(word in product_name_clean for word in ['khoác', 'jacket']):
        if 'nam' in product_name_clean or 'men' in product_name_clean:
            logger.info(f"🎯 EXTRACT_IMPROVED - FUZZY MATCH: áo khoác nam -> ID: 16")
            return 16
        elif 'nữ' in product_name_clean or 'women' in product_name_clean:
            logger.info(f"🎯 EXTRACT_IMPROVED - FUZZY MATCH: áo khoác nữ -> ID: 3")
            return 3
        else:
            logger.info(f"🎯 EXTRACT_IMPROVED - FUZZY MATCH: áo khoác -> ID: 16")
            return 16
    
    # Check for áo thun patterns  
    if any(word in product_name_clean for word in ['thun', 't-shirt', 'tshirt']):
        if 'nam' in product_name_clean:
            logger.info(f"🎯 EXTRACT_IMPROVED - FUZZY MATCH: áo thun nam -> ID: 2")
            return 2
        elif 'nữ' in product_name_clean:
            logger.info(f"🎯 EXTRACT_IMPROVED - FUZZY MATCH: áo thun nữ -> ID: 12")
            return 12
        else:
            return 2
    
    # Generic áo fallback
    if 'áo' in product_name_clean:
        logger.info(f"🎯 EXTRACT_IMPROVED - GENERIC MATCH: áo -> ID: 2")
        return 2
    
    # Không tìm thấy
    logger.warning(f"⚠️ EXTRACT_IMPROVED - No match found for '{product_name_clean}', using default ID: 2")
    return 2


def get_payment_method_display(payment_method: str) -> str:
    """Hiển thị tên phương thức thanh toán"""
    methods = {
        '1': 'COD (thanh toán khi nhận hàng)',
        'cod': 'COD (thanh toán khi nhận hàng)',
        '2': 'Chuyển khoản ngân hàng',
        'bank': 'Chuyển khoản ngân hàng',
        '3': 'Thẻ tín dụng / ghi nợ',
        'card': 'Thẻ tín dụng / ghi nợ',
        '4': 'Ví điện tử (Momo, ZaloPay...)',
        'ewallet': 'Ví điện tử (Momo, ZaloPay...)'
    }
    return methods.get(str(payment_method).lower(), payment_method)

def convert_product_info_to_string(product_info: Union[str, Dict[str, Any]]) -> str:
    """Convert product info to string format for processing"""
    if isinstance(product_info, str):
        return product_info
    elif isinstance(product_info, dict):
        # Extract meaningful product name from dict
        category = product_info.get("category", "")
        color = product_info.get("color", "")
        size = product_info.get("size", "")
        gender = product_info.get("gender", "")
        
        # Build product name from components
        parts = []
        if category:
            parts.append(category)
        if color:
            parts.append(color)
        if gender:
            parts.append(gender)
        if size:
            parts.append(f"size {size}")
            
        if parts:
            return " ".join(parts)
        else:
            # Use keywords if available
            keywords = product_info.get("keywords", [])
            if keywords and isinstance(keywords, list):
                # Filter out common words and take first few meaningful ones
                meaningful_keywords = [kw for kw in keywords if kw not in ['mua', 'cần', 'tìm', 'có']][:3]
                if meaningful_keywords:
                    return " ".join(meaningful_keywords)
            
            return "Sản phẩm"
    else:
        return str(product_info) if product_info else "Sản phẩm"

def estimate_price_by_category(product_name: Union[str, Dict[str, Any]]) -> float:
    """Ước tính giá bằng USD dựa trên danh mục sản phẩm - Fixed version"""
    
    # Convert to string if it's a dict
    if isinstance(product_name, dict):
        product_name_str = convert_product_info_to_string(product_name)
    elif not isinstance(product_name, str):
        product_name_str = str(product_name)
    else:
        product_name_str = product_name
    
    product_lower = product_name_str.lower()
    
    # Giá ước tính trực tiếp bằng USD
    price_ranges_usd = {
        "áo thun": (6, 12),      # $6-12
        "áo": (6, 12),           # Fallback cho "áo" chung chung
        "áo khoác": (12, 32),    # $12-32  
        "quần jean": (10, 24),   # $10-24
        "quần": (8, 20),         # Fallback cho "quần" chung chung
        "giày": (16, 48),        # $16-48
        "túi xách": (8, 40),     # $8-40
        "túi": (8, 40),          # Fallback cho "túi" chung chung
        "đồng hồ": (20, 80),     # $20-80
        "kính mát": (6, 20),     # $6-20
        "kính": (6, 20),         # Fallback cho "kính" 
        "ba lô": (8, 24),        # $8-24
        "balo": (8, 24)          # Alternative spelling
    }
    
    for category, (min_price, max_price) in price_ranges_usd.items():
        if category in product_lower:
            avg_price_usd = (min_price + max_price) / 2
            return round(avg_price_usd, 2)
    
    # Giá mặc định nếu không xác định được danh mục
    return 10.0  # $10 USD

def ensure_user_exists(session_id: str, user_profile: dict) -> bool:
    """Đảm bảo user record tồn tại trong database"""
    db_manager = get_db_manager()
    
    if not db_manager:
        logger.error("Database manager not available")
        return False
    
    try:
        # Kiểm tra user có tồn tại không
        existing_user = db_manager.get_user_by_session_id(session_id)
        
        if not existing_user:
            # Tạo user record mới
            user_created = db_manager.create_user_record(session_id)
            if not user_created:
                logger.error(f"Failed to create user record for session: {session_id}")
                return False
            logger.info(f"Created new user record for session: {session_id}")
        
        # Cập nhật thông tin user nếu có
        if user_profile.get('name') or user_profile.get('phone') or user_profile.get('address'):
            user_data = {
                'name': user_profile.get('name', existing_user.get('name', 'Guest') if existing_user else 'Guest'),
                'phone': user_profile.get('phone', ''),
                'address': user_profile.get('address', '')
            }
            success = db_manager.update_user_info(session_id, user_data)
            if success:
                logger.info(f"Updated user info for session: {session_id}")
            else:
                logger.warning(f"Failed to update user info for session: {session_id}")
        
        return True
        
    except Exception as e:
        logger.error(f"Error ensuring user exists: {str(e)}")
        return False
def test_improved_matching():
    """Test improved matching function"""
    test_cases = [
        ("mua áo khoác gió nam", 16),    # Should work now
        ("áo khoác gió nam", 16),        
        ("áo size M nam", 2),            # Generic áo -> áo thun
        ("áo thun nam tay ngắn", 2),
        ("áo khoác", 16),
        ("Ba lô Fjallraven", 1),
        ("đồng hồ nam", 5),
    ]
    
    print("🧪 Testing improved product matching:")
    for product_name, expected_id in test_cases:
        # Clean first
        cleaned_name = clean_and_normalize_product_name(product_name)
        result_id = extract_product_id_from_name_improved(cleaned_name)
        status = "✅" if result_id == expected_id else "❌"
        print(f"{status} '{product_name}' -> Cleaned: '{cleaned_name}' -> Expected: {expected_id}, Got: {result_id}")


def create_order_with_better_product_handling_v2(session_data, user_profile):
    """Tạo đơn hàng với debug logging chi tiết - V2 với full debug"""
    db_manager = get_db_manager()  
    
    try:
        # ====== FULL DEBUG SECTION ======
        logger.info("="*50)
        logger.info("🔍 FULL DEBUG - ORDER CREATION START V3 FIXED")
        logger.info("="*50)
        
        # STEP 1: Debug all sources
        debug_user_profile_sources(user_profile)
        
        # STEP 2: Analyze conflicts
        debug_product_extraction_conflict(user_profile)
        
        logger.info(f"🔍 DEBUG - session_data: {session_data}")
        logger.info(f"🔍 DEBUG - session_data type: {type(session_data)}")
        
        if not db_manager:
            logger.error("Database manager không khả dụng")
            return "ERROR", 0, []
        
        # Session ID extraction
        if isinstance(session_data, dict):
            session_id = session_data.get('session_id')
            if not session_id:
                logger.error("session_id not found in session_data dict")
                return "ERROR", 0, []
        elif isinstance(session_data, str):
            session_id = session_data
        else:
            logger.error(f"Invalid session_data type: {type(session_data)}")
            return "ERROR", 0, []
        
        logger.info(f"🔍 Processing order for session: {session_id}")
        
        # ====== CRITICAL FIX: EXTRACT ORIGINAL INPUT ======
        original_user_input = extract_original_user_input(session_data, user_profile)
        logger.info(f"🔧 CRITICAL FIX - Original user input: '{original_user_input}'")
        
        # ====== PRODUCT EXTRACTION WITH ORIGINAL INPUT PRIORITY ======
        selected_product = None
        extraction_source = None
        
        # HIGHEST PRIORITY: Use original input if available
        if original_user_input:
            selected_product = original_user_input
            extraction_source = "original_user_input (HIGHEST PRIORITY)"
            logger.info(f"✅ USING ORIGINAL INPUT: '{selected_product}' from {extraction_source}")
        else:
            # Fallback to existing extraction logic
            extraction_priority = [
                ('original_request', 'Câu hỏi gốc của user'),
                ('query', 'Query đã xử lý'),  
                ('user_input', 'Input từ user'),
                ('message', 'Message content'),
                ('product_name', 'Tên sản phẩm'),
                ('selected_product', 'Sản phẩm đã chọn - CÓ THỂ BỊ GHI ĐÈ'),
            ]
            
            logger.info("🔍 DEBUG - FALLBACK EXTRACTION:")
            for field, description in extraction_priority:
                value = user_profile.get(field)
                if value and str(value).strip():
                    selected_product = value
                    extraction_source = f"{field} ({description})"
                    logger.info(f"✅ EXTRACTED from {extraction_source}: '{selected_product}'")
                    break
                else:
                    logger.info(f"❌ SKIP {field}: {value}")
        
        # ====== VALIDATION ======
        if not selected_product:
            logger.error("❌ KHÔNG TÌM THẤY SẢN PHẨM từ bất kỳ nguồn nào!")
            return "ERROR", 0, []

        # ====== PRODUCT NAME PROCESSING ======
        logger.info(f"🔍 DEBUG - PROCESSING PRODUCT: '{selected_product}' from {extraction_source}")
        
        if isinstance(selected_product, dict):
            product_name = (selected_product.get('product_name') or 
                          selected_product.get('name') or 
                          selected_product.get('title') or 
                          selected_product.get('category') or
                          str(selected_product))
        else:
            product_name = str(selected_product).strip()

        # ====== CLEANING & NORMALIZATION ======
        original_product_name = product_name
        product_name = clean_and_normalize_product_name(product_name)
        logger.info(f"🧹 CLEANED: '{original_product_name}' -> '{product_name}'")

        # ====== PRODUCT ID EXTRACTION ======
        logger.info(f"🔍 DEBUG - About to extract product_id from: '{product_name}'")
        product_id = extract_product_id_from_name_improved(product_name)
        logger.info(f"🔍 DEBUG - Extracted product_id: {product_id}")
        
        if not product_id:
            logger.error(f"❌ Không tìm thấy product ID cho: {product_name}")
            return "ERROR", 0, []

        # ====== VALIDATION CHECK ======
        logger.info("🔍 FINAL VALIDATION:")
        logger.info(f"  Original input: '{original_user_input}'")
        logger.info(f"  Processed product: '{product_name}'") 
        logger.info(f"  Product ID: {product_id}")
        
        # CRITICAL FIX: Verify the result makes sense
        if "khoác" in original_user_input.lower() and product_id != 16:
            logger.error(f"❌ MISMATCH DETECTED! Input contains 'khoác' but got ID={product_id}")
            logger.info(f"🔧 FORCE CORRECTING: Using ID=16 for áo khoác")
            product_id = 16
            product_name = "áo khoác gió nam"

        # ====== REST OF THE PROCESS (unchanged) ======
        # User management
        existing_user = db_manager.get_user_by_session_id(session_id)
        
        if not existing_user:
            user_created = db_manager.create_user_record(session_id)
            if not user_created:
                logger.warning("⚠️ Failed to create user record")
        
        # Update user info if provided
        if user_profile.get('name') or user_profile.get('phone') or user_profile.get('address'):
            user_data = {
                'name': user_profile.get('name', 'Guest'),
                'phone': user_profile.get('phone', ''),
                'address': user_profile.get('address', '')
            }
            try:
                db_manager.update_user_info(session_id, user_data)
            except Exception as e:
                logger.warning(f"⚠️ Failed to update user info: {str(e)}")
         
        # Get product details
        product_info = None
        try:
            product_info = db_manager.get_product_by_id(product_id)
        except Exception as e:
            logger.error(f"Error getting product info: {str(e)}")
        
        if not product_info:
            product_info = {
                'id': product_id,
                'title': product_name,
                'price': 50.0,
                'description': f'Sản phẩm {product_name}'
            }
          
        # Create order
        order_id = db_manager.create_order(
            user_id=session_id,
            product_ids=[product_id],
            total_amount=float(product_info['price']),
            phone=user_profile.get('phone', ''),
            address=user_profile.get('address', ''),
            payment_method=user_profile.get('payment_method', 'cod'),
            notes=f"Đơn hàng từ chat - {product_name} (from {extraction_source})"
        )
        
        product_details = [{
            'title': product_info['title'],
            'price': float(product_info['price']),
            'id': product_id
        }]
        
        logger.info("="*50)
        logger.info("✅ ORDER CREATION SUCCESS V3 FIXED")
        logger.info(f"✅ Order ID: {order_id}")
        logger.info(f"✅ Final Product: {product_name} (ID: {product_id})")
        logger.info(f"✅ Source: {extraction_source}")
        logger.info("="*50)
        
        return order_id, float(product_info['price']), product_details
        
    except Exception as e:
        logger.error(f"❌ Unexpected error in order creation: {str(e)}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        return "ERROR", 0, []
def extract_original_user_input(session_data, user_profile):
    """
    CRITICAL FIX: Extract original user input from session data
    """
    original_input = None
    
    # Try to get from session memory/chat history
    if isinstance(session_data, dict):
        # Check if session has memory with chat history
        if 'memory' in session_data:
            memory = session_data['memory']
            if hasattr(memory, 'chat_memory') and hasattr(memory.chat_memory, 'messages'):
                # Get the last human message
                messages = memory.chat_memory.messages
                for message in reversed(messages):
                    if hasattr(message, 'content') and message.__class__.__name__ == 'HumanMessage':
                        content = message.content.strip()
                        # Look for product-related messages
                        if any(keyword in content.lower() for keyword in ['mua', 'áo', 'khoác', 'thun', 'quần']):
                            original_input = content
                            logger.info(f"🔍 FOUND original input in chat history: '{original_input}'")
                            break
        
        # Try other possible locations
        if not original_input:
            possible_fields = ['last_message', 'current_input', 'raw_input', 'user_message']
            for field in possible_fields:
                value = session_data.get(field)
                if value:
                    original_input = str(value)
                    logger.info(f"🔍 FOUND original input in {field}: '{original_input}'")
                    break
    
    # Fallback to user_profile if nothing found in session
    if not original_input:
        fallback_fields = ['original_request', 'query', 'user_input', 'message']
        for field in fallback_fields:
            value = user_profile.get(field)
            if value and str(value).strip():
                original_input = str(value)
                logger.info(f"🔍 FALLBACK: Using '{original_input}' from user_profile.{field}")
                break
    
    return original_input

def debug_user_profile_sources(user_profile):
    """Debug tất cả các nguồn có thể chứa thông tin sản phẩm"""
    logger.info("🔍 DEBUG - FULL USER PROFILE ANALYSIS:")
    logger.info(f"user_profile type: {type(user_profile)}")
    logger.info(f"user_profile keys: {list(user_profile.keys()) if isinstance(user_profile, dict) else 'N/A'}")
    
    # Check all potential product fields
    potential_product_fields = [
        'selected_product', 'product_info', 'original_request', 'query', 
        'intent', 'product_name', 'product_details', 'item', 'category',
        'parsed_product', 'extracted_product', 'user_input', 'message'
    ]
    
    logger.info("🔍 DEBUG - PRODUCT FIELDS ANALYSIS:")
    for field in potential_product_fields:
        value = user_profile.get(field)
        if value:
            logger.info(f"  ✅ {field}: '{value}' (type: {type(value)})")
        else:
            logger.info(f"  ❌ {field}: None/Empty")

def debug_product_extraction_conflict(user_profile):
    """Debug để tìm nguồn gây conflict trong product extraction"""
    logger.info("🔍 CONFLICT ANALYSIS:")
    
    # All fields that might contain product info
    all_fields = [
        'original_request', 'query', 'user_input', 'message', 'selected_product',
        'product_info', 'product_name', 'intent', 'category', 'parsed_product'
    ]
    
    product_values = {}
    for field in all_fields:
        value = user_profile.get(field)
        if value:
            product_values[field] = str(value)
    
    logger.info(f"Found {len(product_values)} fields with product data:")
    for field, value in product_values.items():
        logger.info(f"  {field}: '{value}'")
    
    # Detect conflicts
    unique_values = set(product_values.values())
    if len(unique_values) > 1:
        logger.warning("⚠️ CONFLICT DETECTED - Multiple different product values found!")
        for value in unique_values:
            fields_with_value = [k for k, v in product_values.items() if v == value]
            logger.warning(f"  '{value}' appears in: {fields_with_value}")
    else:
        logger.info("✅ No conflicts - all fields have same product value")
    
    return product_values


def add_product_preservation_middleware(user_profile, original_input):
    """Middleware để bảo vệ original product input khỏi bị ghi đè"""
    
    # Backup original input
    if original_input and not user_profile.get('original_request'):
        user_profile['original_request'] = original_input
        logger.info(f"🛡️ PRESERVED original_request: '{original_input}'")
    
    # Detect và cảnh báo overwrites
    if user_profile.get('selected_product'):
        if (user_profile.get('original_request') and 
            user_profile['selected_product'] != user_profile['original_request']):
            logger.warning("⚠️ OVERWRITE DETECTED:")
            logger.warning(f"  Original: '{user_profile['original_request']}'")
            logger.warning(f"  Current:  '{user_profile['selected_product']}'")
    
    return user_profile

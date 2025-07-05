
#utils\helpers.py

import re
def extract_product_from_message_improved(message: str) -> str:
    """
    Trích xuất thông tin sản phẩm từ tin nhắn
    """
    if not message:
        return ""
    
    message_lower = message.lower().strip()
    
    # Loại bỏ các từ nhiễu
    noise_words = ['mua', 'tôi', 'em', 'cho', 'cần', 'muốn', 'được', 'có', 'tìm']
    words = message_lower.split()
    filtered_words = [word for word in words if word not in noise_words]
    
    # Nối lại thành chuỗi sản phẩm
    product_name = ' '.join(filtered_words)
    
    return product_name if product_name else message

def check_purchase_intent_natural(message: str) -> bool:
    """
    Kiểm tra ý định mua hàng một cách tự nhiên
    """
    message_lower = message.lower().strip()
    
    # Các từ khóa thể hiện ý định mua hàng
    purchase_keywords = [
        "lấy", "mua", "đặt", "order", "chọn", "tôi lấy", "tôi mua", 
        "tôi đặt", "tôi chọn", "có thể mua", "muốn mua", "quyết định mua",
        "đặt hàng", "đặt mua", "book", "take", "get", "want this",
        "tôi quyết định", "ok lấy", "ok mua", "oke lấy", "được rồi",
        "tôi cần", "cho tôi", "gửi cho tôi", "ship cho tôi"
    ]
    product_keywords = [
        'áo', 'ao', 'quần', 'quan', 'giày', 'giay',
        'túi', 'tui', 'ba lô', 'balo', 'đồng hồ', 'dong ho',
        'kính', 'kinh', 'vòng', 'vong', 'nhẫn', 'nhan',
        'dây chuyền', 'day chuyen'
    ]
    # Kiểm tra các từ khóa
    has_purchase_intent = any(keyword in message_lower for keyword in purchase_keywords)
    
    # Kiểm tra có từ khóa sản phẩm
    has_product_mention = any(keyword in message_lower for keyword in product_keywords)
    
    # Có ý định mua nếu có từ khóa mua hàng + từ khóa sản phẩm
    result = has_purchase_intent and has_product_mention
    
    return result

def remove_consecutive_duplicates(words):
    """Loại bỏ từ lặp liên tiếp"""
    if not words:
        return []
    
    result = [words[0]]
    for i in range(1, len(words)):
        current_word = words[i].lower().strip()
        previous_word = words[i-1].lower().strip()
        
        # Chỉ thêm từ nếu khác từ trước đó
        if current_word != previous_word:
            result.append(words[i])
        else:
            # Kiểm tra xem có nên giữ từ lặp không (cho trường hợp đặc biệt)
            if should_keep_duplicate(current_word, result):
                result.append(words[i])
    
    return result

def remove_nearby_duplicates(words, window_size=3):
    """Loại bỏ từ lặp gần nhau (trong khoảng window_size từ) - Improved version"""
    if len(words) <= 1:
        return words
    
    result = []
    
    for i, word in enumerate(words):
        word_lower = word.lower().strip()
        should_add = True
        
        # Kiểm tra trong cửa sổ từ gần đây
        start_check = max(0, len(result) - window_size)
        recent_words = [w.lower().strip() for w in result[start_check:]]
        
        if word_lower in recent_words:
            # Từ đã xuất hiện gần đây, kiểm tra xem có nên giữ không
            if not should_keep_duplicate(word_lower, result):
                should_add = False
        
        if should_add:
            result.append(word)
    
    return result

def should_keep_duplicate(word, current_result):
    """Quyết định có nên giữ từ lặp hay không - Fixed version"""
    # Một số trường hợp đặc biệt có thể cần giữ từ lặp
    # Ví dụ: "bánh bánh mì" -> "bánh mì" 
    
    # Nếu từ lặp tạo thành cụm từ có nghĩa khác
    meaningful_duplicates = {
        'bánh': ['bánh mì', 'bánh kẹo', 'bánh ngọt'],
        'nước': ['nước hoa', 'nước ngọt', 'nước mắm'],
        'máy': ['máy tính', 'máy giặt', 'máy lạnh'],
        'áo': ['áo khoác', 'áo thun', 'áo sơ mi'],
        'quần': ['quần jean', 'quần áo', 'quần short'],
        'giày': ['giày thể thao', 'giày cao gót']
    }
    
    if word in meaningful_duplicates:
        # Kiểm tra 2-3 từ gần nhất để tạo thành cụm từ có nghĩa
        recent_words = current_result[-3:] if len(current_result) >= 3 else current_result
        current_text = ' '.join(recent_words).lower()
        
        for phrase in meaningful_duplicates[word]:
            # Kiểm tra xem việc thêm từ lặp có tạo thành cụm từ có nghĩa không
            potential_phrase = (current_text + ' ' + word).strip()
            if phrase in potential_phrase:
                return True
    
    return False

def validate_vietnamese_phone(phone: str) -> bool:
    """Validate Vietnamese phone number format"""
    # Remove spaces and special characters except +
    clean_phone = re.sub(r'[^\d+]', '', phone)
    patterns = [
        r'^0[3-9][0-9]{8}$',           # 0xxxxxxxxx (10 digits, starts with 03-09)
        r'^\+84[3-9][0-9]{8}$',        # +84xxxxxxxxx (12 chars)
        r'^84[3-9][0-9]{8}$'           # 84xxxxxxxxx (11 digits, without +)
    ]
    
    for pattern in patterns:
        if re.match(pattern, clean_phone):
            return True
    
    print(f"❌ Phone validation failed for: {clean_phone}")
    return False

def format_phone_number(phone: str) -> str:
    """Format phone number to standard Vietnamese format"""
    # Remove all non-digit characters except +
    clean_phone = re.sub(r'[^\d+]', '', phone)
    
    # Convert to standard 0xxxxxxxxx format
    if clean_phone.startswith('+84'):
        return '0' + clean_phone[3:]
    elif clean_phone.startswith('84') and len(clean_phone) == 11:
        return '0' + clean_phone[2:]
    else:
        return clean_phone
    
def extract_payment_method(message: str, user_profile: dict = None, context: str = None) -> str:
    """Trích xuất phương thức thanh toán từ tin nhắn - CONTEXT-AWARE VERSION"""
    message_lower = message.lower().strip()
    
    # CHỈ extract payment method khi đang trong context thanh toán
    payment_context_keywords = [
        "thanh toán", "payment", "cod", "chuyển khoản", "thẻ", "ví điện tử",
        "momo", "zalopay", "visa", "mastercard"
    ]
    
    # Nếu không có context payment và message không chứa từ khóa payment -> không extract
    if (context != "payment" and 
        not any(keyword in message_lower for keyword in payment_context_keywords)):
        return None
    
    # Mapping phương thức thanh toán với từ khóa CỤ THỂ và CHÍNH XÁC
    payment_methods_priority = [
        # Ưu tiên các từ khóa cụ thể trước
        {
            "method": "COD",
            "keywords": ["cod", "1", "thanh toán khi nhận", "nhận hàng", "ship cod", "giao hàng thu tiền"],
            "exact_match": True
        },
        {
            "method": "Bank Transfer", 
            "keywords": ["chuyển khoản", "2", "ck", "banking", "internet banking"],
            "exact_match": True
        },
        {
            "method": "Credit Card",
            "keywords": ["thẻ tín dụng", "thẻ", "visa", "mastercard", "3", "credit card", "debit card"],
            "exact_match": True  
        },
        {
            "method": "E-Wallet",
            "keywords": ["ví điện tử", "momo", "zalopay", "4", "vnpay", "shopeepay"],
            "exact_match": True
        }
    ]
    
    print(f"🔍 Checking payment method for: '{message}' with context: {context}")
    
    # Kiểm tra theo thứ tự ưu tiên
    for payment_info in payment_methods_priority:
        method_name = payment_info["method"]
        keywords = payment_info["keywords"]
        
        # Kiểm tra exact match hoặc partial match
        for keyword in keywords:
            if keyword in message_lower:
                # Đối với số, kiểm tra exact match
                if keyword.isdigit():
                    if message_lower.strip() == keyword or f" {keyword} " in f" {message_lower} ":
                        if user_profile is not None:
                            user_profile["payment_method"] = method_name
                            user_profile["payment_method_confirmed"] = True
                            print(f"✅ Payment method extracted (number): {method_name}")
                        return method_name
                else:
                    # Đối với text, kiểm tra có chứa keyword
                    if user_profile is not None:
                        user_profile["payment_method"] = method_name
                        user_profile["payment_method_confirmed"] = True
                        print(f"✅ Payment method extracted (text): {method_name}")
                    return method_name
    
    print(f"❌ No payment method found in: '{message}'")
    return None

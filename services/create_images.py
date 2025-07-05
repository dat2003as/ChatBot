#ervices\create_images.py
import json
import time
from difflib import SequenceMatcher
import re
from typing import List, Dict, Optional, Tuple
from fastapi import logger
import requests

# API endpoint
def detect_image_request(message: str) -> bool:
    """
    Phát hiện yêu cầu xem hình ảnh - PHIÊN BẢN CẢI THIỆN
    """
    message_lower = message.lower().strip()
    
    # Các từ khóa chỉ yêu cầu xem hình ảnh
    image_keywords = [
        # Trực tiếp
        'hình ảnh', 'hinh anh', 'ảnh', 'anh', 'hình', 'hinh',
        'image', 'picture', 'photo', 'pic',
        
        # Yêu cầu xem/hiển thị
        'xem ảnh', 'xem hình', 'xem hinh', 'xem anh',
        'cho xem', 'hiển thị', 'hien thi', 'show me',
        'muốn xem', 'muon xem', 'want to see',
        'tôi muốn xem', 'toi muon xem',
        'mình muốn xem', 'minh muon xem',
        
        # Cụm từ thường gặp
        'có hình', 'co hinh', 'có ảnh', 'co anh',
        'trông như thế nào', 'trong nhu the nao',
        'nó trông ra sao', 'no trong ra sao',
        'hình dạng', 'hinh dang', 'shape',
        
        # Yêu cầu trực quan
        'nhìn thế nào', 'nhin the nao', 'look like',
        'màu sắc', 'mau sac', 'color',
        'thiết kế', 'thiet ke', 'design',
        
        # Động từ xem
        'xem qua', 'xem thử', 'xem thu',
        'coi thử', 'coi thu', 'thử xem', 'thu xem'
    ]
    
    # Kiểm tra từng từ khóa
    for keyword in image_keywords:
        if keyword in message_lower:
            print(f"🖼️ Image keyword detected: '{keyword}' in '{message}'")
            return True
    
    # Kiểm tra pattern: "muốn/cần/tìm + [verb] + [product]"
    # Ví dụ: "muốn xem áo khoác", "cần xem laptop", "tìm hình giày"
    view_patterns = [
        r'muốn\s+(xem|coi|thấy|nhìn)',
        r'muon\s+(xem|coi|thay|nhin)',
        r'cần\s+(xem|coi|thấy|nhìn)',
        r'can\s+(xem|coi|thay|nhin)',
        r'tìm\s+(hình|ảnh|anh|hinh)',
        r'tim\s+(hinh|anh)',
        r'want\s+to\s+(see|view|look)',
        r'show\s+me',
        r'let\s+me\s+see'
    ]
    
    import re
    for pattern in view_patterns:
        if re.search(pattern, message_lower):
            print(f"🖼️ Image pattern detected: '{pattern}' in '{message}'")
            return True
    
    # Kiểm tra cụm từ có chứa sản phẩm + yêu cầu xem
    product_keywords = [
        'áo', 'ao', 'shirt', 'jacket', 'coat',
        'quần', 'quan', 'pants', 'jeans',
        'giày', 'giay', 'shoes', 'boot',
        'laptop', 'computer', 'máy tính', 'may tinh',
        'điện thoại', 'dien thoai', 'phone',
        'túi', 'tui', 'bag', 'backpack', 'balo',
        'đồng hồ', 'dong ho', 'watch',
        'nhẫn', 'nhan', 'ring',
        'vòng', 'vong', 'bracelet', 'necklace'
    ]
    
    # Nếu có từ khóa sản phẩm + từ xem/muốn
    has_product = any(prod in message_lower for prod in product_keywords)
    has_view_intent = any(word in message_lower for word in ['xem', 'coi', 'thấy', 'nhìn', 'muốn', 'muon', 'want', 'see', 'show'])
    
    if has_product and has_view_intent:
        print(f"🖼️ Product + view intent detected in: '{message}'")
        return True
    
    # Kiểm tra câu hỏi về hình dạng/màu sắc
    visual_questions = [
        'trông như thế nào', 'trong nhu the nao',
        'có màu gì', 'co mau gi', 'what color',
        'thiết kế ra sao', 'thiet ke ra sao', 'design',
        'hình dạng', 'hinh dang', 'shape',
        'nó như thế nào', 'no nhu the nao', 'what does it look like'
    ]
    
    for question in visual_questions:
        if question in message_lower:
            print(f"🖼️ Visual question detected: '{question}' in '{message}'")
            return True
    
    return False

def extract_product_name_from_image_request(message: str) -> Optional[str]:
    """Trích xuất tên sản phẩm từ yêu cầu xem hình - CẢI THIỆN"""
    # Các pattern thường gặp - CẢI THIỆN
    patterns = [
        r'(?:xem|coi|show)\s+(?:hình|ảnh)\s+(.+)',
        r'(?:hình|ảnh)\s+(?:của\s+)?(.+)',
        r'cho\s+(?:tôi\s+)?(?:xem|coi)\s+(.+)',
        r'hiển\s*thị\s+(.+)',
        r'(.+)\s+(?:trông|nhìn)\s+(?:như\s+)?(?:thế\s+)?nào',
        r'mẫu\s+mã\s+(.+)',
        r'thiết\s+kế\s+(.+)',
        r'kiểu\s+dáng\s+(.+)',
        # Thêm pattern mới
        r'tôi\s+muốn\s+xem\s+(?:hình|ảnh)\s+(.+)',
        r'muốn\s+xem\s+(?:hình|ảnh)\s+(.+)',
    ]
    
    message_clean = message.strip()
    for pattern in patterns:
        match = re.search(pattern, message_clean, re.IGNORECASE)
        if match:
            product_name = match.group(1).strip()
            # Loại bỏ các từ không cần thiết
            stop_words = ['của', 'này', 'đó', 'kia', 'không', 'có', 'được', 'là', 'thì', 'ạ', 'à']
            words = product_name.split()
            filtered_words = [word for word in words if word.lower() not in stop_words]
            result = ' '.join(filtered_words)
            print(f"🔍 Extracted product name: '{result}' from message: '{message}'")
            return result
    
    print(f"❌ Could not extract product name from: '{message}'")
    return None

def normalize_text_advanced(text: str) -> str:
    """Chuẩn hóa text nâng cao cho tiếng Việt"""
    if not text:
        return ""
    
    # Chuyển về lowercase
    text = text.lower()
    
    # Từ điển mapping tiếng Việt đầy đủ hơn
    vietnamese_map = {
        'à': 'a', 'á': 'a', 'ạ': 'a', 'ả': 'a', 'ã': 'a',
        'â': 'a', 'ầ': 'a', 'ấ': 'a', 'ậ': 'a', 'ẩ': 'a', 'ẫ': 'a',
        'ă': 'a', 'ằ': 'a', 'ắ': 'a', 'ặ': 'a', 'ẳ': 'a', 'ẵ': 'a',
        'è': 'e', 'é': 'e', 'ẹ': 'e', 'ẻ': 'e', 'ẽ': 'e',
        'ê': 'e', 'ề': 'e', 'ế': 'e', 'ệ': 'e', 'ể': 'e', 'ễ': 'e',
        'ì': 'i', 'í': 'i', 'ị': 'i', 'ỉ': 'i', 'ĩ': 'i',
        'ò': 'o', 'ó': 'o', 'ọ': 'o', 'ỏ': 'o', 'õ': 'o',
        'ô': 'o', 'ồ': 'o', 'ố': 'o', 'ộ': 'o', 'ổ': 'o', 'ỗ': 'o',
        'ơ': 'o', 'ờ': 'o', 'ớ': 'o', 'ợ': 'o', 'ở': 'o', 'ỡ': 'o',
        'ù': 'u', 'ú': 'u', 'ụ': 'u', 'ủ': 'u', 'ũ': 'u',
        'ư': 'u', 'ừ': 'u', 'ứ': 'u', 'ự': 'u', 'ử': 'u', 'ữ': 'u',
        'ỳ': 'y', 'ý': 'y', 'ỵ': 'y', 'ỷ': 'y', 'ỹ': 'y',
        'đ': 'd'
    }
    
    for vn_char, en_char in vietnamese_map.items():
        text = text.replace(vn_char, en_char)
    
    # Xóa ký tự đặc biệt, chỉ giữ chữ và số
    text = re.sub(r'[^a-z0-9\s]', ' ', text)
    
    # Xóa khoảng trắng thừa
    text = ' '.join(text.split())
    
    return text

def get_vietnamese_to_english_mapping() -> Dict[str, List[str]]:
    """Từ điển mapping tiếng Việt sang tiếng Anh mở rộng"""
    return {
        # Quần áo cơ bản
        'ao': ['shirt', 'top', 'blouse', 'tee', 't-shirt', 'jacket', 'coat', 'hoodie', 'sweater'],
        'quan': ['pants', 'trousers', 'jeans', 'shorts', 'bottom'],
        'vay': ['dress', 'skirt', 'gown'],
        'dam': ['dress', 'gown', 'evening'],
        
        # Loại áo cụ thể
        'thun': ['t-shirt', 'tee', 'shirt', 'cotton'],
        'polo': ['polo', 'shirt'],
        'somi': ['shirt', 'blouse', 'dress shirt', 'button', 'formal'],
        
        # Áo khoác
        'khoac': ['jacket', 'coat', 'hoodie', 'cardigan', 'sweater', 'blazer', 'windbreaker'],
        'gio': ['wind', 'windbreaker', 'light', 'jacket'],  # cho "áo khoác gió"
        'cardigan': ['cardigan', 'sweater'],
        'blazer': ['blazer', 'jacket'],
        
        # Giày dép
        'giay': ['shoes', 'sneakers', 'boots', 'footwear'],
        'dep': ['sandals', 'slippers', 'flip-flops'],
        'boot': ['boots', 'boot'],
        'sneaker': ['sneakers', 'shoes'],
        
        # Phụ kiện
        'tui': ['bag', 'purse', 'handbag', 'tote'],
        'balo': ['backpack', 'bag', 'rucksack'],
        'ba': ['backpack', 'bag'],  # cho "ba lô"
        'lo': ['backpack', 'bag'],  # cho "ba lô" 
        'mu': ['hat', 'cap', 'beanie'],
        'non': ['hat', 'cap'],
        'kinh': ['glasses', 'sunglasses', 'eyewear'],
        'mat': ['glasses', 'sunglasses'],  # cho "kính mát"
        
        # Đồng hồ
        'dongho': ['watch', 'clock', 'timepiece'],
        'dong': ['watch', 'clock'],
        'ho': ['watch', 'clock'],
        
        # Electronics
        'laptop': ['laptop', 'computer', 'notebook'],
        'phone': ['phone', 'smartphone', 'mobile'],
        'dien': ['phone', 'smartphone', 'mobile', 'electronic'],
        'thoai': ['phone', 'smartphone', 'mobile'],
        
        # Gender & Age
        'nam': ['men', 'male', 'man', "men's"],
        'nu': ['women', 'female', 'woman', "women's"],
        'tre': ['kids', 'children', 'child'],
        'em': ['kids', 'children', 'child'],
        
        # Colors (bonus)
        'den': ['black'],
        'trang': ['white'],
        'do': ['red'],
        'xanh': ['blue', 'green'],
        'vang': ['yellow'],
        'tim': ['purple'],
        
        # Materials
        'cotton': ['cotton'],
        'polyester': ['polyester'],
        'denim': ['denim', 'jeans'],
        'da': ['leather'],
        'vai': ['fabric', 'cloth'],
    }

def search_products_by_name_improved(product_name: str, limit: int = 10, user_profile: Dict = None) -> List[Dict]:
    """
    Tìm kiếm sản phẩm theo tên với logic được cải thiện - VERSION 3.0
    FIX: Loại bỏ hoàn toàn kết quả không liên quan
    """
    if not product_name or not product_name.strip():
        print("❌ Empty product name")
        return []
    
    query_normalized = normalize_text_advanced(product_name)
    query_words = set(query_normalized.split())
    
    print(f"🔍 Searching for: '{product_name}' -> normalized: '{query_normalized}'")
    print(f"🔍 Query words: {query_words}")
    
    # Lấy từ điển mapping
    vietnamese_keywords = get_vietnamese_to_english_mapping()
    
    # Tìm từ khóa tiếng Anh tương ứng
    english_terms = set()
    
    for word in query_words:
        if word in vietnamese_keywords:
            english_terms.update(vietnamese_keywords[word])
            print(f"🔄 Mapped '{word}' -> {vietnamese_keywords[word]}")
        else:
            english_terms.add(word)
    
    # Xử lý trường hợp đặc biệt
    if 'khoac' in query_words and 'gio' in query_words:
        english_terms.update(['windbreaker', 'wind jacket', 'light jacket'])
        print("🌪️ Special case: áo khoác gió -> windbreaker")
    
    if not english_terms:
        english_terms = query_words
        
    print(f"🎯 Final search terms: {english_terms}")
    
    # Xác định category chính và từ khóa bắt buộc
    main_category = detect_product_category(query_words, english_terms)
    required_keywords = extract_required_keywords(query_words, english_terms)
    print(f"🏷️ Detected main category: {main_category}")
    print(f"🔑 Required keywords: {required_keywords}")
    
    # Load products data
    try:
        from db.sql_api import DatabaseManager
        db_api = DatabaseManager()
        products_data = db_api.get_all_products()
        
        if not products_data:
            print("❌ No products data available")
            return []   
    except Exception as e:
        print(f"❌ Error loading products: {str(e)}")
        return []
    
    # Ensure products_data is a list
    if isinstance(products_data, dict):
        if 'products' in products_data:
            products_data = products_data['products']
        elif 'data' in products_data:
            products_data = products_data['data']
        else:
            print(f"❌ products_data keys: {products_data.keys()}")
            return []
    
    if not isinstance(products_data, list):
        print(f"❌ products_data is not a list: {type(products_data)}")
        return []
    
    print(f"📦 Processing {len(products_data)} products...")
    
    # Tìm kiếm với logic filtering nghiêm ngặt
    matching_products = []
    
    try:
        for product in products_data:
            if not product or not isinstance(product, dict):
                continue
                
            # Lấy thông tin sản phẩm
            title = str(product.get('title', ''))
            description = str(product.get('description', ''))
            category = str(product.get('category', ''))
            brand = str(product.get('brand', ''))
            
            # Chuẩn hóa text
            title_normalized = normalize_text_advanced(title)
            description_normalized = normalize_text_advanced(description)
            category_normalized = normalize_text_advanced(category)
            brand_normalized = normalize_text_advanced(brand)
            
            full_text = f"{title_normalized} {description_normalized} {category_normalized} {brand_normalized}"
            product_words = set(full_text.split())
            
            # 🔥 STRICT FILTERING - Kiểm tra từ khóa bắt buộc
            if required_keywords and not has_required_keywords(full_text, required_keywords):
                print(f"❌ Missing required keywords in '{title}' - SKIPPED")
                continue
            
            # Category filtering
            product_category = detect_product_category(product_words, product_words)
            if main_category and product_category:
                if is_strict_category_mismatch(main_category, product_category, query_words):
                    print(f"❌ Strict category mismatch: Query({main_category}) vs Product({product_category}) - '{title}' SKIPPED")
                    continue
            
            # Blacklist filtering - Nghiêm ngặt hơn
            if has_strict_irrelevant_keywords(full_text, main_category, query_words):
                print(f"🚫 Strict irrelevant keywords detected in '{title}' - SKIPPED")
                continue
            
            # Tính điểm với logic cải thiện
            score = calculate_enhanced_score(
                product, query_words, english_terms, 
                title_normalized, description_normalized, 
                category_normalized, brand_normalized, 
                main_category, required_keywords
            )
            
            # Threshold nghiêm ngặt hơn
            MIN_SCORE_THRESHOLD = 20  # Tăng từ 15 lên 25
            
            if score >= MIN_SCORE_THRESHOLD:
                product_copy = product.copy()
                product_copy['similarity_score'] = score
                matching_products.append((product_copy, score))
                
                if score >= 70:
                    print(f"🌟 EXCELLENT: '{title}' (Score: {score})")
                elif score >= 40:
                    print(f"✅ GOOD: '{title}' (Score: {score})")
                else:
                    print(f"🔍 OK: '{title}' (Score: {score})")
            else:
                print(f"❌ LOW SCORE: '{title}' (Score: {score}) - FILTERED OUT")
        
        print(f"\n📊 Found {len(matching_products)} relevant products (after strict filtering)")
        
        # Sắp xếp và áp dụng advanced filtering
        matching_products.sort(key=lambda x: x[1], reverse=True)
        
        # Advanced filtering: Nếu có sản phẩm điểm cao, loại bỏ sản phẩm điểm thấp
        final_results = apply_advanced_filtering(matching_products, limit)
        
        print("🏆 FINAL TOP RESULTS:")
        for i, (product, score) in enumerate(final_results[:5]):
            print(f"  {i+1}. {product['title']} - Score: {score}")
        
        return [product for product, score in final_results]
        
    except Exception as e:
        print(f"❌ Error in search_products_by_name_improved: {str(e)}")
        import traceback
        traceback.print_exc()
        return []

def extract_required_keywords(query_words: set, english_terms: set) -> set:
    """
    Trích xuất từ khóa bắt buộc phải có trong sản phẩm
    """
    required = set()
    
    # Các từ khóa loại sản phẩm bắt buộc
    product_type_keywords = {
        'ao', 'quan', 'giay', 'dep', 'tui', 'balo', 'nhan', 'vong', 'day',
        'laptop', 'phone', 'may', 'tinh', 'dong', 'ho', 'kinh', 'mat',
        'shirt', 'jacket', 'pants', 'shoes', 'bag', 'ring', 'necklace',
        'computer', 'watch', 'glasses'
    }
    
    # Từ khóa loại vải/chất liệu cho quần áo
    clothing_keywords = {
        'khoac', 'thun', 'jean', 'short', 'dai', 'ngan'
    }
    
    # Tìm từ khóa bắt buộc trong query
    for word in query_words.union(english_terms):
        if word in product_type_keywords:
            required.add(word)
        elif word in clothing_keywords and any(cloth in query_words for cloth in ['ao', 'quan']):
            required.add(word)
    
    # Trường hợp đặc biệt: áo khoác gió
    if 'ao' in query_words and 'khoac' in query_words:
        required.update(['jacket', 'coat', 'khoac'])
    
    return required


def has_required_keywords(full_text: str, required_keywords: set) -> bool:
    """
    Kiểm tra xem sản phẩm có chứa ít nhất một từ khóa bắt buộc
    """
    if not required_keywords:
        return True
    
    # Phải có ít nhất 1 từ khóa bắt buộc
    return any(keyword in full_text for keyword in required_keywords)


def is_strict_category_mismatch(main_category: str, product_category: str, query_words: set) -> bool:
    """
    Kiểm tra category mismatch nghiêm ngặt hơn
    """
    if main_category == 'general' or product_category == 'general':
        return False
    
    # Các category hoàn toàn không tương thích
    strict_incompatible = {
        'clothing': ['jewelry', 'electronics', 'books'],
        'jewelry': ['clothing', 'electronics', 'shoes', 'bags'],
        'electronics': ['clothing', 'jewelry', 'shoes'],
        'shoes': ['jewelry', 'electronics', 'books'],
        'bags': ['jewelry', 'electronics'],
        'books': ['clothing', 'jewelry', 'electronics', 'shoes']
    }
    
    # Nếu query rõ ràng về 1 category, loại bỏ hoàn toàn category khác
    if main_category in strict_incompatible:
        if product_category in strict_incompatible[main_category]:
            return True
    
    # Đặc biệt nghiêm ngặt với jewelry
    if 'jewelry' in [main_category, product_category]:
        jewelry_words = {'nhan', 'vong', 'day', 'chuyen', 'ring', 'necklace', 'bracelet', 'gold', 'silver'}
        clothing_words = {'ao', 'quan', 'shirt', 'jacket', 'pants', 'dress'}
        
        has_jewelry_intent = bool(jewelry_words.intersection(query_words))
        has_clothing_intent = bool(clothing_words.intersection(query_words))
        
        if has_clothing_intent and product_category == 'jewelry':
            return True
        if has_jewelry_intent and product_category == 'clothing':
            return True
    
    return False


def has_strict_irrelevant_keywords(full_text: str, main_category: str, query_words: set) -> bool:
    """
    Kiểm tra từ khóa không liên quan nghiêm ngặt
    """
    # Blacklist nghiêm ngặt cho từng category
    strict_blacklists = {
        'clothing': {
            'must_not_have': ['ring', 'necklace', 'bracelet', 'earring', 'gold chain', 'silver chain', 
                             'diamond', 'jewelry', 'laptop', 'computer', 'phone', 'tablet'],
            'clothing_context_required': True
        },
        'jewelry': {
            'must_not_have': ['shirt', 'jacket', 'pants', 'dress', 'coat', 'laptop', 'computer'],
            'jewelry_context_required': True
        },
        'electronics': {
            'must_not_have': ['ring', 'necklace', 'shirt', 'jacket', 'dress', 'gold', 'silver'],
            'electronics_context_required': True
        }
    }
    
    if main_category in strict_blacklists:
        blacklist_config = strict_blacklists[main_category]
        
        # Kiểm tra từ khóa cấm
        for forbidden_word in blacklist_config['must_not_have']:
            if forbidden_word in full_text:
                print(f"🚫 Found forbidden word '{forbidden_word}' for category '{main_category}'")
                return True
    
    # Đặc biệt nghiêm ngặt: nếu tìm áo khoác mà sản phẩm có "gold", "silver", "ring" -> loại bỏ
    clothing_query = any(word in query_words for word in ['ao', 'khoac', 'shirt', 'jacket', 'coat'])
    if clothing_query:
        jewelry_indicators = ['gold', 'silver', 'diamond', 'ring', 'necklace', 'bracelet', 'chain']
        if any(indicator in full_text for indicator in jewelry_indicators):
            print(f"🚫 Clothing query but found jewelry indicators in product")
            return True
    
    return False


def calculate_enhanced_score(product: dict, query_words: set, english_terms: set, 
                           title_normalized: str, description_normalized: str,
                           category_normalized: str, brand_normalized: str,
                           main_category: str, required_keywords: set) -> int:
    """
    Tính điểm với logic cải thiện và bonus/penalty rõ ràng
    """
    score = 0
    
    # Phase 1: Title matching (trọng số cao nhất)
    title_words = set(title_normalized.split())
    query_coverage = len(query_words.intersection(title_words)) / len(query_words) if query_words else 0
    
    if query_coverage >= 0.9:  # Gần như exact match
        score += 120
    elif query_coverage >= 0.7:
        score += 100
    elif query_coverage >= 0.5:
        score += 80
    elif query_coverage >= 0.3:
        score += 50
    
    # Phase 2: Required keywords bonus
    if required_keywords:
        found_required = sum(1 for kw in required_keywords if kw in title_normalized)
        score += found_required * 20
    
    # Phase 3: Category alignment
    if main_category:
        category_bonus = calculate_strict_category_bonus(main_category, category_normalized, title_normalized)
        score += category_bonus
    
    # Phase 4: Keyword matching với penalty cho mismatch
    for term in english_terms:
        if term in title_normalized:
            score += 25
        elif term in category_normalized:
            score += 15
        elif term in description_normalized:
            score += 8
    
    # Phase 5: Quality bonuses
    rating = product.get('rating_rate', 0)
    if not rating and product.get('rating') and isinstance(product['rating'], dict):
        rating = product['rating'].get('rate', 0)
    
    if rating >= 4.5:
        score += 10
    elif rating >= 4.0:
        score += 5
    
    # Phase 6: Penalty cho mismatch nghiêm trọng
    if has_severe_mismatch(query_words, title_normalized, description_normalized):
        score -= 30
    
    return max(0, score)


def calculate_strict_category_bonus(main_category: str, category_normalized: str, title_normalized: str) -> int:
    """
    Tính bonus cho category matching nghiêm ngặt
    """
    category_mappings = {
        'clothing': ['clothing', 'shirt', 'jacket', 'coat', 'dress', 'pants', 'apparel', 'fashion'],
        'jewelry': ['jewelry', 'ring', 'necklace', 'bracelet', 'chain', 'gold', 'silver'],
        'electronics': ['electronics', 'computer', 'laptop', 'phone', 'tablet', 'tech'],
        'shoes': ['shoes', 'sneaker', 'boot', 'sandal', 'footwear'],
        'bags': ['bag', 'backpack', 'handbag', 'purse', 'luggage']
    }
    
    if main_category in category_mappings:
        target_words = category_mappings[main_category]
        full_text = f"{category_normalized} {title_normalized}"
        
        for word in target_words:
            if word in full_text:
                return 30
    
    return 0


def has_severe_mismatch(query_words: set, title: str, description: str) -> bool:
    """
    Kiểm tra mismatch nghiêm trọng
    """
    # Nếu query về quần áo mà product chủ yếu về jewelry
    clothing_intent = bool({'ao', 'quan', 'shirt', 'jacket', 'coat', 'dress', 'pants'}.intersection(query_words))
    jewelry_signals = ['gold', 'silver', 'diamond', 'ring', 'necklace', 'bracelet', 'jewelry']
    
    if clothing_intent:
        jewelry_count = sum(1 for signal in jewelry_signals if signal in f"{title} {description}")
        if jewelry_count >= 2:  # Nhiều dấu hiệu jewelry
            return True
    
    return False


def apply_advanced_filtering(matching_products: list, requested_limit: int) -> list:
    """
    Áp dụng advanced filtering để loại bỏ sản phẩm không phù hợp
    """
    if not matching_products:
        return []
    
    # Nếu có sản phẩm điểm rất cao (>=80), chỉ lấy những sản phẩm điểm cao
    top_score = matching_products[0][1]
    
    if top_score >= 80:
        # Lấy những sản phẩm có điểm >= 60% top score
        min_acceptable_score = top_score * 0.6
        filtered = [item for item in matching_products if item[1] >= min_acceptable_score]
        print(f"🔥 High-quality filtering: {len(filtered)} products with score >= {min_acceptable_score:.1f}")
        return filtered[:requested_limit]
    
    # Nếu có nhiều sản phẩm, loại bỏ những sản phẩm có điểm quá thấp
    if len(matching_products) > requested_limit:
        # Tính median score
        scores = [item[1] for item in matching_products]
        median_score = sorted(scores)[len(scores)//2]
        
        # Chỉ lấy sản phẩm có điểm >= median
        filtered = [item for item in matching_products if item[1] >= median_score]
        print(f"📊 Median filtering: {len(filtered)} products with score >= {median_score}")
        return filtered[:requested_limit]
    
    return matching_products[:requested_limit]

def detect_product_category(words: set, english_terms: set) -> str:
    """
    Xác định category chính của sản phẩm từ các từ khóa
    """
    categories = {
        'clothing': ['ao', 'quan', 'shirt', 'jacket', 'coat', 'dress', 'skirt', 'pants', 'jeans', 
                    'khoac', 'thun', 'hoodie', 'sweater', 'blazer', 'windbreaker'],
        'shoes': ['giay', 'dep', 'boot', 'sneaker', 'sandals', 'heels', 'shoes'],
        'electronics': ['laptop', 'phone', 'computer', 'tablet', 'headphone', 'camera', 'tv', 
                       'dien', 'thoai', 'may', 'tinh'],
        'jewelry': ['nhan', 'vong', 'day', 'chuyen', 'ring', 'necklace', 'bracelet', 'earring', 
                   'jewelry', 'gold', 'silver', 'diamond'],
        'bags': ['tui', 'balo', 'backpack', 'handbag', 'wallet', 'purse'],
        'accessories': ['dong', 'ho', 'watch', 'hat', 'cap', 'belt', 'scarf', 'sunglasses'],
        'sports': ['the', 'thao', 'gym', 'fitness', 'ball', 'sport'],
        'books': ['sach', 'book', 'novel', 'magazine'],
        'beauty': ['my', 'pham', 'cosmetic', 'makeup', 'skincare', 'perfume'],
        'home': ['nha', 'cua', 'home', 'furniture', 'decoration']
    }
    
    all_words = words.union(english_terms)
    
    for category, keywords in categories.items():
        if any(keyword in all_words for keyword in keywords):
            return category
    
    return 'general'

def get_product_images(product_name: str, limit: int = 3) -> List[Dict]:
    """
    Lấy hình ảnh sản phẩm từ database - SỬ DỤNG HÀM CẢI THIỆN
    """
    try:
        print(f"🔍 Getting images v2.1 for: '{product_name}'")
        
        # Sử dụng search function cải thiện
        products = search_products_by_name_improved(product_name, limit=limit*3)
        
        if not products:
            print(f"❌ No products found for: '{product_name}'")
            return []
        
        print(f"✅ Found {len(products)} products from search")
        
        images = []
        processed_urls = set()
        
        for product in products:
            if len(images) >= limit:
                break
            
            # Get image URL with fallbacks
            image_url = (
                product.get('image_url') or 
                product.get('image') or 
                product.get('thumbnail_url') or
                product.get('picture_url') or
                product.get('img_url')
            )
            
            if not image_url or image_url in processed_urls:
                continue
            
            processed_urls.add(image_url)
            
            # Create image data
            image_data = {
                'product_id': product.get('id', f"temp_{hash(product.get('title', ''))}"),
                'product_name': product.get('title', product_name),
                'image_url': image_url,
                'alt_text': f"{product.get('title', product_name)} - Product Image",
                'price': float(product.get('price', 0)),
                'description': str(product.get('description', ''))[:200],
                'thumbnail_url': product.get('thumbnail_url', image_url),
                'similarity_score': product.get('similarity_score', 0),
                'category': product.get('category', ''),
                'rating': product.get('rating_rate', 0)
            }
            
            images.append(image_data)
            print(f"  ✅ Added: {product.get('title')} (Score: {product.get('similarity_score', 0)})")
        
        print(f"✅ Final: {len(images)} images ready")
        return images
        
    except Exception as e:
        print(f"❌ Error getting images v2.1: {str(e)}")
        import traceback
        traceback.print_exc()
        return []

def validate_image_url(url: str) -> bool:
    """
    Validate image URL format
    """
    if not url or not isinstance(url, str):
        return False
        
    url = url.strip()
    
    # Check if it's a valid URL format
    if not (url.startswith('http://') or url.startswith('https://') or url.startswith('/')):
        return False
    
    # Check if it might be an image file
    image_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp', '.svg']
    url_lower = url.lower()
    
    # Either has image extension OR comes from known image domains
    has_image_ext = any(ext in url_lower for ext in image_extensions)
    known_domains = ['fakestoreapi.com', 'images.', 'img.', 'static.', 'cdn.', 'imgur.com']
    from_image_domain = any(domain in url_lower for domain in known_domains)
    
    return has_image_ext or from_image_domain


def create_image_data_object(product: dict, image_url: str, product_name: str) -> dict:
    """
    Tạo object chứa thông tin image hoàn chỉnh
    """
    return {
        'product_id': product.get('id', f"temp_{hash(product.get('title', ''))}"),
        'product_name': product.get('title', product_name),
        'image_url': image_url,
        'alt_text': f"{product.get('title', product_name)} - Product Image",
        'price': float(product.get('price', 0)),
        'description': str(product.get('description', ''))[:200] + ('...' if len(str(product.get('description', ''))) > 200 else ''),
        'thumbnail_url': product.get('thumbnail_url', image_url),
        'similarity_score': product.get('similarity_score', 0),
        'category': product.get('category', ''),
        'brand': product.get('brand', ''),
        'rating': product.get('rating_rate', product.get('rating', {}).get('rate', 0) if isinstance(product.get('rating'), dict) else 0),
        'in_stock': product.get('in_stock', True),
        # THÊM: Metadata để frontend biết cách render
        'display_priority': product.get('similarity_score', 0),
        'image_type': 'product_image',
        'show_details': True
    }

def get_product_image_url(product: dict) -> str:
    """
    Lấy image URL từ product với nhiều fallback options
    """
    # Thử các field khác nhau theo thứ tự ưu tiên
    print(f"🔍 Checking image URL for product: {product.get('title', 'Unknown')}")
    print(f"🔍 Available fields: {list(product.keys())}")
    
    # Thử các field khác nhau theo thứ tự ưu tiên
    image_fields = [
        'image_url', 'image', 'thumbnail_url', 'picture_url', 
        'img_url', 'photo_url', 'imageUrl', 'thumbnailUrl',
        'image_link', 'img', 'thumb', 'thumbnail'
    ]
    
    for field in image_fields:
        url = product.get(field)
        if url and isinstance(url, str) and url.strip():
            # Validate URL format
            if url.startswith(('http://', 'https://', 'data:')):
                print(f"    ✅ Found valid image in field '{field}': {url}")
                return url.strip()
            else:
                print(f"    ⚠️ Invalid URL format in field '{field}': {url}")
    
    # Nếu không tìm thấy, thử trong nested objects
    if 'images' in product and isinstance(product['images'], list) and product['images']:
        first_image = product['images'][0]
        if isinstance(first_image, str) and first_image.startswith(('http://', 'https://')):
            print(f"    ✅ Found image in images array: {first_image}")
            return first_image
        elif isinstance(first_image, dict):
            nested_url = get_product_image_url(first_image)
            if nested_url:
                return nested_url
    
    print(f"    ❌ No valid image URL found")
    return None
def create_image_response_text(images: List[Dict], product_name: str) -> str:
    """Tạo response text kèm theo hình ảnh - CẢI THIỆN"""
    if not images:
        return f"""🔍 Xin lỗi, mình không tìm thấy hình ảnh cho '{product_name}'. 

Có thể vì:
- Tên sản phẩm chưa chính xác
- Sản phẩm này chưa có hình ảnh
- Hệ thống đang cập nhật

Bạn có thể thử:
✅ Mô tả rõ hơn (ví dụ: "áo khoác gió nam màu đen")
✅ Dùng từ khóa khác (ví dụ: "jacket" thay vì "áo khoác")
✅ Hỏi "có những loại áo khoác nào?"

Mình sẵn sàng hỗ trợ bạn! 😊"""
    
    if len(images) == 1:
        product = images[0]
        return f"""🖼️ **Hình ảnh {product['product_name']}:**

📸 Đây là hình ảnh sản phẩm bạn yêu cầu ạ!
💰 Giá: ${product['price']:.2f}
⭐ Độ phù hợp: {product.get('similarity_score', 0)} điểm

{product['description'][:150]}{'...' if len(product['description']) > 150 else ''}

Bạn có muốn xem thêm thông tin chi tiết hoặc đặt hàng không? 
Chỉ cần nói "mình muốn mua {product['product_name']}" là được! 😊✨"""
    
    else:
        response = f"🖼️ **Hình ảnh các sản phẩm '{product_name}':**\n\n"
        response += "📸 Mình tìm thấy một số sản phẩm phù hợp:\n\n"
        
        for i, product in enumerate(images, 1):
            score = product.get('similarity_score', 0)
            response += f"{i}. **{product['product_name']}** - ${product['price']:.2f} (⭐{score} điểm)\n"
        
        response += f"\n✨ Tổng cộng {len(images)} sản phẩm được tìm thấy!"
        response += "\n\nBạn muốn xem chi tiết sản phẩm nào hoặc có câu hỏi gì khác không? "
        response += 'Chỉ cần nói "mình muốn mua [tên sản phẩm]" để đặt hàng! 😊🛒'
        
        return response
def handle_image_request_fixed(message: str, user_profile: Dict) -> str:
    """
    Xử lý yêu cầu xem hình ảnh - FIXED VERSION
    """
    print(f"🖼️ Processing image request (FIXED): '{message}'")
    
    # ✅ FIXED: Unpack 3 values instead of 2
    response_text, images_data, html_content = handle_image_request_with_display(message, user_profile)
    
    # If we have images, add them to the response
    if images_data and html_content:
        # For systems that support HTML
        final_response = response_text + "\n\n" + html_content
    elif images_data:
        # Fallback: Add simple image display
        simple_display = create_simple_image_display(images_data)
        final_response = response_text + simple_display
    else:
        final_response = response_text
    
    # Debug info
    print(f"📊 Final response length: {len(final_response)}")
    print(f"📊 Images included: {len(images_data)}")
    print(f"📊 HTML content: {'Yes' if html_content else 'No'}")
    
    return final_response
def create_simple_image_display(images: List[Dict]) -> str:
    """
    Tạo hiển thị hình ảnh đơn giản với markdown
    """
    if not images:
        return ""
    
    display = "\n\n📸 **Hình ảnh sản phẩm:**\n\n"
    
    for i, img in enumerate(images, 1):
        display += f"**{i}. {img['product_name']}** (${img['price']:.2f})\n"
        display += f"![{img['alt_text']}]({img['image_url']})\n"
        display += f"*{img.get('description', 'Không có mô tả')[:100]}...*\n\n"
    
    return display

def handle_image_request_with_display(message: str, user_profile: Dict) -> Tuple[str, List[Dict]]:
    """
    Xử lý yêu cầu xem hình ảnh - VERSION 2.1 với debug tốt hơn
    FIXED: Đồng bộ return type và actual return
    """
    print(f"🖼️ Processing image request v3.0: '{message}'")
    
    # Extract product name
    product_name = extract_product_name_from_image_request(message)
    
    if not product_name:
        no_product_response = """🤔 Bạn muốn xem hình ảnh sản phẩm nào ạ? 

Hãy cho mình biết cụ thể như:
• "Tôi muốn xem ảnh áo khoác gió nam"
• "Cho xem hình laptop gaming"  
• "Hình ảnh ba lô đi học"

Mình sẽ tìm và hiển thị hình ảnh cho bạn ngay! 😊📸"""
        return (no_product_response, [], "")
    
    # Get images
    print(f"🔍 Getting images for: '{product_name}'")
    images = get_product_images(product_name, limit=5)
    
    print(f"📊 Images retrieved: {len(images)} items")
    
    if not images:
        no_images_response = f"""🔍 Xin lỗi, mình không tìm thấy hình ảnh cho '{product_name}'. 

Có thể vì:
- Tên sản phẩm chưa chính xác  
- Sản phẩm này chưa có hình ảnh
- Hệ thống đang cập nhật

Bạn có thể thử:
✅ Mô tả rõ hơn: "áo khoác gió nam màu đen"
✅ Dùng từ khóa khác: "jacket windbreaker"  
✅ Hỏi: "có những loại áo khoác nào?"

Mình sẵn sàng hỗ trợ! 😊"""
        return (no_images_response, [], "")
    
    # Create HTML content for image display
    html_content = create_image_gallery_html(images, product_name)
    
    # Create text response
    if len(images) == 1:
        img = images[0]
        response_text = f"""🖼️ **Hình ảnh {img['product_name']}**

📸 Đây là sản phẩm bạn muốn xem!

💰 **Giá:** ${img['price']:.2f}
⭐ **Độ phù hợp:** {img.get('similarity_score', 0)} điểm
🏷️ **Danh mục:** {img.get('category', 'Chưa phân loại')}
{'📊 **Rating:** ' + str(img.get('rating', 0)) + '/5' if img.get('rating', 0) > 0 else ''}

📝 **Mô tả:** {img.get('description', 'Chưa có mô tả')}

---
🛒 **Mua ngay:** Nói "*mình muốn mua {img['product_name']}*"
❓ **Xem thêm:** Hỏi "*có màu/size nào khác không?*"

✨ *Hình ảnh đang được hiển thị bên dưới...*"""
    else:
        response_text = f"""🖼️ **Hình ảnh các sản phẩm '{product_name}'**

📸 Mình tìm thấy **{len(images)} sản phẩm** phù hợp:

"""
        for i, img in enumerate(images, 1):
            score = img.get('similarity_score', 0)
            score_emoji = "🌟" if score >= 50 else "✅" if score >= 30 else "🔍"
            
            response_text += f"""{score_emoji} **{i}. {img['product_name']}**
   💰 ${img['price']:.2f} | ⭐ {score} điểm | 🏷️ {img.get('category', 'N/A')}

"""
        
        response_text += """---
🛒 **Để mua:** "*mình muốn mua [tên sản phẩm]*"
📋 **Chi tiết:** "*cho xem thông tin chi tiết sản phẩm số [X]*"  

✨ *Tất cả hình ảnh đang được hiển thị bên dưới...*"""
    
    print(f"✅ Image request processed. Response: {len(response_text)} chars, Images: {len(images)}")
    return (response_text, images, html_content)

def create_image_gallery_html(images: List[Dict], product_name: str) -> str:
    """
    Tạo HTML gallery để hiển thị hình ảnh sản phẩm
    """
    if not images:
        return None
    
    html_parts = []
    html_parts.append('<div class="product-gallery" style="display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 15px; margin-top: 15px;">')
    
    for i, image in enumerate(images):
        # ✅ FIXED: Đảm bảo không có lỗi quote trong HTML
        image_url = str(image.get('image_url', '')).replace('"', '&quot;').replace("'", '&#39;')
        product_name = str(image.get('product_name', 'Sản phẩm')).replace('"', '&quot;').replace("'", '&#39;')
        alt_text = str(image.get('alt_text', product_name)).replace('"', '&quot;').replace("'", '&#39;')
        description = str(image.get('description', 'Không có mô tả')).replace('"', '&quot;').replace("'", '&#39;')
        
        # Cắt ngắn description
        if len(description) > 80:
            description = description[:80] + '...'
        
        html_parts.append(f'''
        <div class="product-card" style="border: 1px solid #ddd; border-radius: 8px; padding: 15px; background: #fff; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
            <img src="{image_url}" 
                 alt="{alt_text}"
                 style="width: 100%; height: 200px; object-fit: cover; border-radius: 4px; cursor: pointer;"
                 onload="console.log('✅ Image loaded')"
                 onerror="this.src='data:image/svg+xml,%3Csvg xmlns=\\'http://www.w3.org/2000/svg\\' width=\\'250\\' height=\\'200\\' viewBox=\\'0 0 250 200\\'%3E%3Crect width=\\'250\\' height=\\'200\\' fill=\\'%23f0f0f0\\'/%3E%3Ctext x=\\'125\\' y=\\'100\\' text-anchor=\\'middle\\' dy=\\'.3em\\' fill=\\'%23999\\' font-size=\\'12\\'%3EKhông tải được ảnh%3C/text%3E%3C/svg%3E';">
            
            <div style="margin-top: 10px;">
                <h4 style="margin: 5px 0; font-size: 16px; color: #333;">{product_name}</h4>
                <p style="margin: 5px 0; color: #e74c3c; font-weight: bold; font-size: 18px;">💰 ${image.get('price', '0.00')}</p>
                <p style="margin: 3px 0; color: #f39c12;">⭐ {image.get('similarity_score', 0)} điểm | 📊 {image.get('rating', 'N/A')}/5</p>
                <p style="margin: 8px 0; font-size: 14px; color: #666; line-height: 1.4;">{description}</p>
            </div>
        </div>
        ''')
    
    html_parts.append('</div>')
    html_parts.append('<div style="margin-top: 15px; padding: 10px; background: #f8f9fa; border-radius: 4px; font-size: 14px; color: #666;">💡 <strong>Mẹo:</strong> Nói "mình muốn mua [tên sản phẩm]" để đặt hàng nhanh!</div>')
    
    return ''.join(html_parts)
def handle_image_request_structured_fixed(message: str, user_profile: Dict) -> Dict:
    """
    Trả về structured data để frontend tự render - FIXED VERSION
    """
    # ✅ FIXED: Unpack 3 values  
    response_text, images_data, html_content = handle_image_request_with_display(message, user_profile)
    
    return {
        'type': 'image_response',
        'text': response_text,
        'images': images_data,
        'html': html_content,
        'success': len(images_data) > 0,
        'count': len(images_data)
    }

# Test function

def debug_image_pipeline(product_name: str):
    """
    Debug từng bước của image pipeline
    """
    print("🐛 === DEBUGGING IMAGE PIPELINE ===")
    user_profile = {'user_id': 'test', 'language': 'vi'}

    try:
        # Test the fixed function
        result = handle_image_request_fixed("tôi muốn xem ảnh áo khoác gió nam", user_profile)
        print("✅ FIXED: No more unpacking error!")
        print(f"📊 Result length: {len(result)}")
        print("🐛 === DEBUG COMPLETE ===")

        return result
        
    except Exception as e:
        print(f"❌ Still has error: {e}")
        import traceback
        traceback.print_exc()
        return None
    
    


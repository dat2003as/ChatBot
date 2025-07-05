# services/product_utils.py - PHIÊN BẢN CẢI THIỆN
from decimal import Decimal
import re
from typing import List, Dict, Any, Optional
import random
import logging

# Thiết lập logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def extract_product_from_message_improved(message: str) -> str:
    """
    Fixed version that returns a string instead of dict for compatibility
    """
    from startup.initializer import detect_gender
    
    message_lower = message.lower()
    
    # Danh mục sản phẩm và từ khóa (mở rộng hơn)
    categories = {
        "áo": ["áo", "shirt", "t-shirt", "áo sơ mi", "áo thun", "áo khoác", "hoodie", "sweater", "blouse", "top"],
        "quần": ["quần", "pants", "jeans", "quần jean", "quần short", "shorts", "trousers", "leggings"],
        "giày": ["giày", "shoes", "sneaker", "boots", "sandals", "dép", "giày thể thao", "giày cao gót"],
        "túi": ["túi", "bag", "backpack", "handbag", "balo", "túi xách", "clutch", "ví"],
        "phụ kiện": ["phụ kiện", "accessories", "mũ", "hat", "cap", "thắt lưng", "belt", "đồng hồ", "watch", "kính", "glasses"]
    }
    
    # Màu sắc (mở rộng)
    colors = ["đỏ", "xanh", "đen", "trắng", "vàng", "hồng", "nâu", "xám", "tím", "cam", 
              "red", "blue", "black", "white", "yellow", "pink", "brown", "gray", "purple", "orange",
              "xanh lá", "xanh dương", "be", "nude", "navy"]
    
    # Kích thước
    sizes = ["s", "m", "l", "xl", "xxl", "xs", "size s", "size m", "size l", "size xl", "3xl"]
    
    # Build product name parts
    product_parts = []
    
    # Trích xuất danh mục
    found_category = None
    for category, keywords in categories.items():
        if any(keyword in message_lower for keyword in keywords):
            found_category = category
            product_parts.append(category)
            break
    
    # Trích xuất màu sắc
    found_color = None
    for color in colors:
        if color in message_lower:
            found_color = color
            product_parts.append(color)
            break
    
    # Trích xuất kích thước
    found_size = None
    for size in sizes:
        if size in message_lower:
            found_size = size.upper()
            product_parts.append(f"size {found_size}")
            break
    
    # Trích xuất giới tính
    try:
        gender = detect_gender(message)
        if gender:
            product_parts.append(gender)
    except:
        pass  # Skip if detect_gender fails
    
    # Return combined product name
    if product_parts:
        return " ".join(product_parts)
    else:
        # Fallback: use first meaningful word from message
        words = message_lower.split()
        meaningful_words = [word for word in words if len(word) > 2 and word not in ['tôi', 'mình', 'muốn', 'cần', 'tìm', 'có', 'không', 'cho', 'với', 'mua']]
        if meaningful_words:
            return meaningful_words[0]
        return "sản phẩm"

def search_products_by_vietnamese_keywords(query: str, user_profile: Dict, filtered_products: List[Dict], limit: int = 5) -> List[Dict]:
    """
    Tìm kiếm sản phẩm theo từ khóa tiếng Việt trong danh sách đã lọc
    """
    try:
        if not filtered_products:
            logger.error("❌ filtered_products is empty")
            return []
            
        query_lower = query.lower().strip()
        logger.info(f"🔍 Tìm kiếm trong {len(filtered_products)} sản phẩm đã lọc với từ khóa: '{query}'")
        
        # Sử dụng lại logic từ search_products_by_vietnamese_keywords
        vietnamese_keywords = {
            'áo': ['shirt', 'top', 'blouse', 'tee', 't-shirt', 'áo', 'clothing', 'wear', 'jacket', 'coat', 'hoodie', 'sweater'],
            'quần': ['pants', 'trousers', 'jeans', 'shorts', 'quần', 'bottom'],
            'váy': ['dress', 'skirt', 'váy', 'gown'],
            'đầm': ['dress', 'gown', 'đầm', 'evening'],
            
            # Loại áo cụ thể - MỞ RỘNG
            'áo khoác': ['jacket', 'coat', 'hoodie', 'cardigan', 'sweater', 'blazer', 'windbreaker'],
            'áo thun': ['t-shirt', 'tee', 'shirt', 'polo'],
            'áo sơ mi': ['shirt', 'blouse', 'dress shirt', 'button', 'formal'],
            'khoác': ['jacket', 'coat', 'hoodie', 'cardigan', 'sweater', 'blazer', 'windbreaker'],
            
            # Giày dép
            'giày': ['shoes', 'sneakers', 'boots', 'giày', 'footwear'],
            'dép': ['sandals', 'slippers', 'flip-flops', 'dép'],
            
            # Phụ kiện - MỞ RỘNG
            'túi': ['bag', 'purse', 'backpack', 'túi', 'handbag', 'tote'],
            'balo': ['backpack', 'bag', 'balo', 'rucksack'],
            'mũ': ['hat', 'cap', 'mũ', 'beanie'],
            'kính': ['glasses', 'sunglasses', 'kính', 'eyewear'],
            'đồng hồ': ['watch', 'clock', 'đồng hồ', 'timepiece'],
            
            # Trang sức - MỞ RỘNG
            'nhẫn': ['ring', 'nhẫn', 'jewelry', 'band'],
            'dây chuyền': ['necklace', 'chain', 'dây chuyền', 'pendant'],
            'vòng tay': ['bracelet', 'bangle', 'vòng tay', 'wristband'],
            'vòng cổ': ['necklace', 'choker', 'vòng cổ', 'collar'],
            'trang sức': ['jewelry', 'accessory', 'trang sức', 'ornament'],
        }
        
        # Tìm từ khóa phù hợp
        search_terms = set()
        
        for vn_word, en_words in vietnamese_keywords.items():
            if vn_word in query_lower:
                search_terms.update(en_words)
                search_terms.add(vn_word)  # Thêm luôn từ tiếng Việt
                logger.info(f"✅ Tìm thấy từ khóa '{vn_word}' -> {en_words}")
        
        # Nếu không tìm thấy từ khóa cụ thể, sử dụng từ gốc
        if not search_terms:
            search_terms = set(query_lower.split())
            logger.info(f"🔄 Sử dụng từ khóa gốc: {list(search_terms)}")
        
        # Tìm kiếm trong danh sách đã lọc
        matching_products = []
        
        for product in filtered_products:
            if not product:
                continue
                
            # Tạo text để tìm kiếm
            title = str(product.get('title', ''))
            description = str(product.get('description', ''))
            category = str(product.get('category', ''))
            brand = str(product.get('brand', ''))
            color = str(product.get('color', ''))
            tags = str(product.get('tags', '')) if isinstance(product.get('tags'), str) else ''
            
            
            product_text = f"{title} {description} {category} {brand} {color} {tags}".lower()

            # Tính điểm phù hợp
            score = 0
            matched_terms = []
            primary_keywords = ['áo', 'quần', 'váy', 'đầm', 'giày', 'dép', 'túi', 'mũ', 'kính', 'đồng hồ', 'nhẫn']

             # Kiểm tra từ khóa với scoring khác nhau
            for term in search_terms:
                if re.search(r'\b' + re.escape(term) + r'\b', title.lower()):
                    if term in primary_keywords:
                            score += 20  # Tăng cao cho primary keywords trong title
                    else:
                            score += 10
                    matched_terms.append(f"title:{term}")
                    # Category match với word boundary  
                elif re.search(r'\b' + re.escape(term) + r'\b', category.lower()):
                    if term in primary_keywords:
                            score += 15  # Tăng cao cho primary keywords trong category
                    else:
                            score += 8
                    matched_terms.append(f"category:{term}")
                    # Description match - chỉ cho non-primary keywords
                elif term not in primary_keywords and re.search(r'\b' + re.escape(term) + r'\b', description.lower()):
                        score += 5
                        matched_terms.append(f"desc:{term}")
                    # General text match - penalty cho primary keywords không exact
                elif term in product_text:
                    if term in primary_keywords:
                            score += 1  # Penalty thấp cho match không chính xác
                    else:
                            score += 2
                    matched_terms.append(f"general:{term}")

            
            primary_matches = len([term for term in matched_terms if any(pk in term for pk in primary_keywords)])
            if primary_matches >= 2:
                score += primary_matches * 2
            
            # Reduced rating bonus
            rating = product.get('rating_rate', 0)
            if rating >= 4.5:
                score += 2  # Giảm từ 3
            elif rating >= 4.0:
                score += 1  # Giảm từ 2
            
            if score > 0:
                matching_products.append((product, score, matched_terms))
                logger.debug(f"📊 Product: {title[:30]}... - Score: {score} - Terms: {matched_terms}")
        
        # Sắp xếp theo điểm và trả về - INCREASED LIMIT
        matching_products.sort(key=lambda x: x[1], reverse=True)
        result = [product for product, score, terms in matching_products[:limit]]
        
        logger.info(f"✅ Tìm thấy {len(result)} sản phẩm phù hợp từ {len(matching_products)} candidates trong danh sách đã lọc")
        
        # DEBUG: In ra top matches
        for i, (product, score, terms) in enumerate(matching_products[:min(10, len(matching_products))]):
            logger.info(f"🏆 #{i+1}: {product.get('title', '')[:40]}... (Score: {score})")
        
        return result
        
        
    except Exception as e:
        logger.error(f"❌ Lỗi trong search_products_by_vietnamese_keywords_improved: {str(e)}")
        import traceback
        logger.error(f"❌ Traceback: {traceback.format_exc()}")
        return []

def get_fallback_products(user_profile: Dict, limit: int = 5) -> List[Dict]:
    """
    Lấy sản phẩm dự phòng dựa trên profile người dùng
    """
    try:
        from startup.initializer import products as current_products, products_by_gender
        
        if not current_products:
            logger.error("❌ current_products is empty for fallback")
            return []
            
        user_gender = user_profile.get('gender', '').lower()
        user_preferences = user_profile.get('preferences', [])
        
        fallback_products = []
        
        # Ưu tiên sản phẩm theo giới tính
        if user_gender in ['nam', 'male', 'men'] and products_by_gender and 'nam' in products_by_gender:
            fallback_products = list(products_by_gender['nam'])
        elif user_gender in ['nữ', 'female', 'women'] and products_by_gender and 'nữ' in products_by_gender:
            fallback_products = list(products_by_gender['nữ'])
        
        # Nếu không có sản phẩm theo giới tính, lấy ngẫu nhiên
        if not fallback_products:
            fallback_products = list(current_products)
        
        # Lọc theo sở thích nếu có
        if user_preferences and fallback_products:
            preference_products = []
            for product in fallback_products:
                product_text = f"{product.get('title', '')} {product.get('description', '')}".lower()
                for pref in user_preferences:
                    if pref.lower() in product_text:
                        preference_products.append(product)
                        break
            
            if preference_products:
                fallback_products = preference_products
        
        # Trộn ngẫu nhiên và lấy số lượng cần thiết
        if len(fallback_products) > limit:
            return random.sample(fallback_products, limit)
        
        return fallback_products[:limit]
        
    except Exception as e:
        logger.error(f"❌ Lỗi trong get_fallback_products: {str(e)}")
        return []

def ensure_products_loaded():
    """Đảm bảo products được load, nếu không thì load lại - FIXED VERSION"""
    try:
        logger.info("🔄 Kiểm tra và đảm bảo products được load...")
        
        # Import trực tiếp từ startup.initializer
        from startup.initializer import products as current_products
        
        # Kiểm tra products có dữ liệu không
        if not current_products or len(current_products) == 0:
            logger.warning("⚠️ products is empty, trying to reinitialize...")
            
            # Thử reinitialize hệ thống
            try:
                from startup import initializer
                if hasattr(initializer, 'initialize_system'):
                    success = initializer.initialize_system()
                    logger.info(f"🔄 Reinitialize result: {success}")
                    
                    # Import lại sau khi reinitialize
                    from startup.initializer import products as reloaded_products
                    if reloaded_products and len(reloaded_products) > 0:
                        logger.info(f"✅ Reloaded products: {len(reloaded_products)} items")
                        return True
                        
            except Exception as e:
                logger.error(f"❌ Error reinitializing: {e}")
                return False
        else:
            logger.info(f"✅ Products OK: {len(current_products)} items available")
            return True
            
        logger.error("❌ Products still empty after all attempts")
        return False
            
    except Exception as e:
        logger.error(f"❌ Error in ensure_products_loaded: {e}")
        import traceback
        logger.error(f"❌ Traceback: {traceback.format_exc()}")
        return False
    
def get_relevant_products_enhanced(message: str, user_profile: Dict, limit: int = 5) -> List[Dict]:
    """
    Tìm kiếm sản phẩm với nhiều phương pháp khác nhau - ENHANCED VERSION với lọc giới tính
    """
    try:
        logger.info(f"🔍 Bắt đầu tìm kiếm sản phẩm cho: '{message}'")
        
        # BƯỚC 0: Đảm bảo products được load
        if not ensure_products_loaded():
            logger.error("❌ Cannot load products, returning empty list")
            return []
        
        # Import fresh products sau khi ensure
        from startup.initializer import products as current_products, retriever
        
        if not current_products:
            logger.error("❌ current_products still empty after ensure")
            return []
        
        # BƯỚC 0.5: Lọc sản phẩm theo giới tính ngay từ đầu
        gender_filtered_products = get_gender_filtered_products(user_profile, current_products)
        logger.info(f"👥 Lọc theo giới tính: {len(gender_filtered_products)} sản phẩm từ {len(current_products)} sản phẩm gốc")
        
        # Tạo dict mapping ID -> product cho gender_filtered_products để lookup nhanh hơn
        gender_filtered_dict = {}
        for product in gender_filtered_products:
            if product and 'id' in product:
                gender_filtered_dict[product['id']] = product
        
        logger.info(f"🗂️ Created gender filter dict với {len(gender_filtered_dict)} products")
        logger.info(f"🔢 Available gender-filtered IDs: {list(gender_filtered_dict.keys())}")
        
        # Kiểm tra xem có phải là simple keyword không (để ưu tiên keyword search)
        simple_keywords = ['áo', 'quần', 'váy', 'đầm', 'giày', 'dép', 'túi', 'mũ', 'kính', 'đồng hồ', 'nhẫn']
        is_simple_keyword = any(keyword in message.lower() for keyword in simple_keywords)
        
        # BƯỚC 1: Nếu là simple keyword, thử keyword search trước
        if is_simple_keyword:
            logger.info("🎯 Phát hiện simple keyword, ưu tiên keyword search...")
            keyword_products = search_products_by_vietnamese_keywords(message, user_profile, gender_filtered_products, limit)
            
            if keyword_products and len(keyword_products) >= limit:
                logger.info(f"✅ Keyword search đủ kết quả: {len(keyword_products)} sản phẩm")
                return keyword_products
            elif keyword_products:
                logger.info(f"🔄 Keyword search có {len(keyword_products)} sản phẩm, sẽ combine với vector search...")
        
        # BƯỚC 2: Vector search (hoặc combine với keyword nếu cần)
        vector_products = []
        try:
            logger.info(f"🤖 Bắt đầu vector search cho: '{message}'")
            
            if retriever is not None:
                # Sử dụng invoke thay vì get_relevant_documents (deprecated)
                docs = retriever.invoke(message)
                logger.info(f"📄 Vector search trả về {len(docs)} documents")
                
                vector_products = []
                
                # Tăng số lượng docs để xử lý để có nhiều lựa chọn hơn
                # Lấy nhiều docs hơn để đảm bảo có đủ sau khi filter gender
                max_docs_to_process = min(len(docs), limit * 5)  # Tăng lên limit * 5
                for i, doc in enumerate(docs[:max_docs_to_process]):
                    product_id = doc.metadata.get("id")
                    
                    if product_id is not None:
                        logger.info(f"📋 Doc {i}: Tìm product ID = {product_id}")
                        
                        # Tìm trực tiếp trong dict đã lọc giới tính
                        if product_id in gender_filtered_dict:
                            found_product = gender_filtered_dict[product_id]
                            vector_products.append(found_product)
                            logger.info(f"✅ Added (gender filtered): {found_product.get('title', 'No title')}")
                        else:
                            # Kiểm tra xem product có tồn tại trong toàn bộ danh sách không
                            found_in_all = any(p.get('id') == product_id for p in current_products if p)
                            if found_in_all:
                                # Tìm product đó để log tên
                                original_product = next((p for p in current_products if p and p.get('id') == product_id), None)
                                product_title = original_product.get('title', 'Unknown') if original_product else 'Unknown'
                                logger.info(f"⚠️ Found '{product_title}' (ID={product_id}) but filtered out by gender")
                            else:
                                logger.warning(f"❌ Product ID {product_id} not found in any list")
                
                if vector_products:
                    # Nếu đã có keyword_products từ bước trước, combine chúng
                    if is_simple_keyword and 'keyword_products' in locals() and keyword_products:
                        logger.info(f"🔄 Combining keyword ({len(keyword_products)}) + vector ({len(vector_products)}) results...")
                        
                        # Tạo combined result, ưu tiên keyword search
                        combined_result = []
                        existing_ids = set()
                        
                        # Thêm keyword results trước
                        for product in keyword_products:
                            if product.get('id') not in existing_ids and len(combined_result) < limit:
                                combined_result.append(product)
                                existing_ids.add(product.get('id'))
                        
                        # Thêm vector results để đủ limit
                        for product in vector_products:
                            if product.get('id') not in existing_ids and len(combined_result) < limit:
                                combined_result.append(product)
                                existing_ids.add(product.get('id'))
                        
                        logger.info(f"🎯 Final combined result: {len(combined_result)} products")
                        return combined_result
                    
                    else:
                        result = vector_products[:limit]
                        logger.info(f"🎉 Vector search SUCCESS: {len(result)} gender-filtered products found!")
                        
                        # Nếu vector search có kết quả nhưng không đủ limit, combine với keyword search
                        if len(result) < limit:
                            logger.info(f"🔄 Vector search chỉ có {len(result)}/{limit} sản phẩm, combine với keyword search...")
                            
                            # Lấy IDs đã có từ vector search để tránh duplicate
                            existing_ids = {p.get('id') for p in result if p.get('id') is not None}
                            
                            # Tìm thêm bằng keyword search
                            remaining_limit = limit - len(result)
                            additional_keyword_products = search_products_by_vietnamese_keywords(
                                message, user_profile, gender_filtered_products, remaining_limit * 2
                            )
                            
                            # Thêm products từ keyword search (loại bỏ duplicate)
                            for product in additional_keyword_products:
                                if product.get('id') not in existing_ids and len(result) < limit:
                                    result.append(product)
                                    existing_ids.add(product.get('id'))
                            
                            logger.info(f"🎯 Combined result: {len(result)} products (vector + keyword)")
                        
                        return result
                else:
                    logger.warning(f"⚠️ Vector search found {len(docs)} docs but matched 0 gender-filtered products")
            else:
                logger.warning("⚠️ Retriever is None, skipping vector search")
                    
        except Exception as e:
            logger.error(f"❌ Vector search failed: {str(e)}")
            import traceback
            logger.error(f"❌ Vector search traceback: {traceback.format_exc()}")
        
        # BƯỚC 2: Tìm kiếm bằng từ khóa tiếng Việt (trong sản phẩm đã lọc giới tính)
        logger.info("🔄 Chuyển sang tìm kiếm bằng từ khóa tiếng Việt (gender-filtered)...")
        keyword_products = search_products_by_vietnamese_keywords(message, user_profile, gender_filtered_products, limit)
        
        if keyword_products:
            logger.info(f"✅ Từ khóa tiếng Việt tìm thấy {len(keyword_products)} sản phẩm (gender-filtered)")
            return keyword_products
        
        # BƯỚC 4: Tìm kiếm theo danh mục (trong sản phẩm đã lọc giới tính)
        logger.info("🔄 Tìm kiếm theo danh mục (gender-filtered)...")
        extracted_info = extract_product_from_message_improved(message)
        
        if extracted_info.get('category'):
            category_products = []
            
            for product in gender_filtered_products:
                if not product:
                    continue
                    
                product_text = f"{product.get('title', '')} {product.get('category', '')}".lower()
                
                if extracted_info['category'] in product_text:
                    category_products.append(product)
            
            if category_products:
                result = category_products[:limit]
                logger.info(f"✅ Tìm theo danh mục tìm thấy {len(result)} sản phẩm (gender-filtered)")
                return result
        
        # BƯỚC 5: Sử dụng get_fallback_products (đã có logic lọc giới tính sẵn)
        logger.info("🔄 Sử dụng fallback products với gender filtering...")
        fallback_products = get_fallback_products(user_profile, limit)
        
        if fallback_products:
            logger.info(f"✅ Fallback products: {len(fallback_products)} sản phẩm")
            return fallback_products
        
        # BƯỚC 6: Cuối cùng - trả về sản phẩm đã lọc giới tính
        if gender_filtered_products:
            emergency_products = gender_filtered_products[:limit]
            logger.info(f"🚨 Sử dụng gender-filtered emergency products: {len(emergency_products)} sản phẩm")
            return emergency_products
        
        # BƯỚC 7: Tuyệt đối cuối cùng - sản phẩm gốc
        emergency_products = current_products[:limit] if current_products else []
        logger.info(f"🚨 Sử dụng sản phẩm khẩn cấp không lọc: {len(emergency_products)} sản phẩm")
        return emergency_products
        
    except Exception as e:
        logger.error(f"❌ Lỗi nghiêm trọng: {str(e)}")
        import traceback
        logger.error(f"❌ Main function traceback: {traceback.format_exc()}")
        
        # Thử trả về dữ liệu từ fallback
        try:
            return get_fallback_products(user_profile, limit)
        except:
            return []

def get_gender_filtered_products(user_profile: Dict, all_products: List[Dict]) -> List[Dict]:
    """
    Lọc sản phẩm theo giới tính từ danh sách tất cả sản phẩm - IMPROVED VERSION với debug
    """
    try:
        if not all_products:
            logger.info("⚠️ all_products is empty")
            return []
        
        user_gender = user_profile.get('gender', '').lower()
        logger.info(f"👥 Lọc sản phẩm theo giới tính: {user_gender}")
        
        # Nếu không có thông tin giới tính, trả về toàn bộ
        if not user_gender:
            logger.info("⚠️ Không có thông tin giới tính, trả về toàn bộ sản phẩm")
            return all_products
        
        filtered_products = []
        
        # Log một vài products để debug
        logger.info(f"🔍 Đang lọc từ {len(all_products)} sản phẩm:")
        for i, product in enumerate(all_products[:3]):  # Log 3 sản phẩm đầu
            if product:
                logger.info(f"  Sample {i}: ID={product.get('id')}, Title='{product.get('title', 'No title')}'")
        
        # Lọc sản phẩm theo giới tính
        for product in all_products:
            if not product:
                continue
            
            if is_product_suitable_for_gender(product, user_gender):
                filtered_products.append(product)
                logger.debug(f"✅ Kept: {product.get('title', 'No title')} (ID: {product.get('id')})")
            else:
                logger.debug(f"❌ Filtered out: {product.get('title', 'No title')} (ID: {product.get('id')})")
        
        # Nếu không tìm thấy sản phẩm nào phù hợp với giới tính, trả về toàn bộ
        if not filtered_products:
            logger.warning(f"⚠️ Không tìm thấy sản phẩm nào cho giới tính {user_gender}, trả về toàn bộ")
            return all_products
        
        # Log kết quả
        logger.info(f"✅ Lọc thành công: {len(filtered_products)} sản phẩm từ {len(all_products)} sản phẩm gốc")
        logger.info(f"🔢 Filtered product IDs: {[p.get('id') for p in filtered_products[:5]]}...")  # Log 5 ID đầu
        
        return filtered_products
        
    except Exception as e:
        logger.error(f"❌ Lỗi trong get_gender_filtered_products: {str(e)}")
        import traceback
        logger.error(f"❌ Traceback: {traceback.format_exc()}")
        return all_products
    
def get_gender_filtered_products(user_profile: Dict, all_products: List[Dict]) -> List[Dict]:
    """
    Lọc sản phẩm theo giới tính từ danh sách tất cả sản phẩm - IMPROVED VERSION với debug
    """
    try:
        if not all_products:
            logger.info("⚠️ all_products is empty")
            return []
        
        user_gender = user_profile.get('gender', '').lower()
        logger.info(f"👥 Lọc sản phẩm theo giới tính: {user_gender}")
        
        # Nếu không có thông tin giới tính, trả về toàn bộ
        if not user_gender:
            logger.info("⚠️ Không có thông tin giới tính, trả về toàn bộ sản phẩm")
            return all_products
        
        filtered_products = []
        
        # Log một vài products để debug
        logger.info(f"🔍 Đang lọc từ {len(all_products)} sản phẩm:")
        for i, product in enumerate(all_products[:3]):  # Log 3 sản phẩm đầu
            if product:
                logger.info(f"  Sample {i}: ID={product.get('id')}, Title='{product.get('title', 'No title')}'")
        
        # Lọc sản phẩm theo giới tính
        for product in all_products:
            if not product:
                continue
            
            if is_product_suitable_for_gender(product, user_gender):
                filtered_products.append(product)
                logger.debug(f"✅ Kept: {product.get('title', 'No title')} (ID: {product.get('id')})")
            else:
                logger.debug(f"❌ Filtered out: {product.get('title', 'No title')} (ID: {product.get('id')})")
        
        # Nếu không tìm thấy sản phẩm nào phù hợp với giới tính, trả về toàn bộ
        if not filtered_products:
            logger.warning(f"⚠️ Không tìm thấy sản phẩm nào cho giới tính {user_gender}, trả về toàn bộ")
            return all_products
        
        # Log kết quả
        logger.info(f"✅ Lọc thành công: {len(filtered_products)} sản phẩm từ {len(all_products)} sản phẩm gốc")
        logger.info(f"🔢 Filtered product IDs: {[p.get('id') for p in filtered_products[:5]]}...")  # Log 5 ID đầu
        
        return filtered_products
        
    except Exception as e:
        logger.error(f"❌ Lỗi trong get_gender_filtered_products: {str(e)}")
        import traceback
        logger.error(f"❌ Traceback: {traceback.format_exc()}")
        return all_products
        
def is_product_suitable_for_gender(product: Dict, user_gender: str) -> bool:
    """
    Kiểm tra xem sản phẩm có phù hợp với giới tính người dùng không
    """
    if not user_gender:
        return True
    
    user_gender = user_gender.lower()
    product_text = f"{product.get('title', '')} {product.get('description', '')} {product.get('category', '')}".lower()
    
    # Kiểm tra giới tính nam
    if user_gender in ['nam', 'male', 'men']:
        # 1. Có từ khóa nam rõ ràng -> phù hợp
        if any(word in product_text for word in ['men', 'male', 'nam', 'boy', 'gentleman']):
            return True
        
        # 2. Có từ khóa nữ rõ ràng -> không phù hợp
        if any(word in product_text for word in ['women', 'female', 'nữ', 'girl', 'lady', 'woman']):
            return False
        
        # 3. Sản phẩm unisex/neutral -> phù hợp
        return True

    # Kiểm tra giới tính nữ
    elif user_gender in ['nữ', 'female', 'women', 'woman']:
        # 1. Có từ khóa nữ rõ ràng -> phù hợp
        if any(word in product_text for word in ['women', 'female', 'nữ', 'girl', 'lady', 'woman']):
            return True
        
        # 2. Trang sức (thường unisex nhưng thiên về nữ) -> phù hợp
        if any(keyword in product_text for keyword in ['trang sức', 'jewelry', 'jewelery', 'ring', 'necklace', 'bracelet', 'earring']):
            return True
        
        # 3. Có từ khóa nam rõ ràng -> không phù hợp
        if any(word in product_text for word in ['men', 'male', 'nam', 'boy', 'gentleman', 'man']):
            return False
        
        # 4. Sản phẩm unisex/neutral -> phù hợp
        return True
    
    return True
def get_gender_filtered_products(user_profile: Dict, all_products: List[Dict]) -> List[Dict]:
    """
    Lọc sản phẩm theo giới tính từ danh sách tất cả sản phẩm - IMPROVED VERSION với debug
    """
    try:
        if not all_products:
            logger.info("⚠️ all_products is empty")
            return []
        
        user_gender = user_profile.get('gender', '').lower()
        logger.info(f"👥 Lọc sản phẩm theo giới tính: {user_gender}")
        
        # Nếu không có thông tin giới tính, trả về toàn bộ
        if not user_gender:
            logger.info("⚠️ Không có thông tin giới tính, trả về toàn bộ sản phẩm")
            return all_products
        
        filtered_products = []
        
        # Log một vài products để debug
        logger.info(f"🔍 Đang lọc từ {len(all_products)} sản phẩm:")
        for i, product in enumerate(all_products[:3]):  # Log 3 sản phẩm đầu
            if product:
                logger.info(f"  Sample {i}: ID={product.get('id')}, Title='{product.get('title', 'No title')}'")
        
        # Lọc sản phẩm theo giới tính
        for product in all_products:
            if not product:
                continue
            
            if is_product_suitable_for_gender(product, user_gender):
                filtered_products.append(product)
                logger.debug(f"✅ Kept: {product.get('title', 'No title')} (ID: {product.get('id')})")
            else:
                logger.debug(f"❌ Filtered out: {product.get('title', 'No title')} (ID: {product.get('id')})")
        
        # Nếu không tìm thấy sản phẩm nào phù hợp với giới tính, trả về toàn bộ
        if not filtered_products:
            logger.warning(f"⚠️ Không tìm thấy sản phẩm nào cho giới tính {user_gender}, trả về toàn bộ")
            return all_products
        
        # Log kết quả
        logger.info(f"✅ Lọc thành công: {len(filtered_products)} sản phẩm từ {len(all_products)} sản phẩm gốc")
        logger.info(f"🔢 Filtered product IDs: {[p.get('id') for p in filtered_products[:5]]}...")  # Log 5 ID đầu
        
        return filtered_products
        
    except Exception as e:
        logger.error(f"❌ Lỗi trong get_gender_filtered_products: {str(e)}")
        import traceback
        logger.error(f"❌ Traceback: {traceback.format_exc()}")
        return all_products

def create_product_recommendation_text(products_list: List[Dict], user_name: str = "") -> str:
    """Tạo text gợi ý sản phẩm thân thiện và hấp dẫn"""
    if not products_list:
        return f"""Xin lỗi {user_name if user_name else 'bạn'}, hiện tại mình không tìm thấy sản phẩm chính xác như bạn yêu cầu. 😅
        
🔍 **Bạn có thể thử:**
• Mô tả cụ thể hơn sản phẩm bạn muốn tìm
• Nói rõ loại sản phẩm: áo, quần, giày, túi...
• Hoặc cho mình biết màu sắc, kích thước bạn thích

💡 Mình sẽ tư vấn những sản phẩm tuyệt vời nhất cho bạn! 🛍️"""

    greeting = f"Chào {user_name}! " if user_name else "Chào bạn! "
    
    if len(products_list) == 1:
        product = products_list[0]
        description = product.get('description', 'Sản phẩm chất lượng cao')
        short_desc = description[:80] + '...' if len(description) > 80 else description
        
        return f"""{greeting}Mình tìm thấy sản phẩm tuyệt vời này cho bạn:

🛍️ **{product.get('title', 'Sản phẩm')}**
💰 Giá: ${product.get('price', 0):.2f}
📱 Danh mục: {product.get('category', 'Thời trang')}
✨ {short_desc}

Sản phẩm này có vẻ phù hợp với bạn đấy! Bạn có muốn mua không? Nếu có thì mình sẽ hướng dẫn bạn đặt hàng ngay nhé! 😊🛒"""
    
    else:
        product_list_text = ""
        for i, product in enumerate(products_list, 1):
            title = product.get('title', 'Sản phẩm')
            price = product.get('price', 0)
            category = product.get('category', 'Thời trang')
            
            product_list_text += f"""{i}. 🔸 **{title}** - ${price:.2f}
   📱 {category}
   
"""
        
        return f"""{greeting}Mình tìm thấy những sản phẩm tuyệt vời này cho bạn:

{product_list_text}

✨ **Bạn thích sản phẩm nào?** Chỉ cần nói "mình muốn mua [tên sản phẩm]" là mình sẽ hỗ trợ bạn đặt hàng ngay! 

🛒 Hoặc bạn muốn xem thêm thông tin chi tiết về sản phẩm nào không? 😊"""

# Các hàm hỗ trợ khác (giữ nguyên từ code cũ)
def find_best_matching_product(extracted_info: Dict[str, Any], available_products: List[Dict]) -> Optional[Dict]:
    """Tìm sản phẩm phù hợp nhất dựa trên thông tin đã trích xuất"""
    if not available_products:
        return None
    
    scored_products = []
    
    for product in available_products:
        score = 0
        product_text = f"{product.get('title', '')} {product.get('description', '')} {product.get('category', '')}".lower()
        
        # Khớp danh mục (ưu tiên cao nhất)
        if extracted_info.get("category") and extracted_info["category"] in product.get('category', '').lower():
            score += 10
        
        # Khớp giới tính
        if extracted_info.get("gender") and extracted_info["gender"] == product.get('gender', 'khác'):
            score += 8
        
        # Khớp màu sắc
        if extracted_info.get("color") and extracted_info["color"] in product_text:
            score += 5
        
        # Khớp kích thước
        if extracted_info.get("size") and extracted_info["size"].lower() in product_text:
            score += 5
        
        # Khớp từ khóa
        for keyword in extracted_info.get("keywords", []):
            if keyword in product_text:
                score += 2
        
        if score > 0:
            scored_products.append((product, score))
    
    if not scored_products:
        return random.choice(available_products) if available_products else None
    
    # Sắp xếp theo điểm và trả về kết quả tốt nhất
    scored_products.sort(key=lambda x: x[1], reverse=True)
    return scored_products[0][0]

def find_product_id_by_name_improved(product_name: str) -> Optional[str]:
    """Tìm ID sản phẩm theo tên với logic tìm kiếm cải tiến"""
    try:
        from startup.initializer import products as current_products
        
        if not current_products or not product_name:
            return None
        
        product_name_lower = product_name.lower()
        
        # Khớp trực tiếp với tiêu đề
        for product in current_products:
            if product_name_lower in product.get('title', '').lower():
                return product.get('id')
        
        # Khớp danh mục + từ khóa
        for product in current_products:
            product_text = f"{product.get('title', '')} {product.get('description', '')} {product.get('category', '')}".lower()
            if any(word in product_text for word in product_name_lower.split() if len(word) > 2):
                return product.get('id')
    
        return None
    except ImportError as e:
        logger.error(f"❌ ImportError in find_product_id_by_name_improved: {e}")
        return None
    except Exception as e:
        logger.error(f"❌ Error in find_product_id_by_name_improved: {e}")
        return None

# Các hàm hỗ trợ để tương thích với code hiện có
def get_product_by_id(product_id: str) -> Optional[Dict]:
    from startup.initializer import products as current_products
    if not current_products:
        ensure_products_loaded()
        from startup.initializer import products as current_products  # reload
    return next((p for p in current_products if p.get('id') == product_id), None)

def search_products_by_keywords(keywords: List[str], limit: int = 10) -> List[Dict]:
    """Tìm kiếm sản phẩm theo nhiều từ khóa"""
    from startup.initializer import products
    if not keywords or not products:
        return []
    
    matching_products = []
    keywords_lower = [kw.lower() for kw in keywords]
    
    for product in products:
        product_text = f"{product.get('title', '')} {product.get('description', '')} {product.get('category', '')}".lower()
        
        # Tính điểm khớp
        score = sum(1 for kw in keywords_lower if kw in product_text)
        
        if score > 0:
            matching_products.append((product, score))
    
    # Sắp xếp theo điểm và trả về kết quả hàng đầu
    matching_products.sort(key=lambda x: x[1], reverse=True)
    return [product for product, score in matching_products[:limit]]

# def check_initializer_status():
#     """Kiểm tra trạng thái của startup.initializer"""
#     try:
        
#         logger.info("=== CHECKING INITIALIZER STATUS ===")
#         logger.info(f"✅ Import successful")
#         logger.info(f"📦 products: {type(products)} - Length: {len(products) if products else 'None'}")
#         logger.info(f"👥 products_by_gender: {type(products_by_gender)} - Keys: {list(products_by_gender.keys()) if products_by_gender else 'None'}")
#         logger.info(f"🔍 retriever: {type(retriever)} - Value: {retriever}")
#         logger.info(f"🚻 detect_gender: {type(detect_gender)} - Callable: {callable(detect_gender)}")
        
#         # Test retriever methods nếu có
#         if retriever:
#             logger.info(f"🔧 retriever methods: {dir(retriever)}")
#             if hasattr(retriever, 'vectorstore'):
#                 logger.info(f"🗃️ retriever.vectorstore: {retriever.vectorstore}")
        
#         return True
        
    # except ImportError as e:
    #     logger.error(f"❌ Import Error: {e}")
    #     return False
    # except Exception as e:
    #     logger.error(f"❌ Other Error: {e}")
    #     return False

# Hàm kiểm tra vector store hoạt động
def test_vector_search(test_query: str = "áo"):
    """Test vector search functionality"""
    logger.info(f"=== TESTING VECTOR SEARCH ===")
    
    try:
        from startup.initializer import retriever
        
        if not retriever:
            logger.error("❌ retriever is None or falsy")
            return False
        
        logger.info(f"🔍 Testing with query: '{test_query}'")
        docs = retriever.get_relevant_documents(test_query)
        logger.info(f"📄 Got {len(docs)} documents")
        
        for i, doc in enumerate(docs[:3]):
            logger.info(f"📋 Doc {i}: {doc.page_content[:100]}...")
            logger.info(f"📋 Metadata: {doc.metadata}")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Vector search test failed: {e}")
        import traceback
        logger.error(f"❌ Traceback:\n{traceback.format_exc()}")
        return False
    
def debug_gender_filtering_issue(user_profile: Dict, all_products: List[Dict]):
    """
    Debug function để kiểm tra vấn đề gender filtering
    """
    logger.info("🔍 === DEBUG GENDER FILTERING ISSUE ===")
    
    user_gender = user_profile.get('gender', '').lower()
    logger.info(f"👤 User gender: {user_gender}")
    
    logger.info(f"📦 Total products to filter: {len(all_products)}")
    
    # Kiểm tra từng sản phẩm
    for i, product in enumerate(all_products):
        if not product:
            continue
            
        title = product.get('title', '')
        product_text = f"{product.get('title', '')} {product.get('description', '')} {product.get('category', '')}".lower()
        
        # Kiểm tra logic cho nam
        if user_gender in ['nam', 'male', 'men']:
            has_male_keywords = any(word in product_text for word in ['men', 'male', 'nam', 'boy', 'gentleman'])
            has_female_keywords = any(word in product_text for word in ['women', 'female', 'nữ', 'girl', 'lady', 'woman'])
            
            logger.info(f"🔍 Product {i}: {title[:40]}...")
            logger.info(f"   - Has male keywords: {has_male_keywords}")
            logger.info(f"   - Has female keywords: {has_female_keywords}")
            
            if has_male_keywords:
                logger.info(f"   ✅ INCLUDE (explicit male)")
            elif not has_female_keywords:
                logger.info(f"   ✅ INCLUDE (unisex for male)")
            else:
                logger.info(f"   ❌ EXCLUDE (has female keywords)")
        
        if i >= 5:  # Chỉ debug 5 sản phẩm đầu
            break
    
    logger.info("🔍 === END DEBUG ===")
    
def test_product_filtering():
    """
    Test function để kiểm tra việc lọc sản phẩm
    """
    logger.info("=== TESTING PRODUCT FILTERING ===")
    
    # Test data giống như bạn cung cấp
    test_products = [
        {
            "id": 1,
            "title": "Ba lô Fjallraven - Foldsack No. 1, phù hợp với laptop 15 inch",
            "price": 109.95,
            "description": "Chiếc ba lô hoàn hảo cho việc sử dụng hàng ngày và đi dạo trong rừng. Được làm từ vải G-1000 HeavyDuty bền bỉ, có thể tùy chỉnh bằng sáp Greenland. Ngăn chính rộng rãi với dây rút và nắp gập, cùng với túi phía trước và dây đeo vai đệm.",
            "category": "quần áo nam",
            "image": "https://fakestoreapi.com/img/81fPKd-2AYL._AC_SL1500_.jpg",
            "rating_rate": 3.9,
            "rating_count": 120
        },
        {
            "id": 2,
            "title": "Áo thun nam tay ngắn",
            "price": 22.3,
            "description": "Áo thun nam cổ tròn, tay ngắn, chất liệu cotton mềm mại, thoáng mát, phù hợp cho các hoạt động hàng ngày.",
            "category": "quần áo nam",
            "image": "https://fakestoreapi.com/img/71-3HjGNDUL._AC_UL600_SR600,400_.jpg",
            "rating_rate": 4.1,
            "rating_count": 259
        },
        {
            "id": 3,
            "title": "Áo khoác nữ thời trang",
            "price": 55.99,
            "description": "Áo khoác nữ kiểu dáng hiện đại, chất liệu dày dặn, giữ ấm tốt, phù hợp cho mùa đông.",
            "category": "quần áo nữ",
            "image": "https://fakestoreapi.com/img/71li-ujtlUL._AC_UX679_.jpg",
            "rating_rate": 4.7,
            "rating_count": 500
        },
        {
            "id": 4,
            "title": "Vòng cổ vàng 18K",
            "price": 695.0,
            "description": "Vòng cổ làm từ vàng 18K, thiết kế tinh xảo, mang lại vẻ đẹp sang trọng và quý phái.",
            "category": "trang sức",
            "image": "https://fakestoreapi.com/img/71ya6v7xJIL._AC_UL600_SR600,400_.jpg",
            "rating_rate": 4.9,
            "rating_count": 400
        },
        {
            "id": 5,
            "title": "Đồng hồ nam dây da",
            "price": 125.0,
            "description": "Đồng hồ nam với dây da cao cấp, mặt kính chống xước, thiết kế lịch lãm, phù hợp cho doanh nhân.",
            "category": "trang sức",
            "image": "https://fakestoreapi.com/img/71Zy32Y5hIL._AC_UL600_SR600,400_.jpg",
            "rating_rate": 4.6,
            "rating_count": 340
        },
        {
            "id": 6,
            "title": "Áo khoác nữ mùa đông",
            "price": 59.99,
            "description": "Áo khoác nữ mùa đông, chất liệu dày dặn, giữ ấm tốt, thiết kế thời trang, phù hợp cho mùa lạnh.",
            "category": "quần áo nữ",
            "image": "https://fakestoreapi.com/img/71HblAHs5xL._AC_UY879_-2.jpg",
            "rating_rate": 4.5,
            "rating_count": 250
        },
        {
            "id": 7,
            "title": "Vòng tay bạc nữ",
            "price": 49.99,
            "description": "Vòng tay làm từ bạc cao cấp, thiết kế tinh tế, phù hợp làm quà tặng cho người thân yêu.",
            "category": "trang sức",
            "image": "https://fakestoreapi.com/img/71ya6v7xJIL._AC_UL600_SR600,400_.jpg",
            "rating_rate": 4.8,
            "rating_count": 180
        },
        {
            "id": 8,
            "title": "Áo sơ mi nam dài tay",
            "price": 39.99,
            "description": "Áo sơ mi nam dài tay, chất liệu cotton, thiết kế đơn giản, phù hợp cho công sở và dạo phố.",
            "category": "quần áo nam",
            "image": "https://fakestoreapi.com/img/71YXzeOuslL._AC_UY879_.jpg",
            "rating_rate": 4.2,
            "rating_count": 300
        },
        {
            "id": 9,
            "title": "Nhẫn bạc nữ đính đá",
            "price": 89.99,
            "description": "Nhẫn bạc nữ đính đá quý, thiết kế sang trọng, mang lại vẻ đẹp quý phái cho người đeo.",
            "category": "trang sức",
            "image": "https://fakestoreapi.com/img/71pWzhdJNwL._AC_UL600_SR600,400_.jpg",
            "rating_rate": 4.9,
            "rating_count": 220
        },
        {
            "id": 10,
            "title": "Áo khoác nam thể thao",
            "price": 69.99,
            "description": "Áo khoác nam thể thao, chất liệu nhẹ, thoáng khí, phù hợp cho các hoạt động ngoài trời.",
            "category": "quần áo nam",
            "image": "https://fakestoreapi.com/img/71HblAHs5xL._AC_UY879_-2.jpg",
            "rating_rate": 4.3,
            "rating_count": 275
        },
        {
            "id": 11,
            "title": "Dây chuyền bạc nữ",
            "price": 59.99,
            "description": "Dây chuyền bạc nữ, thiết kế đơn giản nhưng tinh tế, phù hợp với nhiều phong cách thời trang.",
            "category": "trang sức",
            "image": "https://fakestoreapi.com/img/71ya6v7xJIL._AC_UL600_SR600,400_.jpg",
            "rating_rate": 4.7,
            "rating_count": 190
        },
        {
            "id": 12,
            "title": "Áo thun nữ cổ tròn",
            "price": 29.99,
            "description": "Áo thun nữ cổ tròn, chất liệu cotton mềm mại, thoáng mát, phù hợp cho mùa hè.",
            "category": "quần áo nữ",
            "image": "https://fakestoreapi.com/img/71YXzeOuslL._AC_UY879_.jpg",
            "rating_rate": 4.4,
            "rating_count": 210
        },
        {
            "id": 13,
            "title": "Vòng cổ ngọc trai",
            "price": 99.99,
            "description": "Vòng cổ ngọc trai tự nhiên, thiết kế sang trọng, mang lại vẻ đẹp quý phái cho người đeo.",
            "category": "trang sức",
            "image": "https://fakestoreapi.com/img/71pWzhdJNwL._AC_UL600_SR600,400_.jpg",
            "rating_rate": 4.9,
            "rating_count": 160
        },
        {
            "id": 14,
            "title": "Áo sơ mi nữ tay dài",
            "price": 45.99,
            "description": "Áo sơ mi nữ tay dài, chất liệu vải mềm mại, thiết kế thanh lịch, phù hợp cho công sở.",
            "category": "quần áo nữ",
            "image": "https://fakestoreapi.com/img/71li-ujtlUL._AC_UX679_.jpg",
            "rating_rate": 4.5,
            "rating_count": 230
        },
        {
            "id": 15,
            "title": "Nhẫn vàng nam",
            "price": 129.99,
            "description": "Nhẫn vàng nam, thiết kế mạnh mẽ, thể hiện phong cách nam tính và đẳng cấp.",
            "category": "trang sức",
            "image": "https://fakestoreapi.com/img/71ya6v7xJIL._AC_UL600_SR600,400_.jpg",
            "rating_rate": 4.6,
            "rating_count": 150
        },
        {
            "id": 16,
            "title": "Áo khoác gió nam",
            "price": 79.99,
            "description": "Áo khoác gió nam, chất liệu chống thấm nước, thiết kế thể thao, phù hợp cho các hoạt động ngoài trời.",
            "category": "quần áo nam",
            "image": "https://fakestoreapi.com/img/71HblAHs5xL._AC_UY879_-2.jpg",
            "rating_rate": 4.3,
            "rating_count": 200
        },
        {
            "id": 17,
            "title": "Vòng tay da nam",
            "price": 34.99,
            "description": "Vòng tay da nam, thiết kế đơn giản nhưng cá tính, phù hợp với phong cách thời trang hiện đại.",
            "category": "trang sức",
            "image": "https://fakestoreapi.com/img/71HblAHs5xL._AC_UY879_-2.jpg",
            "rating_rate": 3.8,
            "rating_count": 679
        }
    ]
    
    # Test với user nam
    male_profile = {'gender': 'nam'}
    logger.info(f"🧑 Testing với user nam...")
    
    print("=== TESTING IMPROVED GENDER FILTERING ===")
    filtered = get_gender_filtered_products(male_profile, test_products)
    print(f"Filtered {len(filtered)} products for male user")
    
    # Test search
    print("=== TESTING IMPROVED KEYWORD SEARCH ===")
    results = search_products_by_vietnamese_keywords("áo", male_profile, filtered, limit=10)
    print(f"Found {len(results)} products for 'áo'")
    
    for i, product in enumerate(results):
        print(f"{i+1}. {product['title']}")
# Gọi hàm test (uncomment để chạy)
# test_result = test_product_filtering()
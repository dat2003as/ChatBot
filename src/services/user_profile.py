#services\user_profile.py
import re

from utils.helpers import extract_payment_method, format_phone_number, validate_vietnamese_phone

def improved_extract_user_info(message: str, user_profile: dict, context: str = None):
    """Cải thiện hàm extract_user_info để xử lý payment method"""
    
    original_result = extract_user_info(message, user_profile, context)
    
    # Nếu đang trong quá trình collect order info và chưa có payment method
    if (user_profile.get("collecting_order_info") and 
        user_profile.get("phone") and 
        user_profile.get("address") and 
        not user_profile.get("payment_method")):
        
        # Thử extract payment method
        payment_method = extract_payment_method(message)
        if payment_method:
            user_profile["payment_method"] = payment_method
            user_profile["payment_method_confirmed"] = True
            print(f"✅ Extracted payment method: {payment_method}")
            return True
    
    return original_result

def extract_user_info(message: str, user_profile: dict, current_question_context: str = None) -> bool:
    """Trích xuất thông tin từ câu trả lời của người dùng"""
    message_lower = message.lower().strip()
    info_extracted = False

    # Trích xuất tên
    if not user_profile.get("name"):
        name_patterns = [
            r"^tên\s+([A-Za-zÀ-ỹ\s]{2,30})$",
            r"tên (?:của )?tôi(?: là)? ([A-ZÀ-Ý][a-zà-ỹ]*(?:\s[A-ZÀ-Ý][a-zà-ỹ]*)*)",
            r"mình(?: tên)?(?: là)? ([A-ZÀ-Ý][a-zà-ỹ]*(?:\s[A-ZÀ-Ý][a-zà-ỹ]*)*)",
            r"(?:tôi|mình)(?: tên| gọi)?(?: là)? ([A-ZÀ-Ý][a-zà-ỹ]*(?:\s[A-ZÀ-Ý][a-zà-ỹ]*)*)",
            r"^([A-ZÀ-Ý][a-zà-ỹ]{1,15})(?:\s+[A-ZÀ-Ý][a-zà-ỹ]{1,15}){0,3}$"
        ]
        
        # Danh sách từ không phải tên (bao gồm cả các từ chào hỏi)
        sai_ten = {
            "xin", "chào", "tôi", "mình", "bot", "ai", "hi", "hello", 
            "em", "anh", "chị", "bác", "cô", "chú", "ạ", "ơi",
            "good", "morning", "evening", "night", "bye", "goodbye",
            "cảm", "ơn", "thank", "you", "please", "xin chào",
            "chào bạn", "hello there", "hey", "hế", "lô"
        }
        
        # Kiểm tra các câu chào hỏi phổ biến
        greeting_phrases = [
            "xin chào", "chào bạn", "hello", "hi", "chào em", "chào anh", 
            "chào chị", "good morning", "good evening", "hế lô", "hế nhô"
        ]
        
        # Nếu là câu chào thông thường, không trích xuất tên
        if any(phrase in message_lower for phrase in greeting_phrases):
            return False
        
        # Nếu câu có dấu chấm hỏi hoặc chấm than và chứa từ chào, có thể là câu hỏi
        if ("?" in message or "!" in message) and any(word in message_lower for word in ["chào", "xin", "hello", "hi"]):
            return False

        for pattern in name_patterns:
            match = re.search(pattern, message, re.IGNORECASE)
            if match:
                name = match.group(1).strip()
                name_lower = name.lower()
                name_words = name_lower.split()
                
                # Kiểm tra nếu tên chứa từ không hợp lệ
                if any(word in sai_ten for word in name_words):
                    continue
                    
                if (
                    len(name.split()) <= 3 and
                    len(name) <= 30 and
                    len(name) >= 2 and  # Tên phải có ít nhất 2 ký tự
                    name_lower not in sai_ten
                ):
                    user_profile["name"] = name.title()
                    info_extracted = True
                    break

        # Nếu user chỉ nhập 1 từ, kiểm tra điều kiện nghiêm ngặt hơn
        if not info_extracted and len(message.split()) == 1:
            word = message.strip()
            word_lower = word.lower()
            
            if (
                word_lower not in sai_ten and
                2 <= len(word) <= 20 and
                word[0].isalpha() and
                word.isalpha()  # Chỉ chứa chữ cái
            ):
                user_profile["name"] = word.title()
                info_extracted = True

    # Trích xuất tuổi - XỬ LÝ TRƯỚC NGÂN SÁCH
    if not user_profile.get("age"):
        age_patterns = [
            r"(?:tôi|mình) (?:năm nay )?(\d{1,2}) tuổi",
            r"(\d{1,2}) tuổi",
            r"tuổi (?:của )?(?:tôi|mình) (?:là )?(\d{1,2})"
        ]

        # Kiểm tra các pattern có ngữ cảnh trước
        for pattern in age_patterns:
            match = re.search(pattern, message, re.IGNORECASE)
            if match:
                age = int(match.group(1))
                if 10 <= age <= 100:
                    user_profile["age"] = age
                    info_extracted = True
                    break

        if not info_extracted and re.match(r"^\d{1,2}$", message.strip()):
            try:
                age = int(message.strip())
              
                money_context = ["giá", "tiền", "chi", "mua", "budget", "ngân sách", "$", "đồng", "vnd"]
                has_money_context = any(word in message_lower for word in money_context)

                if ((current_question_context == "age") or 
                    (10 <= age <= 90 and not has_money_context)):
                    user_profile["age"] = age
                    info_extracted = True
            except ValueError:
                pass

    # Trích xuất giới tính
    if not user_profile.get("gender"):
        if any(word in message_lower for word in ["nam", "trai", "boy", "male"]):
            user_profile["gender"] = "Nam"
            info_extracted = True
        elif any(word in message_lower for word in ["nữ", "gái", "girl", "female"]):
            user_profile["gender"] = "Nữ"
            info_extracted = True

    # Trích xuất sở thích
    if not user_profile.get("preferences"):
        preference_keywords = {
            "thời trang": ["thời trang", "quần áo", "áo", "phong cách"],
            "trang sức": ["trang sức", "nhẫn", "dây chuyền", "vòng tay", "jewelry"],
            "thể thao": ["thể thao", "gym", "chạy bộ", "tập luyện"],
            "công sở": ["công sở", "làm việc", "chuyên nghiệp", "lịch sự"],
            "dạo phố": ["dạo phố", "đi chơi", "casual", "thoải mái"]
        }

        detected_preferences = []
        for category, keywords in preference_keywords.items():
            if any(keyword in message_lower for keyword in keywords):
                detected_preferences.append(category)
        
        if detected_preferences:
            user_profile["preferences"] = detected_preferences
            info_extracted = True

    # Trích xuất ngân sách - XỬ LÝ SAU TUỔI VÀ CÓ ĐIỀU KIỆN NGHIÊM NGẶT HƠN
    if not user_profile.get("budget_range") and not info_extracted:
        budget_patterns = [
            r"ngân sách.*?(\d+(?:[.,]\d+)?)\s*(?:k|nghìn|triệu|tr|đ|$|usd|vnd)",
            r"khoảng\s+(\d+(?:[.,]\d+)?)\s*(?:k|nghìn|triệu|tr|đ|$|usd|vnd)",
            r"(?:từ\s+)?(\d+(?:[.,]\d+)?)\s*(?:k|nghìn|triệu|tr|đ|$|usd|vnd)",
            r"dưới\s+(\d+(?:[.,]\d+)?)\s*(?:k|nghìn|triệu|tr|đ|$|usd|vnd)",
            r"(\d+(?:[.,]\d+)?)\s*(k|nghìn|triệu|tr|đ|$|usd|vnd)"
        ]

        for pattern in budget_patterns:
            match = re.search(pattern, message_lower)
            if match:
                amount = match.group(1).replace(',', '.')
                try:
                    budget_num = float(amount)
                    if budget_num > 0:
                        # Xác định đơn vị
                        unit_match = re.search(r"(\d+(?:[.,]\d+)?)\s*(k|nghìn|triệu|tr|đ|$|usd|vnd)", message_lower)
                        if unit_match and unit_match.group(2):
                            unit = unit_match.group(2).lower()
                            if unit in ['k', 'nghìn']:
                                budget_display = f"${budget_num:.0f}K"
                            elif unit in ['triệu', 'tr']:
                                budget_display = f"${budget_num:.0f}M"
                            else:
                                budget_display = f"${budget_num:.0f}"
                        else:
                            budget_display = f"${budget_num:.0f}"
                        
                        user_profile["budget_range"] = budget_display
                        info_extracted = True
                        break
                except ValueError:
                    continue
        
        # Xử lý số thuần túy cho ngân sách - ĐIỀU KIỆN NGHIÊM NGẶT HƠN
        if not info_extracted and re.match(r"^\d+$", message.strip()):
            # Các từ khóa ngữ cảnh về tiền
            money_context = ["giá", "tiền", "chi", "mua", "budget", "ngân sách", "$", "đồng", "vnd","k"]
            has_money_context = any(word in message_lower for word in money_context)
            
            try:
                number = float(message.strip())
                is_budget_context = (current_question_context == "budget")
                is_large_number_with_money_context = (has_money_context and number >= 100)
                is_not_typical_age = not (10 <= number <= 80)
                
                if (is_budget_context or 
                    (is_large_number_with_money_context and is_not_typical_age)):
                    user_profile["budget_range"] = f"${number:.0f}"
                    info_extracted = True
            except ValueError:
                pass

    # Trích xuất số điện thoại
    if not user_profile.get("phone"):
        # Improved phone patterns for Vietnamese numbers
        phone_patterns = [
            r"(?:số điện thoại|sđt|phone|số|dt)\s*(?:của\s+(?:tôi|mình)\s*)?(?:là\s*)?(?::\s*)?((?:0|\+84)[0-9]{8,9})",
            
            r"(?:^|\s)((?:0[0-9]{9}|\+84[0-9]{9}))(?:\s|$|[^\d])",
            
            r"(?:liên hệ|gọi)\s*(?:cho\s*(?:tôi|mình)\s*)?(?:theo\s*số\s*)?((?:0|\+84)[0-9]{8,9})",
            
            r"^((?:0[0-9]{9}|\+84[0-9]{9}))$"
        ]
        
        for i, pattern in enumerate(phone_patterns):
            match = re.search(pattern, message, re.IGNORECASE)
            if match:
                phone = match.group(1).strip()
                
                if validate_vietnamese_phone(phone):
                    user_profile["phone"] = format_phone_number(phone)
                    info_extracted = True
                    print(f"✅ Phone extracted with pattern {i+1}: {phone}")
                    break
                else:
                    print(f"❌ Invalid phone format: {phone}")
        
        # Special handling when context is asking for phone
        if not info_extracted and current_question_context == "phone":
            # Try to extract any sequence that looks like a phone number
            potential_phone = re.search(r'((?:0|\+84)[0-9]{8,10})', message)
            if potential_phone:
                phone = potential_phone.group(1)
                if validate_vietnamese_phone(phone):
                    user_profile["phone"] = format_phone_number(phone)
                    info_extracted = True
                    print(f"✅ Phone extracted in phone context: {phone}")

    # Trích xuất địa chỉ
    if not user_profile.get("address"):
        # Các pattern để nhận diện địa chỉ
        address_patterns = [
            r"địa chỉ\s+(?:của\s+tôi\s+)?(?:là\s+)?(.+)",
            r"tôi ở\s+(.+)",
            r"nhà tôi ở\s+(.+)",
            r"giao hàng\s+(?:đến\s+)?(.+)",
            r"(?:số\s+)?(\d+\s+[^0-9].+(?:quận|huyện|thành phố|tỉnh|phường|xã).+)",
        ]
        
        for pattern in address_patterns:
            match = re.search(pattern, message, re.IGNORECASE)
            if match:
                address = match.group(1).strip()
                # Kiểm tra địa chỉ có ý nghĩa (không phải các từ ngắn vô nghĩa)
                if len(address) >= 10 and not address.lower().startswith(('tôi muốn', 'mua', 'bán')):
                    user_profile["address"] = address
                    info_extracted = True
                    break
    # Trích xuất phương thức thanh toán
    if (not user_profile.get("payment_method") or not user_profile.get("payment_method_confirmed")):
        # CHỈ extract khi:
        # 1. Đang trong quá trình collect order info
        # 2. HOẶC current_question_context là "payment"  
        # 3. HOẶC message có chứa từ khóa payment rõ ràng
        should_extract_payment = (
            user_profile.get("collecting_order_info") or
            current_question_context == "payment" or
            any(keyword in message_lower for keyword in ["cod", "chuyển khoản", "thẻ", "momo", "zalopay"])
        )
        
        if should_extract_payment:
            from utils.helpers import extract_payment_method
            
            payment_method = extract_payment_method(message, user_profile, context="payment")
            if payment_method:
                info_extracted = True
                print(f"✅ Payment method set to: {payment_method}")
    

    # Cập nhật trạng thái hoàn thành
    required_fields = ["name", "age", "gender", "preferences", "budget_range"]
    if all(user_profile.get(field) for field in required_fields):
        user_profile["is_complete"] = True
    
    return info_extracted

def get_current_question_context(user_profile):
    """Xác định ngữ cảnh câu hỏi hiện tại đang hỏi gì"""
    if not user_profile.get("name"):
        return "name"
    elif not user_profile.get("age"):
        return "age"
    elif not user_profile.get("gender"):
        return "gender"
    elif not user_profile.get("preferences"):
        return "preferences"
    elif not user_profile.get("budget_range"):
        return "budget"
    elif not user_profile.get("phone"):
        return "phone"
    elif not user_profile.get("address"):
        return "address"
    return "complete"

def get_user_info_string(user_profile):
    """Tạo chuỗi thông tin user"""
    info = []
    if user_profile.get("name"):
        info.append(f"Tên: {user_profile['name']}")
    if user_profile.get("age"):
        info.append(f"Tuổi: {user_profile['age']}")
    if user_profile.get("gender"):
        info.append(f"Giới tính: {user_profile['gender']}")
    if user_profile.get("preferences"):
        info.append(f"Sở thích: {', '.join(user_profile['preferences'])}")
    if user_profile.get("budget_range"):
        info.append(f"Ngân sách: {user_profile['budget_range']}")
    return " | ".join(info) if info else "Chưa có thông tin"

def get_next_question(user_profile):
    """Xác định câu hỏi tiếp theo cần hỏi với phản hồi thông minh"""
    
    # Lấy số lần hội thoại để biết đã hỏi bao nhiêu lần
    conversation_count = user_profile.get("conversation_count", 0)
    
    if not user_profile.get("name"):
        if conversation_count <= 1:
            # Lần đầu tiên
            return "Chào bạn! Tôi là trợ lý mua sắm thông minh. Để tôi có thể tư vấn tốt hơn, bạn có thể cho tôi biết tên của bạn không? 😊"
        else:
            # Đã hỏi rồi nhưng chưa có tên
            return "Mình chưa biết tên bạn ạ. Bạn có thể chia sẻ tên để cuộc trò chuyện thân thiện hơn không? 😊"

    if not user_profile.get("age"):
        if not user_profile.get("age_asked"):
            # Lần đầu hỏi tuổi
            user_profile["age_asked"] = True
            return f"Rất vui được gặp {user_profile['name']}! Bạn bao nhiêu tuổi rồi? 🎂"
        else:
            # Đã hỏi rồi nhưng chưa có tuổi hợp lệ
            return f"Mình chưa rõ tuổi của {user_profile['name']} ạ. Bạn có thể cho biết tuổi để mình gợi ý sản phẩm phù hợp không? 🎂"

    if not user_profile.get("gender"):
        if not user_profile.get("gender_asked"):
            # Lần đầu hỏi giới tính
            user_profile["gender_asked"] = True
            return f"Cảm ơn {user_profile['name']}! Bạn là nam hay nữ ạ? Điều này giúp tôi gợi ý sản phẩm phù hợp hơn. 👫"
        else:
            # Đã hỏi rồi nhưng chưa hiểu giới tính
            return f"Mình chưa rõ giới tính của {user_profile['name']} ạ. Bạn có thể cho biết bạn là nam hay nữ để mình tư vấn chính xác hơn không? 👫"

    if not user_profile.get("preferences"):
        if not user_profile.get("preferences_asked"):
            # Lần đầu hỏi sở thích
            user_profile["preferences_asked"] = True
            return f"Tuyệt vời! {user_profile['name']} thích mua sắm loại sản phẩm nào? (Ví dụ: thời trang, trang sức, đồ thể thao, điện tử...) 🛍️"
        else:
            # Đã hỏi rồi nhưng chưa hiểu sở thích
            return f"""Mình chưa hiểu rõ sở thích mua sắm của {user_profile['name']} ạ. 
Bạn có thể chia sẻ những loại sản phẩm mà bạn quan tâm không? 

Ví dụ: 
🎽 Thời trang (quần áo, giày dép...)
💎 Trang sức & phụ kiện  
🏃 Đồ thể thao
📱 Công nghệ & điện tử
🏡 Đồ gia dụng
✨ Mỹ phẩm & làm đẹp"""

    if not user_profile.get("budget_range"):
        if not user_profile.get("budget_asked"):
            # Lần đầu hỏi ngân sách
            user_profile["budget_asked"] = True
            return f"Cuối cùng, {user_profile['name']} thường có ngân sách mua sắm trong khoảng bao nhiêu? (Ví dụ: dưới $50, từ $50-100, trên $200...) 💰"
        else:
            # Đã hỏi rồi nhưng chưa hiểu ngân sách
            return f"""Mình chưa rõ ngân sách mua sắm của {user_profile['name']} ạ. 
Bạn có thể cho biết khoảng chi tiêu mà bạn thoải mái không?

💵 Ví dụ:
• Dưới $50 (tiết kiệm)
• $50 - $100 (trung bình) 
• $100 - $200 (thoải mái)
• Trên $200 (cao cấp)

Hoặc bạn có thể nói theo cách khác cũng được ạ! 😊"""

    # Hoàn thành thu thập thông tin cơ bản
    user_profile["is_complete"] = True
    preferences_text = ", ".join(user_profile.get("preferences", [])) if user_profile.get("preferences") else "đa dạng"
    
    return f"""🎉 Hoàn tất! Cảm ơn {user_profile['name']} đã chia sẻ thông tin!

📋 **Hồ sơ của bạn:**
👤 Tên: {user_profile['name']}
🎂 Tuổi: {user_profile['age']}
👫 Giới tính: {user_profile['gender']} 
❤️ Sở thích: {preferences_text}
💰 Ngân sách: {user_profile['budget_range']}

Tuyệt vời! Giờ mình đã hiểu rõ về {user_profile['name']} rồi. Bạn muốn tìm kiếm sản phẩm gì hôm nay? Mình sẽ gợi ý những món đồ phù hợp nhất! 🛒✨"""
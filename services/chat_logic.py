# services/chat_logic.py
import logging
logger = logging.getLogger(__name__)
from services.create_images import create_image_gallery_html, detect_image_request, extract_product_name_from_image_request, get_product_images, handle_image_request_with_display
from services.user_profile import (
    extract_user_info, get_current_question_context,
    get_next_question
)
from services.order import (
    create_order_with_better_product_handling_v2,
    get_payment_method_display
)
from services.product_utils import (
    extract_product_from_message_improved,
    get_relevant_products_enhanced, 
    create_product_recommendation_text
)
from db.database import (
    get_or_create_session,
    get_user_session,
    save_chat_session_to_db, db_manager,
    save_user_profile_to_db
)
from utils.helpers import check_purchase_intent_natural

# Import vector store từ initializer
from services import globals
from datetime import datetime   
from langchain.memory import ConversationBufferMemory
from langchain_google_genai import GoogleGenerativeAI
import json
import os
import random
# Lấy API key từ environment variable thay vì hardcode
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
def process_chat_message(message: str, session_id: str):
    """hàm xử lý chat với khách hàng - CẢI THIỆN XỬ LÝ HÌNH ẢNH"""
    
    session_id, session_data = get_or_create_session(session_id)
    user_profile = session_data["profile"]
    memory = session_data["memory"]

    user_profile["conversation_count"] = user_profile.get("conversation_count", 0) + 1
    
    # KIỂM TRA YÊU CẦU XEM HÌNH ẢNH - CẢI THIỆN
    if detect_image_request(message):
        print(f"🖼️ Enhanced image request detected: '{message}'")
        
        try:
            response_text, images, html_content = handle_image_request_with_display(message, user_profile)
            
            print(f"📊 Enhanced image request result:")
            print(f"  - Response length: {len(response_text)}")
            print(f"  - Images found: {len(images)}")
            for i, img in enumerate(images):
                print(f"    {i+1}. {img.get('product_name')} - {img.get('image_url')}")
            
            # Lưu vào memory
            memory.save_context({"question": message}, {"answer": response_text})
            product_name = extract_product_name_from_image_request(message)
            if not product_name and images:
                product_name = images[0].get('product_name', 'sản phẩm')   

            return {
                "response": response_text,
                "session_id": session_id,
                "user_profile": user_profile,
                "is_profile_complete": user_profile.get("is_complete", False),
                "images": images,  
                "has_images": len(images) > 0, 
                "response_type": "image_request",  
                "image_count": len(images),  
                "original_message": message,
                "detection_method": "enhanced",
                "html_content": html_content,  
                "image_gallery": html_content, 
                "display_mode": "gallery" if len(images) > 1 else "single",
                "order_status": None
            }
            
        except Exception as e:
            print(f"❌ Error processing enhanced image request: {str(e)}")
            import traceback
            traceback.print_exc()
            
            error_response = f"""🔧 Xin lỗi, hệ thống gặp sự cố khi tải hình ảnh.

Lỗi: {str(e)}

Bạn có thể thử lại bằng cách:
• Mô tả rõ hơn sản phẩm cần xem
• Sử dụng từ khóa đơn giản hơn
• Liên hệ hỗ trợ nếu vấn đề tiếp diễn

Mình sẽ cố gắng khắc phục ngay! 😊"""
            
            return {
                "response": error_response,
                "session_id": session_id,
                "user_profile": user_profile,
                "is_profile_complete": user_profile.get("is_complete", False),
                "images": [],
                "has_images": False,
                "response_type": "error",
                "error": str(e),
                "order_status": None
            }

    # PHASE 1: Thu thập thông tin cơ bản
    if not user_profile.get("is_complete", False):
        current_context = get_current_question_context(user_profile)
        info_extracted = extract_user_info(message, user_profile, current_context)
        response = get_next_question(user_profile)

        if info_extracted:
            save_user_profile_to_db(session_id, user_profile)

        memory.save_context({"question": message}, {"answer": response})
        chat_history = json.dumps([msg.content for msg in memory.chat_memory.messages])
        save_chat_session_to_db(session_id, session_id, chat_history)

        return {
            "response": response,
            "session_id": session_id,
            "user_profile": user_profile,
            "is_profile_complete": user_profile.get("is_complete", False),
            "images": [],
            "has_images": False,
            "response_type": "profile_collection"
        }

    # PHASE 2: Kiểm tra ý định mua hàng
    purchase_intent = check_purchase_intent_natural(message)
    if purchase_intent and not user_profile.get("collecting_order_info"):
        user_profile["collecting_order_info"] = True
        user_profile["selected_product"] = extract_product_from_message_improved(message)

    if user_profile.get("collecting_order_info", False) or purchase_intent:
        # Lưu trạng thái thông tin trước khi xử lý
        previous_phone = user_profile.get("phone")
        previous_address = user_profile.get("address")
        previous_payment = user_profile.get("payment_method")
        
        # Extract thông tin từ tin nhắn hiện tại
        info_extracted = extract_user_info(message, user_profile, "purchase")

        if info_extracted:
            save_user_profile_to_db(session_id, user_profile)

        # Kiểm tra điều kiện theo thứ tự ưu tiên với phản hồi thông minh
        if not user_profile.get("phone"):
            # Trường hợp 1: Chưa có số điện thoại
            if previous_phone is None:
                # Lần đầu hỏi
                response = f"Tuyệt! {user_profile.get('name', 'bạn')} ơi, bạn cho mình xin số điện thoại để giao hàng nhé! ☎️"
            else:
                # Đã hỏi rồi nhưng thông tin không hợp lệ
                response = "Số điện thoại bạn vừa nhập có vẻ chưa đúng định dạng ạ. Bạn vui lòng nhập lại số điện thoại giúp mình nhé! 😊"
        
        elif not user_profile.get("address"):
            # Trường hợp 2: Chưa có địa chỉ
            if previous_address is None:
                # Lần đầu hỏi
                response = f"Ok! Bây giờ cho mình biết địa chỉ nhận hàng nhé 🏠 (Ví dụ: 123 Nguyễn Văn A, Phường 1, Quận 1, TP.HCM)"
            else:
                # Đã hỏi rồi nhưng thông tin không hợp lệ
                response = "Địa chỉ bạn vừa nhập có vẻ chưa đầy đủ ạ. Bạn có thể nhập lại địa chỉ chi tiết hơn được không? 🏠"
        
        elif not user_profile.get("payment_method_confirmed"):
            # Trường hợp 3: Chưa có phương thức thanh toán
            payment_method = user_profile.get("payment_method")
            if payment_method:
                # Vừa extract được payment method, confirm và chuyển sang tạo đơn hàng
                user_profile["payment_method_confirmed"] = True
                response = None  # Sẽ xử lý ở phần tạo đơn hàng bên dưới
                print(f"✅ Payment method confirmed: {payment_method}")
            else:
                # Chưa có payment method
                if previous_payment is None:
                    # Lần đầu hỏi
                    response = f"""Bạn muốn thanh toán bằng hình thức nào ạ?
1. COD (thanh toán khi nhận hàng)
2. Chuyển khoản ngân hàng  
3. Thẻ tín dụng / ghi nợ
4. Ví điện tử (Momo, ZaloPay...)

Bạn chỉ cần gõ số thứ tự hoặc tên phương thức nhé! 😊"""
                else:
                    # Đã hỏi rồi nhưng chưa hiểu
                    response = """Mình chưa hiểu rõ phương thức thanh toán bạn muốn chọn ạ. Bạn có thể chọn một trong các cách sau:

1️⃣ COD (thanh toán khi nhận hàng)
2️⃣ Chuyển khoản 
3️⃣ Thẻ tín dụng
4️⃣ Ví điện tử

Bạn gõ số hoặc tên phương thức giúp mình nhé! 🙏"""
        
        else:
            response = None 
        
        # Xử lý tạo đơn hàng khi đã có đủ thông tin
        if response is None:
            user_profile["collecting_order_info"] = False
            try:
                session_data_for_order = {
                    'session_id': session_id,
                    'profile': user_profile,
                    'memory': memory,
                    'cart': session_data.get('cart', [])
                }
                
                order_id, total_amount, product_details = create_order_with_better_product_handling_v2(
                    session_data_for_order, user_profile,
                )

                if order_id == "ERROR":
                    response = "❌ Đã có lỗi khi tạo đơn hàng. Vui lòng thử lại sau hoặc liên hệ hỗ trợ ạ."
                else:
                    product_text = "\n".join([f"🔹 {p['title']} - ${p['price']:.2f}" for p in product_details])
                    payment_method = get_payment_method_display(user_profile.get("payment_method"))

                    response = f"""🎉 Đơn hàng đã được tạo thành công!

📋 Mã đơn: {order_id}
{product_text}
💰 Tổng tiền: ${total_amount:.2f}
🏠 Địa chỉ giao: {user_profile.get('address')}
📞 SĐT: {user_profile.get('phone')}
💳 Thanh toán: {payment_method}

Cảm ơn {user_profile.get('name', 'bạn')} rất nhiều! Đơn hàng sẽ được xử lý trong thời gian sớm nhất. 
Bạn có muốn xem thêm sản phẩm nào khác không? 😊✨"""
            except Exception as e:
                print(f"❌ Unexpected error in order creation: {str(e)}")
                response = f"❌ Đã có lỗi không mong muốn khi tạo đơn hàng. Vui lòng liên hệ bộ phận hỗ trợ để được trợ giúp ạ."

        memory.save_context({"question": message}, {"answer": response})
        chat_history = json.dumps([msg.content for msg in memory.chat_memory.messages])
        save_chat_session_to_db(session_id, session_id, chat_history)

        return {
            "response": response,
            "session_id": session_id,
            "user_profile": user_profile,
            "is_profile_complete": True,
            "images": [],
            "has_images": False,
            "response_type": "order_processing"
        }

    # PHASE 3: Gợi ý sản phẩm (nếu user không yêu cầu gì đặc biệt) - CẢI THIỆN HIỂN THỊ HÌNH ẢNH
    try:
        print(f"🔍 Getting product recommendations for: '{message}'")
        recommended_products = get_relevant_products_enhanced(message, user_profile, limit=5)
        product_response = create_product_recommendation_text(recommended_products)
        
        # CẢI THIỆN: Tạo danh sách hình ảnh từ sản phẩm được gợi ý
        product_images = []
        for i, product in enumerate(recommended_products[:3]):  # Chỉ lấy 3 sản phẩm đầu
            # Kiểm tra nhiều trường có thể chứa image URL
            image_url = (
                product.get('image_url') or 
                product.get('image') or 
                product.get('thumbnail_url') or
                product.get('picture_url')
            )
            
            if image_url:
                product_images.append({
                    'product_id': product.get('id'),
                    'product_name': product.get('title', f'Product {i+1}'),
                    'image_url': image_url,
                    'price': product.get('price', 0),
                    'alt_text': product.get('title', f'Product {i+1}'),
                    'description': product.get('description', ''),
                    'thumbnail_url': product.get('thumbnail_url', image_url),
                    'similarity_score': product.get('similarity_score', 0)
                })
                print(f"🖼️ Added product image: {product.get('title')} - {image_url}")
            else:
                print(f"⚠️ No image for product: {product.get('title')}")
        
        print(f"📊 Product recommendation result: {len(recommended_products)} products, {len(product_images)} images")
        
    except Exception as e:
        print(f"❌ Error getting product recommendations: {str(e)}")
        import traceback
        traceback.print_exc()
        
        product_response = """Xin lỗi, hiện tại hệ thống đang gặp một chút sự cố khi tải sản phẩm. 

🔧 Bạn có thể thử:
• Hỏi cụ thể hơn: "Tôi cần áo khoác gió nam"
• Hoặc: "Cho xem hình laptop gaming"
• Hoặc: "Có những sản phẩm gì hot?"

Mình sẽ hỗ trợ bạn ngay! 😊"""
        product_images = []

    memory.save_context({"question": message}, {"answer": product_response})
    chat_history = json.dumps([msg.content for msg in memory.chat_memory.messages])
    save_chat_session_to_db(session_id, session_id, chat_history)

    return {
        "response": product_response,
        "session_id": session_id,
        "user_profile": user_profile,
        "is_profile_complete": user_profile.get("is_complete", False),
        "images": product_images,  # ← Đảm bảo trả về hình ảnh
        "has_images": len(product_images) > 0,
        "response_type": "product_recommendation",
        "recommendation_count": len(product_images),  # Thêm debug info
        "total_products_found": len(recommended_products) if 'recommended_products' in locals() else 0
    }


def handle_webhook_integration(webhook_data: dict) -> dict:
    """Xử lý webhook từ các hệ thống bên ngoài"""
    try:
        webhook_type = webhook_data.get("type")
        session_id = webhook_data.get("session_id")
        
        if webhook_type == "order_status_update":
            # Cập nhật trạng thái đơn hàng
            order_id = webhook_data.get("order_id")
            new_status = webhook_data.get("status")
            
            # Update order status in session
            session_data = get_user_session(session_id)
            orders = session_data.get("orders", [])
            
            for order in orders:
                if order.get("order_id") == order_id:
                    order["status"] = new_status
                    order["updated_at"] = datetime.now().isoformat()
                    break
            
            return {"success": True, "message": "Order status updated"}
            
        elif webhook_type == "payment_confirmation":
            # Xác nhận thanh toán
            return {"success": True, "message": "Payment confirmed"}
        
        else:
            return {"success": False, "message": "Unknown webhook type"}
            
    except Exception as e:
        logger.error(f"❌ Error handling webhook: {str(e)}")
        return {"success": False, "error": str(e)}

def cleanup_and_optimize() -> dict:
    """Dọn dẹp và tối ưu hệ thống"""
    try:
        from db.database import cleanup_old_sessions, batch_sync_sessions
        
        # 1. Cleanup old sessions
        cleaned_sessions = cleanup_old_sessions(max_age_hours=24)
        
        # 2. Batch sync remaining sessions
        sync_result = batch_sync_sessions()
        
        # 3. Log optimization results
        logger.info(f"✅ Optimization completed: {cleaned_sessions} sessions cleaned, {sync_result['synced_successfully']} synced")
        
        return {
            "cleaned_sessions": cleaned_sessions,
            "sync_result": sync_result,
            "optimization_time": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"❌ Error in cleanup and optimization: {str(e)}")
        return {"error": str(e)}

# === HEALTH CHECK FUNCTIONS ===
def health_check() -> dict:
    """Kiểm tra sức khỏe hệ thống"""
    try:
        from db.database import get_database_status
        from services import globals
        
        # Check database
        db_status = get_database_status()
        
        # Check vector store
        vector_status = hasattr(globals, 'vectorstore') and globals.vectorstore is not None
        
        # Check memory usage
        import psutil
        memory_percent = psutil.virtual_memory().percent
        
        # Check active sessions
        from db.database import user_sessions
        active_sessions = len(user_sessions)
        
        return {
            "database_connected": db_status["connected"],
            "vector_store_available": vector_status,
            "memory_usage_percent": memory_percent,
            "active_sessions": active_sessions,
            "system_healthy": all([
                db_status["connected"],
                vector_status,
                memory_percent < 85,  # Memory usage under 85%
                active_sessions < 1000  # Less than 1000 active sessions
            ]),
            "check_time": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"❌ Error in health check: {str(e)}")
        return {
            "system_healthy": False,
            "error": str(e),
            "check_time": datetime.now().isoformat()
        }

# === IMPORT FIX ===
def test_image_functionality():
    """Test các chức năng liên quan đến hình ảnh"""
    print("🧪 Testing image functionality...")
    
    # Test 1: Detect image requests
    test_messages = [
        "tôi muốn xem hình áo khoác gió",
        "cho xem ảnh laptop gaming",
        "hình ảnh ba lô đi học",
        "laptop có gì hay không?",  # Không phải image request
        "show pic of jacket",
        "hiển thị thiết kế áo thun"
    ]
    
    print("\n1. Testing detect_image_request:")
    for msg in test_messages:
        is_image_req = detect_image_request(msg)
        print(f"  '{msg}' -> {is_image_req}")
    
    # Test 2: Extract product name
    print("\n2. Testing extract_product_name_from_image_request:")
    image_requests = [
        "tôi muốn xem hình áo khoác gió",
        "cho xem ảnh laptop gaming", 
        "hình ảnh ba lô đi học",
        "show pic of jacket"
    ]
    
    for msg in image_requests:
        product_name = extract_product_name_from_image_request(msg)
        print(f"  '{msg}' -> '{product_name}'")
    
    # Test 3: Get product images
    print("\n3. Testing get_product_images:")
    test_products = ["áo khoác gió", "laptop", "ba lô"]
    
    for product in test_products:
        try:
            images = get_product_images(product, limit=2)
            print(f"  '{product}' -> {len(images)} images found")
            for img in images:
                print(f"    - {img.get('product_name')} ({img.get('image_url')})")
        except Exception as e:
            print(f"  '{product}' -> ERROR: {str(e)}")


def debug_process_chat_message(message: str, session_id: str = "test_session"):
    """Debug version của process_chat_message"""
    print(f"\n🐛 DEBUG: Processing message: '{message}'")
    print(f"🐛 DEBUG: Session ID: {session_id}")
    
    # Check if it's an image request
    is_image_request = detect_image_request(message)
    print(f"🐛 DEBUG: Is image request: {is_image_request}")
    
    if is_image_request:
        product_name = extract_product_name_from_image_request(message)
        print(f"🐛 DEBUG: Extracted product name: '{product_name}'")
        
        if product_name:
            try:
                images = get_product_images(product_name, limit=3)
                print(f"🐛 DEBUG: Found {len(images)} images")
                for i, img in enumerate(images):
                    print(f"🐛 DEBUG:   {i+1}. {img.get('product_name')} - {img.get('image_url')}")
            except Exception as e:
                print(f"🐛 DEBUG: Error getting images: {str(e)}")
    
    # Proceed with normal processing
    try:
        result = process_chat_message(message, session_id)
        print(f"🐛 DEBUG: Result type: {result.get('response_type')}")
        print(f"🐛 DEBUG: Has images: {result.get('has_images')}")
        print(f"🐛 DEBUG: Image count: {len(result.get('images', []))}")
        return result
    except Exception as e:
        print(f"🐛 DEBUG: Error in process_chat_message: {str(e)}")
        import traceback
        traceback.print_exc()
        return None
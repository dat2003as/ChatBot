# === db/database.py (Updated with integrated functions) ===
from dotenv import load_dotenv
import logging
from .sql_api import DatabaseManager
from datetime import datetime
from langchain.memory import ConversationBufferMemory
import uuid
import os
from src.settings import APP_SETTINGS

logger = logging.getLogger(__name__)

# Global variables
db_manager = None
user_sessions = {}


def initialize_database():
    """Khởi tạo kết nối database"""
    global db_manager

    load_dotenv()

    conn_str = (
        "DRIVER={ODBC Driver 17 for SQL Server};"
        f"SERVER={APP_SETTINGS.SQL_SERVER_NAME};"
        f"DATABASE={APP_SETTINGS.SQL_DATABASE_NAME};"
        f"UID={APP_SETTINGS.SQL_DATABASE_USER};"
        f"PWD={APP_SETTINGS.SQL_DATABASE_PASSWORD};"
        "TrustServerCertificate=yes;"
    )

    try:
        db_manager = DatabaseManager(conn_str)
        is_connected, message = db_manager.test_connection()
        if is_connected:
            print("✅ Database connected successfully.")
            print(f"🔧 Connected to: {os.getenv('DB_SERVER')}/{os.getenv('DB_NAME')}")
            logger.info("Database connection established successfully")
            return True
        else:
            print(f"❌ Database connection test failed: {message}")
            logger.error(f"Database connection test failed: {message}")
            db_manager = None
            return False

    except Exception as e:
        print(f"❌ Failed to connect to database: {e}")
        logger.error(f"Failed to connect to database: {e}")
        import traceback

        traceback.print_exc()
        db_manager = None
        return False


def get_or_create_session(session_id: str = None):
    """
    Lấy hoặc tạo session mới với user management hoàn chỉnh
    """
    if not session_id:
        session_id = str(uuid.uuid4())

    if session_id not in user_sessions:
        user_profile = {}

        # Đảm bảo user record tồn tại trước khi sử dụng
        if db_manager:
            try:
                # 1. Kiểm tra user có tồn tại không
                existing_user = db_manager.get_user_by_session_id(session_id)

                if not existing_user:
                    # 2. Tạo user record mới nếu chưa tồn tại
                    user_created = db_manager.create_user_record(session_id)
                    if user_created:
                        logger.info(
                            f"✅ Created new user record for session: {session_id}"
                        )
                    else:
                        logger.error(
                            f"❌ Failed to create user record for session: {session_id}"
                        )
                else:
                    logger.info(
                        f"ℹ️ User record already exists for session: {session_id}"
                    )

                # 3. Lấy profile từ database
                db_profile = db_manager.get_user_profile(session_id)
                if db_profile:
                    user_profile = db_profile
                    logger.info(
                        f"✅ Loaded user profile from DB for session: {session_id}"
                    )
                else:
                    logger.info(
                        f"ℹ️ No existing profile found, using default for session: {session_id}"
                    )

            except Exception as e:
                logger.error(f"❌ Error handling user record: {e}")
                import traceback

                logger.error(f"Traceback: {traceback.format_exc()}")
        else:
            logger.warning(
                "⚠️ Database manager not available, using memory-only session"
            )

        # 4. Tạo session mới
        try:
            from langchain.memory import ConversationBufferMemory

            memory = ConversationBufferMemory(
                memory_key="chat_history", return_messages=True, output_key="answer"
            )

            user_sessions[session_id] = {
                "profile": user_profile,
                "memory": memory,
                "cart": [],
                "created_at": datetime.now().isoformat(),
            }

            logger.info(f"✅ Created new session: {session_id}")

        except Exception as e:
            logger.error(f"❌ Error creating session memory: {e}")
            user_sessions[session_id] = {
                "profile": user_profile,
                "memory": None,
                "cart": [],
                "created_at": datetime.now().isoformat(),
            }
    else:
        logger.info(f"ℹ️ Using existing session: {session_id}")

    return session_id, user_sessions[session_id]


def update_user_info_in_session(session_id: str, user_data: dict) -> bool:
    """Cập nhật thông tin user trong cả session và database"""
    global db_manager, user_sessions

    try:
        # 1. Cập nhật trong session memory
        if session_id in user_sessions:
            profile = user_sessions[session_id].get("profile", {})
            profile.update(user_data)
            user_sessions[session_id]["profile"] = profile
            logger.info(f"✅ Updated user info in session: {session_id}")

        # 2. Cập nhật trong database
        if db_manager:
            # Đảm bảo user record tồn tại
            success = ensure_user_record_exists(session_id)
            if not success:
                logger.error(f"❌ Failed to ensure user record exists: {session_id}")
                return False

            # Cập nhật thông tin user
            update_success = db_manager.update_user_info(session_id, user_data)
            if update_success:
                logger.info(f"✅ Updated user info in database: {session_id}")
            else:
                logger.warning(
                    f"⚠️ Failed to update user info in database: {session_id}"
                )

            # Lưu profile vào user_profiles table
            profile_success = db_manager.save_user_profile_to_db(session_id, user_data)
            if profile_success:
                logger.info(f"✅ Updated user profile in database: {session_id}")
            else:
                logger.warning(
                    f"⚠️ Failed to update user profile in database: {session_id}"
                )

            return update_success and profile_success
        else:
            logger.warning("⚠️ Database manager not available, updated session only")
            return True

    except Exception as e:
        logger.error(f"❌ Error updating user info: {str(e)}")
        import traceback

        logger.error(f"Traceback: {traceback.format_exc()}")
        return False


def save_user_profile_to_db(session_id: str, user_profile: dict):
    """Lưu user profile vào database"""
    global db_manager

    if not db_manager:
        logger.warning("⚠️ Database manager not initialized, cannot save user profile")
        return False

    try:
        # 1. Try to ensure user record exists, but don't fail if it doesn't work
        existing_user = None
        try:
            existing_user = db_manager.get_user_by_session_id(session_id)
            if not existing_user:
                user_created = db_manager.create_user_record(session_id)
                if user_created:
                    logger.info(
                        f"✅ Created user record for profile save: {session_id}"
                    )
                else:
                    logger.warning(
                        f"⚠️ Failed to create user record, but continuing: {session_id}"
                    )
        except Exception as e:
            logger.warning(f"⚠️ Error ensuring user record, but continuing: {str(e)}")

        # 2. Try to update user info in users table
        if (
            user_profile.get("name")
            or user_profile.get("phone")
            or user_profile.get("address")
        ):
            user_data = {
                "name": user_profile.get(
                    "name",
                    existing_user.get("name", "Guest") if existing_user else "Guest",
                ),
                "phone": user_profile.get("phone", ""),
                "address": user_profile.get("address", ""),
            }
            try:
                update_success = db_manager.update_user_info(session_id, user_data)
                if update_success:
                    logger.info(
                        f"✅ Updated user info in users table for session: {session_id}"
                    )
                else:
                    logger.warning(
                        f"⚠️ Failed to update user info for session: {session_id}"
                    )
            except Exception as e:
                logger.warning(f"⚠️ Error updating user info: {str(e)}")

        # 3. Try to save profile to user_profiles table
        try:
            result = db_manager.save_user_profile_to_db(session_id, user_profile)
            if result:
                logger.info(
                    f"✅ User profile saved successfully for session: {session_id}"
                )
                return True
            else:
                logger.warning(
                    f"⚠️ Failed to save user profile for session: {session_id}"
                )
                return False
        except Exception as e:
            logger.error(f"❌ Error saving user profile: {str(e)}")
            return False

    except Exception as e:
        logger.error(f"❌ Failed to save user profile: {str(e)}")
        import traceback

        logger.error(f"Traceback: {traceback.format_exc()}")
        return False


def save_chat_session_to_db(session_id: str, user_id: str, chat_history: str):
    """Lưu chat session với user_id chính xác"""
    global db_manager

    try:
        if db_manager:
            # 1. Đảm bảo user record tồn tại trước
            existing_user = db_manager.get_user_by_session_id(session_id)
            if not existing_user:
                user_created = db_manager.create_user_record(session_id)
                if user_created:
                    logger.info(
                        f"✅ Created user record before saving chat session: {session_id}"
                    )
                else:
                    logger.error(
                        f"❌ Failed to create user record for chat session: {session_id}"
                    )
                    return

            # 2. Lưu chat session với session_id làm user_id
            db_manager.save_chat_session_to_db(session_id, session_id, chat_history)
            logger.info(f"✅ Chat session saved successfully for: {session_id}")
        else:
            logger.warning(
                "⚠️ Database manager not available, skipping chat session save"
            )

    except Exception as e:
        logger.error(f"❌ Failed to save chat session: {str(e)}")
        import traceback

        logger.error(f"Traceback: {traceback.format_exc()}")


def get_database_status():
    """Kiểm tra trạng thái database"""
    global db_manager
    return {
        "connected": db_manager is not None,
        "db_manager_type": type(db_manager).__name__ if db_manager else "None",
    }


def get_db_manager():
    """Thêm function để lấy db_manager từ bên ngoài"""
    global db_manager
    return db_manager


def ensure_user_record_exists(session_id: str) -> bool:
    """Đảm bảo user record tồn tại trong database"""
    global db_manager

    if not db_manager:
        logger.warning("⚠️ Database manager not available")
        return False

    try:
        existing_user = db_manager.get_user_by_session_id(session_id)
        if not existing_user:
            user_created = db_manager.create_user_record(session_id)
            if user_created:
                logger.info(f"✅ Created user record for session: {session_id}")
                return True
            else:
                logger.error(
                    f"❌ Failed to create user record for session: {session_id}"
                )
                return False
        else:
            logger.info(f"ℹ️ User record already exists for session: {session_id}")
            return True

    except Exception as e:
        logger.error(f"❌ Error ensuring user record exists: {str(e)}")
        return False


def get_user_session(session_id: str) -> dict:
    """Lấy session data với error handling"""
    global user_sessions

    if session_id not in user_sessions:
        logger.warning(f"⚠️ Session not found: {session_id}, creating new session")
        session_id, session_data = get_or_create_session(session_id)
        return session_data

    return user_sessions[session_id]


def cleanup_old_sessions(max_age_hours: int = 24) -> int:
    """Dọn dẹp các session cũ"""
    global user_sessions

    try:
        current_time = datetime.now()
        sessions_to_remove = []

        for session_id, session_data in user_sessions.items():
            created_at_str = session_data.get("created_at")
            if created_at_str:
                try:
                    created_at = datetime.fromisoformat(created_at_str)
                    age_hours = (current_time - created_at).total_seconds() / 3600

                    if age_hours > max_age_hours:
                        sessions_to_remove.append(session_id)

                except Exception as e:
                    logger.error(f"❌ Error parsing session date: {str(e)}")
                    sessions_to_remove.append(session_id)

        # Remove old sessions
        for session_id in sessions_to_remove:
            del user_sessions[session_id]
            logger.info(f"🗑️ Removed old session: {session_id}")

        logger.info(
            f"✅ Cleanup completed, removed {len(sessions_to_remove)} old sessions"
        )
        return len(sessions_to_remove)

    except Exception as e:
        logger.error(f"❌ Error during session cleanup: {str(e)}")
        return 0


def get_session_statistics() -> dict:
    """Lấy thống kê về sessions"""
    global user_sessions

    try:
        total_sessions = len(user_sessions)
        sessions_with_profiles = sum(
            1 for s in user_sessions.values() if s.get("profile", {}).get("name")
        )
        sessions_with_carts = sum(1 for s in user_sessions.values() if s.get("cart"))

        return {
            "total_sessions": total_sessions,
            "sessions_with_profiles": sessions_with_profiles,
            "sessions_with_carts": sessions_with_carts,
            "database_connected": db_manager is not None,
        }

    except Exception as e:
        logger.error(f"❌ Error getting session statistics: {str(e)}")
        return {
            "total_sessions": 0,
            "sessions_with_profiles": 0,
            "sessions_with_carts": 0,
            "database_connected": False,
            "error": str(e),
        }


# === UTILITY FUNCTIONS ===
def validate_session_data(session_data: dict) -> bool:
    """Kiểm tra tính hợp lệ của session data"""
    required_keys = ["profile", "memory", "cart", "created_at"]
    return all(key in session_data for key in required_keys)


def safe_json_dumps(data, default=None):
    """JSON serialize with error handling"""
    try:
        import json

        return json.dumps(data, ensure_ascii=False, default=default)
    except Exception as e:
        logger.error(f"❌ JSON serialization error: {str(e)}")
        return "{}"


def safe_json_loads(json_str, default=None):
    """JSON deserialize with error handling"""
    try:
        import json

        return json.loads(json_str) if json_str else (default or {})
    except Exception as e:
        logger.error(f"❌ JSON deserialization error: {str(e)}")
        return default or {}


# === INTEGRATION FUNCTIONS ===
def create_order_integrated(session_id: str, product_info: dict) -> tuple:
    """Tích hợp tạo đơn hàng với user management"""
    try:
        # Import order functions
        from src.services.order import create_order_with_better_product_handling_v2

        # Get session data
        session_data = get_user_session(session_id)
        user_profile = session_data.get("profile", {})

        # Ensure user exists
        if not ensure_user_record_exists(session_id):
            logger.error(f"❌ Failed to ensure user record exists: {session_id}")
            return "ERROR", 0, []

        # Create order
        result = create_order_with_better_product_handling_v2(session_id, user_profile)

        # Update session with order info if successful
        if result[0] != "ERROR":
            order_id, total_amount, product_details = result

            # Save order info to session
            if session_id in user_sessions:
                if "orders" not in user_sessions[session_id]:
                    user_sessions[session_id]["orders"] = []

                user_sessions[session_id]["orders"].append(
                    {
                        "order_id": order_id,
                        "total_amount": total_amount,
                        "products": product_details,
                        "created_at": datetime.now().isoformat(),
                    }
                )

                logger.info(f"✅ Order info saved to session: {session_id}")

        return result

    except Exception as e:
        logger.error(f"❌ Error in integrated order creation: {str(e)}")
        import traceback

        logger.error(f"Traceback: {traceback.format_exc()}")
        return "ERROR", 0, []


def sync_session_to_database(session_id: str) -> bool:
    """Đồng bộ toàn bộ session data xuống database"""
    try:
        if session_id not in user_sessions:
            logger.warning(f"⚠️ Session not found for sync: {session_id}")
            return False

        session_data = user_sessions[session_id]
        user_profile = session_data.get("profile", {})

        # 1. Ensure user record exists
        if not ensure_user_record_exists(session_id):
            return False

        # 2. Save user profile
        profile_saved = save_user_profile_to_db(session_id, user_profile)

        # 3. Save chat history if available
        memory = session_data.get("memory")
        if memory and hasattr(memory, "chat_memory"):
            try:
                chat_history = safe_json_dumps(memory.chat_memory.messages)
                save_chat_session_to_db(session_id, session_id, chat_history)
            except Exception as e:
                logger.error(f"❌ Error saving chat history: {str(e)}")

        logger.info(f"✅ Session synced to database: {session_id}")
        return profile_saved

    except Exception as e:
        logger.error(f"❌ Error syncing session to database: {str(e)}")
        return False


def batch_sync_sessions() -> dict:
    """Đồng bộ tất cả sessions xuống database"""
    global user_sessions

    results = {
        "total_sessions": len(user_sessions),
        "synced_successfully": 0,
        "failed": 0,
        "errors": [],
    }

    for session_id in user_sessions.keys():
        try:
            if sync_session_to_database(session_id):
                results["synced_successfully"] += 1
            else:
                results["failed"] += 1
        except Exception as e:
            results["failed"] += 1
            results["errors"].append(f"Session {session_id}: {str(e)}")

    logger.info(
        f"✅ Batch sync completed: {results['synced_successfully']}/{results['total_sessions']} successful"
    )
    return results

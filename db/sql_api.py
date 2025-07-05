# === db\sql_api.py (DatabaseManager class) ===
import os
import logging
from dotenv import load_dotenv
from fastapi import logger
import pyodbc
import uuid
from datetime import datetime
from typing import Dict, List, Optional, Any
import json

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
class DatabaseManager:
    def __init__(self, conn_str: str = None):
        # Sử dụng connection string được truyền vào, hoặc tạo mặc định
        if conn_str:
            self.conn_str = conn_str
        else:
            load_dotenv()
            self.conn_str = (
                    'DRIVER={ODBC Driver 17 for SQL Server};'
                    f"SERVER={os.getenv('DB_SERVER')};"
                    f"DATABASE={os.getenv('DB_NAME')};"
                    f"UID={os.getenv('DB_USER')};"
                    f"PWD={os.getenv('DB_PASSWORD')};"
                    'TrustServerCertificate=yes;'
            )
    
    def get_connection(self):
        """Tạo kết nối mới đến SQL Server"""
        try:
            return pyodbc.connect(self.conn_str)
        except Exception as e:
            print(f"❌ Lỗi kết nối database: {str(e)}")
            print(f"Connection string: {self.conn_str}")
            raise e

    def test_connection(self):
        """Test kết nối database"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT 1")
            result = cursor.fetchone()
            cursor.close()
            conn.close()
            return True, "Kết nối thành công"
        except Exception as e:
            return False, f"Lỗi kết nối: {str(e)}"

    # ===== PRODUCT METHODS =====
    def get_all_products(self, limit=20, gender=None, category=None, min_price=None, max_price=None):
        """Get products with better error handling"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            # Build query with filters
            query = "SELECT * FROM products WHERE 1=1"
            params = []
            
            if gender:
                query += " AND gender = ?"
                params.append(gender)
            
            if category:
                query += " AND category = ?"
                params.append(category)
            
            if min_price:
                query += " AND price >= ?"
                params.append(min_price)
            
            if max_price:
                query += " AND price <= ?"
                params.append(max_price)
            
            if limit:
                query = query.replace("SELECT", f"SELECT TOP {limit}")
            
            cursor.execute(query, params)
            rows = cursor.fetchall()
            
            # Convert to list of dictionaries
            columns = [column[0] for column in cursor.description]
            products = []
            for row in rows:
                product = dict(zip(columns, row))
                products.append(product)
            
            cursor.close()
            conn.close()

            print(f"✅ Retrieved {len(products)} products from database")
            return products

        except Exception as e:
            print(f"❌ Error in get_all_products: {str(e)}")
            return []
    
    def get_product_by_id(self, product_id: int) -> Optional[Dict[str, Any]]:
        """Lấy thông tin sản phẩm theo ID"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM products WHERE id = ?", (product_id,))
            row = cursor.fetchone()
            
            if row:
                columns = [column[0] for column in cursor.description]
                product_dict = dict(zip(columns, row))
                return product_dict
            return None
        except Exception as e:
            logger.error(f"❌ Error getting product {product_id}: {str(e)}")
            return None
        finally:
            if 'conn' in locals():
                conn.close()

    def get_product_by_id_images(self, product_id: int) -> Optional[Dict[str, Any]]:
        """Lấy thông tin sản phẩm theo ID với tất cả ảnh"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            # Lấy thông tin sản phẩm
            cursor.execute('''
                SELECT p.*, 
                       GROUP_CONCAT(pi.image_url) as additional_images,
                       GROUP_CONCAT(pi.image_type) as image_types,
                       GROUP_CONCAT(pi.display_order) as display_orders
                FROM products p
                LEFT JOIN product_images pi ON p.id = pi.product_id
                WHERE p.id = ?
                GROUP BY p.id
            ''', (product_id,))
            
            row = cursor.fetchone()
            
            if row:
                columns = [column[0] for column in cursor.description]
                product_dict = dict(zip(columns, row))
                # Xử lý nhiều ảnh
                product_dict = self._process_product_images(product_dict)
                return product_dict
            return None
        except Exception as e:
            logger.error(f"❌ Error getting product {product_id}: {str(e)}")
            return None
        finally:
            if 'conn' in locals():
                conn.close()
    
    def _process_product_images(self, product_dict: Dict) -> Dict:
        """Xử lý và chuẩn hóa thông tin ảnh của sản phẩm"""
        images_list = []
        
        # Thêm ảnh chính nếu có
        if product_dict.get('image_url'):
            images_list.append({
                'url': product_dict['image_url'],
                'type': 'main',
                'order': 0
            })
        
        # Xử lý ảnh từ JSON column nếu có
        if product_dict.get('images'):
            try:
                json_images = json.loads(product_dict['images'])
                if isinstance(json_images, list):
                    for i, img_url in enumerate(json_images):
                        if img_url and img_url not in [img['url'] for img in images_list]:
                            images_list.append({
                                'url': img_url,
                                'type': 'gallery',
                                'order': i + 1
                            })
            except json.JSONDecodeError:
                logger.warning(f"Invalid JSON in images column for product {product_dict.get('id')}")
        
        # Xử lý ảnh từ bảng product_images
        if product_dict.get('additional_images'):
            additional_urls = product_dict['additional_images'].split(',')
            image_types = product_dict.get('image_types', '').split(',')
            display_orders = product_dict.get('display_orders', '').split(',')
            
            for i, img_url in enumerate(additional_urls):
                if img_url and img_url.strip() and img_url not in [img['url'] for img in images_list]:
                    img_type = image_types[i] if i < len(image_types) else 'gallery'
                    try:
                        order = int(display_orders[i]) if i < len(display_orders) else len(images_list)
                    except (ValueError, IndexError):
                        order = len(images_list)
                    
                    images_list.append({
                        'url': img_url.strip(),
                        'type': img_type,
                        'order': order
                    })
        
        # Sắp xếp theo thứ tự hiển thị
        images_list.sort(key=lambda x: x['order'])
        
        # Thêm thông tin ảnh vào product
        product_dict['all_images'] = images_list
        product_dict['image_count'] = len(images_list)
        product_dict['main_image'] = images_list[0]['url'] if images_list else None
        product_dict['gallery_images'] = [img['url'] for img in images_list[1:]] if len(images_list) > 1 else []
        
        # Cleanup temporary columns
        product_dict.pop('additional_images', None)
        product_dict.pop('image_types', None)
        product_dict.pop('display_orders', None)
        
        return product_dict

    def get_product_images(self, product_id: int) -> List[Dict[str, Any]]:
        """Lấy tất cả ảnh của một sản phẩm cụ thể"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT image_url, image_type, display_order, alt_text
                FROM product_images
                WHERE product_id = ?
                ORDER BY display_order ASC, id ASC
            ''', (product_id,))
            
            rows = cursor.fetchall()
            images = []
            
            for row in rows:
                images.append({
                    'url': row[0],
                    'type': row[1],
                    'order': row[2],
                    'alt_text': row[3]
                })
            
            return images
            
        except Exception as e:
            logger.error(f"❌ Error getting images for product {product_id}: {str(e)}")
            return []
        finally:
            if 'conn' in locals():
                conn.close()
              
    def search_products_by_name(self, product_name):
        """Tìm kiếm sản phẩm theo tên chính xác"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            query = """
            SELECT id, title, price, description 
            FROM products 
            WHERE LOWER(title) LIKE LOWER(?)
            """
            cursor.execute(query, (f'%{product_name}%',))
            results = cursor.fetchall()
            
            products = []
            for row in results:
                products.append({
                    'id': row[0],
                    'title': row[1], 
                    'price': row[2],
                    'description': row[3]
                })
            
            cursor.close()
            conn.close()
            return products
        except Exception as e:
            print(f"❌ Lỗi search_products_by_name: {str(e)}")
            return []

    def search_products_by_keyword(self, keyword):
        """Tìm kiếm sản phẩm theo từ khóa"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            query = """
            SELECT id, title, price, description 
            FROM products 
            WHERE LOWER(title) LIKE LOWER(?) 
            OR LOWER(description) LIKE LOWER(?)
            """
            cursor.execute(query, (f'%{keyword}%', f'%{keyword}%'))
            results = cursor.fetchall()
            
            products = []
            for row in results:
                products.append({
                    'id': row[0],
                    'title': row[1],
                    'price': row[2], 
                    'description': row[3]
                })
            
            cursor.close()
            conn.close()
            return products
        except Exception as e:
            print(f"❌ Lỗi search_products_by_keyword: {str(e)}")
            return []

    def search_products(self, query: str, limit: int = 20):
        """Tìm kiếm sản phẩm theo từ khóa"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            search_query = """
                SELECT id, title, description, category, price, rating_rate, rating_count, image 
                FROM products 
                WHERE title LIKE ? OR description LIKE ? OR category LIKE ?
                ORDER BY 
                    CASE 
                        WHEN title LIKE ? THEN 1
                        WHEN description LIKE ? THEN 2
                        WHEN category LIKE ? THEN 3
                        ELSE 4
                    END
            """
            
            if limit:
                search_query += f" OFFSET 0 ROWS FETCH NEXT {limit} ROWS ONLY"
            
            search_term = f"%{query}%"
            cursor.execute(search_query, (search_term, search_term, search_term, 
                                        search_term, search_term, search_term))
            
            columns = [column[0] for column in cursor.description]
            products = []
            
            for row in cursor.fetchall():
                product = dict(zip(columns, row))
                products.append(product)
            
            cursor.close()
            conn.close()
            return products
            
        except Exception as e:
            print(f"❌ Error searching products: {str(e)}")
            return []

    # ===== USER METHODS =====
    def save_user_profile_to_db(self, session_id: str, user_profile: Dict[str, Any]) -> bool:
        """Lưu user profile với đồng bộ bảng users"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            # 1. Đảm bảo user record tồn tại
            cursor.execute("SELECT COUNT(*) FROM users WHERE id = ?", (session_id,))
            user_exists = cursor.fetchone()[0] > 0
            
            if not user_exists:
                cursor.execute(
                    """INSERT INTO users (id, name, phone, address, created_at, updated_at) 
                       VALUES (?, ?, ?, ?, GETDATE(), GETDATE())""",
                    (
                        session_id,
                        user_profile.get('name', 'Guest'),
                        user_profile.get('phone', ''),
                        user_profile.get('address', '')
                    )
                )
                logger.info(f"✅ Created user record in users table: {session_id}")
            else:
                # Cập nhật thông tin user nếu đã tồn tại
                cursor.execute(
                    """UPDATE users 
                       SET name = ?, phone = ?, address = ?, updated_at = GETDATE()
                       WHERE id = ?""",
                    (
                        user_profile.get('name', 'Guest'),
                        user_profile.get('phone', ''),
                        user_profile.get('address', ''),
                        session_id
                    )
                )
            
            # 2. Lưu vào user_profiles table
            cleaned_profile = self._clean_user_profile_for_db(user_profile)
            profile_json = json.dumps(cleaned_profile, ensure_ascii=False)
            
            cursor.execute("SELECT COUNT(*) FROM user_profiles WHERE session_id = ?", (session_id,))
            profile_exists = cursor.fetchone()[0] > 0
            
            if profile_exists:
                cursor.execute(
                    """UPDATE user_profiles 
                       SET name = ?, phone = ?, address = ?, preferences = ?, 
                           is_complete = ?, updated_at = GETDATE()
                       WHERE session_id = ?""",
                    (
                        cleaned_profile.get('name', ''),
                        cleaned_profile.get('phone', ''),
                        cleaned_profile.get('address', ''),
                        profile_json,
                        cleaned_profile.get('is_complete', False),
                        session_id
                    )
                )
            else:
                cursor.execute(
                    """INSERT INTO user_profiles 
                       (session_id, name, phone, address, preferences, is_complete, created_at, updated_at)
                       VALUES (?, ?, ?, ?, ?, ?, GETDATE(), GETDATE())""",
                    (
                        session_id,
                        cleaned_profile.get('name', ''),
                        cleaned_profile.get('phone', ''),
                        cleaned_profile.get('address', ''),
                        profile_json,
                        cleaned_profile.get('is_complete', False)
                    )
                )
            
            conn.commit()
            logger.info(f"✅ User profile saved successfully for session_id: {session_id}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error saving user profile to DB: {str(e)}")
            if 'conn' in locals():
                conn.rollback()
            return False
        finally:
            if 'conn' in locals():
                conn.close()


    def get_user_profile(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Lấy user profile"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM user_profiles WHERE session_id = ?", (session_id,))
            row = cursor.fetchone()
            
            if row:
                columns = [column[0] for column in cursor.description]
                user_dict = dict(zip(columns, row))
                if user_dict.get("preferences"):
                    try:
                        user_dict["preferences"] = json.loads(user_dict["preferences"])
                    except:
                        user_dict["preferences"] = {}
                return user_dict
            return None
            
        except Exception as e:
            logger.error(f"❌ Error getting user profile: {str(e)}")
            return None
        finally:
            if 'conn' in locals():
                conn.close()

    # ===== ORDER METHODS =====
    def _clean_user_profile_for_db(self, user_profile: Dict[str, Any]) -> Dict[str, Any]:
        """Làm sạch dữ liệu user profile"""
        cleaned = {}
        
        string_fields = ['name', 'phone', 'address', 'payment_method', 'notes', 'selected_product']
        for field in string_fields:
            value = user_profile.get(field, '')
            if isinstance(value, (dict, list)):
                cleaned[field] = str(value)
            else:
                cleaned[field] = str(value) if value is not None else ''
        
        cleaned['is_complete'] = bool(user_profile.get('is_complete', False))
        cleaned['conversation_count'] = int(user_profile.get('conversation_count', 0))
        
        preferences = user_profile.get('preferences', {})
        if isinstance(preferences, dict):
            safe_preferences = {}
            for key, value in preferences.items():
                safe_key = str(key).replace('thời trang', 'thoi_trang').replace(' ', '_')
                safe_preferences[safe_key] = str(value) if value is not None else ''
            cleaned['preferences'] = safe_preferences
        else:
            cleaned['preferences'] = {}
        
        return cleaned
    
    def create_order(self, user_id: str, product_ids: List[int],
                 total_amount: float, phone: str, address: str,
                 payment_method: str = "cod", notes: str = "") -> str:
        """Tạo đơn hàng với user_id chính xác"""
        order_id = str(uuid.uuid4())
        
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            # SỬA: Đảm bảo user_id tồn tại trước khi tạo order
            cursor.execute("SELECT COUNT(*) FROM users WHERE id = ?", (user_id,))
            user_exists = cursor.fetchone()[0] > 0
            
            if not user_exists:
                # Tạo user record nếu chưa tồn tại
                cursor.execute(
                    """INSERT INTO users (id, name, phone, address, created_at, updated_at) 
                       VALUES (?, ?, ?, ?, GETDATE(), GETDATE())""",
                    (user_id, 'Guest', phone, address)
                )
                logger.info(f"✅ Created user record for order: {user_id}")
            
            # Tạo order
            cursor.execute('''
                INSERT INTO orders (id, user_id, product_ids, total_amount, status, order_date, phone, address, notes, payment_method)
                VALUES (?, ?, ?, ?, ?, GETDATE(), ?, ?, ?, ?)
            ''', (
                order_id,
                user_id,
                json.dumps(product_ids),
                total_amount,
                'pending',
                phone,
                address,
                notes,
                payment_method
            ))
            
            conn.commit()
            logger.info(f"✅ Order {order_id} created successfully")
            return order_id
            
        except Exception as e:
            if 'conn' in locals():
                conn.rollback()
            logger.error(f"❌ Error creating order: {str(e)}")
            raise e
        finally:
            if 'conn' in locals():
                conn.close()
            
    def get_order(self, order_id: str) -> Optional[Dict[str, Any]]:
        """Lấy thông tin đơn hàng theo ID"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute("SELECT * FROM orders WHERE id = ?", (order_id,))
            row = cursor.fetchone()
            
            if row:
                columns = [column[0] for column in cursor.description]
                order_dict = dict(zip(columns, row))
                
                # Parse JSON product_ids
                if order_dict.get("product_ids"):
                    try:
                        order_dict["product_ids"] = json.loads(order_dict["product_ids"])
                    except json.JSONDecodeError:
                        order_dict["product_ids"] = []
                
                # Convert datetime objects to string
                for key, value in order_dict.items():
                    if isinstance(value, datetime):
                        order_dict[key] = value.isoformat()
                
                # Map order_date to created_at for API compatibility
                if 'order_date' in order_dict:
                    order_dict['created_at'] = order_dict['order_date']
                    order_dict['updated_at'] = order_dict['order_date']
                
                return order_dict
            return None
        except Exception as e:
            print(f"❌ Error getting order {order_id}: {str(e)}")
            return None
        finally:
            cursor.close()
            conn.close()

    def get_orders_by_user(self, user_id: str) -> List[Dict[str, Any]]:
        """Lấy tất cả đơn hàng của user"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM orders WHERE user_id = ?", (user_id,))
        rows = cursor.fetchall()
        columns = [col[0] for col in cursor.description]
        orders = []
        for row in rows:
            order = dict(zip(columns, row))
            if order.get("product_ids"):
                try:
                    order["product_ids"] = json.loads(order["product_ids"])
                except:
                    order["product_ids"] = []
            orders.append(order)
        cursor.close()
        conn.close()
        return orders
    
    def update_order_status(self, order_id: str, status: str) -> bool:
        """Cập nhật trạng thái đơn hàng"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute(
                "UPDATE orders SET status = ? WHERE id = ?",
                (status, order_id)
            )
            conn.commit()
            return cursor.rowcount > 0
        except Exception as e:
            conn.rollback()
            print(f"❌ Error updating order status: {str(e)}")
            return False
        finally:
            cursor.close()
            conn.close()

    def get_user_orders(self, user_id: str) -> List[Dict[str, Any]]:
        """Lấy tất cả đơn hàng của user"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute(
                "SELECT * FROM orders WHERE user_id = ? ORDER BY order_date DESC",
                (user_id,)
            )
            rows = cursor.fetchall()
            
            orders = []
            for row in rows:
                columns = [column[0] for column in cursor.description]
                order_dict = dict(zip(columns, row))
                
                # Parse JSON product_ids
                if order_dict.get("product_ids"):
                    try:
                        order_dict["product_ids"] = json.loads(order_dict["product_ids"])
                    except json.JSONDecodeError:
                        order_dict["product_ids"] = []
                
                # Convert datetime objects to string
                for key, value in order_dict.items():
                    if isinstance(value, datetime):
                        order_dict[key] = value.isoformat()
                
                # Map order_date to created_at for API compatibility
                if 'order_date' in order_dict:
                    order_dict['created_at'] = order_dict['order_date']
                    order_dict['updated_at'] = order_dict['order_date']
                
                orders.append(order_dict)
            
            return orders
        except Exception as e:
            print(f"❌ Error getting user orders: {str(e)}")
            return []
        finally:
            cursor.close()
            conn.close()

    def update_order(self, order_id: str, update_fields: Dict[str, Any]) -> bool:
        """Cập nhật các trường của đơn hàng"""
        conn = self.get_connection()
        cursor = conn.cursor()

        fields = []
        values = []

        for key, value in update_fields.items():
            if key == "product_ids" and isinstance(value, list):
                value = json.dumps(value)
            fields.append(f"{key} = ?")
            values.append(value)

        values.append(order_id)
        query = f"UPDATE orders SET {', '.join(fields)} WHERE id = ?"

        try:
            cursor.execute(query, values)
            conn.commit()
            rowcount = cursor.rowcount
            return rowcount > 0
        except Exception as e:
            conn.rollback()
            print(f"❌ Error updating order: {str(e)}")
            return False
        finally:
            cursor.close()
            conn.close()
    
    # ===== CHAT SESSION METHODS =====
    def save_chat_session_to_db(self, session_id: str, user_id: str, chat_history: str):
        """lưu chat"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            # Check if record exists first
            cursor.execute("SELECT COUNT(*) FROM users WHERE id = ?", (session_id,))
            user_exists = cursor.fetchone()[0] > 0
            
            if not user_exists:
                cursor.execute(
                    """INSERT INTO users (id, name, created_at, updated_at) 
                       VALUES (?, ?, GETDATE(), GETDATE())""",
                    (session_id, 'Guest')
                )
                logger.info(f"✅ Created user record for chat session: {session_id}")
            
            # Lưu chat session
            cursor.execute("SELECT COUNT(*) FROM chat_sessions WHERE session_id = ?", (session_id,))
            exists = cursor.fetchone()[0] > 0
            
            if exists:
                cursor.execute(
                    "UPDATE chat_sessions SET chat_history = ?, updated_at = GETDATE() WHERE session_id = ?",
                    (chat_history, session_id)
                )
            else:
                cursor.execute(
                    "INSERT INTO chat_sessions (session_id, user_id, chat_history, created_at, updated_at) VALUES (?, ?, ?, GETDATE(), GETDATE())",
                    (session_id, session_id, chat_history)  # SỬA: Sử dụng session_id cho cả hai
                )
            
            conn.commit()
            logger.info(f"✅ Chat session saved successfully for session_id: {session_id}")
            
        except Exception as e:
            logger.error(f"❌ Failed to save chat session to database: {str(e)}")
            if 'conn' in locals():
                conn.rollback()
        finally:
            if 'conn' in locals():
                conn.close()
    # ===== STATISTICS METHODS =====
    def get_statistics(self) -> Dict[str, Any]:
        """Lấy thống kê hệ thống"""
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT COUNT(*) FROM users")
        total_users = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM orders")
        total_orders = cursor.fetchone()[0]

        cursor.execute("SELECT SUM(total_amount) FROM orders WHERE status != 'cancelled'")
        total_revenue = cursor.fetchone()[0] or 0

        cursor.execute('''
            SELECT status, COUNT(*) FROM orders 
            GROUP BY status
        ''')
        orders_by_status = dict(cursor.fetchall())

        cursor.close()
        conn.close()

        return {
            "total_users": total_users,
            "total_orders": total_orders,
            "total_revenue": total_revenue,
            "orders_by_status": orders_by_status
        }
    #===== THÊM METHODS XỬ LÝ USER =====
    def create_user_record(self, session_id: str) -> bool:
        """Tạo user record mới trong bảng users"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            # Kiểm tra user đã tồn tại chưa
            cursor.execute("SELECT COUNT(*) FROM users WHERE id = ?", (session_id,))
            exists = cursor.fetchone()[0] > 0
            
            if not exists:
                cursor.execute(
                    """
                INSERT INTO users (session_id, name, phone, address, created_at, updated_at)
                VALUES (?, ?, ?, ?, GETDATE(), GETDATE())
            """,
                    (session_id, 'Guest', '', '')
                )
                conn.commit()
                logger.info(f"✅ Created user record for session: {session_id}")
                return True
            else:
                logger.info(f"ℹ️ User record already exists for session: {session_id}")
                return True
                
        except Exception as e:
            logger.error(f"❌ Error creating user record: {str(e)}")
            if 'conn' in locals():
                conn.rollback()
            return False
        finally:
            if 'conn' in locals():
                conn.close()

    def get_user_by_session_id(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Lấy thông tin user theo session_id"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM users WHERE id = ?", (session_id,))
            row = cursor.fetchone()
            
            if row:
                columns = [column[0] for column in cursor.description]
                user_dict = dict(zip(columns, row))
                return user_dict
            return None
            
        except Exception as e:
            logger.error(f"❌ Error getting user by session_id: {str(e)}")
            return None
        finally:
            if 'conn' in locals():
                conn.close()

    def update_user_info(self, session_id: str, user_data: Dict[str, Any]) -> bool:
        """Cập nhật thông tin user"""
        try:
            # Build dynamic update query based on available data
            update_fields = []
            params = []
            
            if user_data.get('name'):
                update_fields.append("name = ?")
                params.append(user_data['name'])
            
            if user_data.get('phone'):
                update_fields.append("phone = ?")
                params.append(user_data['phone'])
            
            if user_data.get('address'):
                update_fields.append("address = ?")
                params.append(user_data['address'])
            
            if not update_fields:
                logger.warning(f"No fields to update for session: {session_id}")
                return True
            
            # Add updated_at field
            update_fields.append("updated_at = GETDATE()")
            
            # Add session_id for WHERE clause
            params.append(session_id)
            
            query = f"""
                UPDATE users 
                SET {', '.join(update_fields)}
                WHERE session_id = ?
            """
            
            cursor = self.connection.cursor()
            cursor.execute(query, params)
            rows_affected = cursor.rowcount
            self.connection.commit()
            cursor.close()
            
            if rows_affected > 0:
                logger.info(f"✅ User info updated successfully for session: {session_id}")
                return True
            else:
                logger.warning(f"⚠️ No rows updated for session: {session_id}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Error updating user info: {str(e)}")
            return False

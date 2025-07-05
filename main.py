import logging
import uuid
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse, Response, HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone
import os
import re
from contextlib import asynccontextmanager


from db.database import db_manager, initialize_database, get_database_status

from src.schema.models import (
    ChatMessage,
    ChatResponse,
    UserProfile,
    Product,
    ProductSearchRequest,
    OrderRequest,
    OrderResponse,
    OrderInfo,
    OrderStatusUpdate,
    ContactInfo,
    SystemStats,
)

from db.sql_api import DatabaseManager
from src.services.create_images import debug_image_pipeline
from src.services.order import test_improved_matching
from src.startup import initializer

# Import DatabaseManager from the correct path
from src.services.chat_logic import (
    debug_process_chat_message,
    process_chat_message,
    test_image_functionality,
)


# Dictionary để lưu trữ session của users (memory cache)
user_sessions: Dict[str, Dict] = {}

logger = logging.getLogger(__name__)
db_manager = DatabaseManager()


# ===== API ENDPOINTS =====


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    print("🚀 Starting Shopping Assistant API...")

    # Initialize database first
    if not initialize_database():
        print("❌ Failed to initialize database during startup")
    else:
        print("✅ Database initialized successfully")

    # Initialize system
    if not initializer.initialize_system():
        print("❌ Failed to initialize system during startup")
    else:
        print("✅ System initialized successfully")

    # Check database connection status
    db_status = get_database_status()
    print(f"📊 Database status: {db_status}")

    yield

    # Shutdown
    print("🛑 Shutting down Shopping Assistant API...")


# Khởi tạo FastAPI app
app = FastAPI(
    title="Shopping Assistant API",
    description="API cho trợ lý mua sắm thông minh với tính năng cá nhân hóa và xử lý đơn hàng",
    version="2.0.0",
    lifespan=lifespan,  # Add lifespan to the app
)

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# Cấu hình CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8000"],
    allow_credentials=True,  # Đặt False khi allow_origins=["*"]
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)


@app.middleware("http")
async def cors_handler(request: Request, call_next):
    if request.method == "OPTIONS":
        response = JSONResponse(content={})
        response.headers["Access-Control-Allow-Origin"] = "*"
        response.headers["Access-Control-Allow-Methods"] = (
            "GET, POST, PUT, DELETE, OPTIONS"
        )
        response.headers["Access-Control-Allow-Headers"] = "*"
        return response

    response = await call_next(request)
    response.headers["Access-Control-Allow-Origin"] = "*"
    return response


@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/api", response_class=JSONResponse)
async def root_api():
    return {
        "message": "Shopping Assistant API is running!",
        "version": "2.0.0",
        "database_connected": db_manager is not None,
        "endpoints": {
            "chat": "/chat",
            "products": "/products",
            "search": "/search",
            "session": "/session/{session_id}",
            "orders": "/orders",
            "health": "/health",
            "stats": "/stats",
        },
    }


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatMessage):
    """Endpoint chính cho chat với trợ lý - FIXED VERSION"""
    try:
        # Validate input
        if not request.message or not request.message.strip():
            raise HTTPException(status_code=400, detail="Tin nhắn không được để trống")

        # Ensure session_id exists
        if not request.session_id:
            request.session_id = str(uuid.uuid4())

        print(f"🔄 Processing chat for session: {request.session_id}")
        print(f"📝 Message: {request.message[:100]}...")

        # Process chat message with error handling
        try:
            result = process_chat_message(request.message, request.session_id)

            # Validate result structure
            if not isinstance(result, dict):
                raise ValueError("process_chat_message must return a dictionary")

            # Ensure required fields exist
            required_fields = ["response", "session_id"]
            for field in required_fields:
                if field not in result:
                    result[field] = (
                        getattr(request, field, "") if hasattr(request, field) else ""
                    )

            # Ensure response is not empty
            if not result.get("response"):
                result["response"] = (
                    "Xin lỗi, tôi không thể xử lý yêu cầu này lúc này. Vui lòng thử lại."
                )

            # ✅ THÊM XỬ LÝ IMAGES - QUAN TRỌNG!
            # Đảm bảo images được truyền từ process_chat_message
            print(f"🔍 Full result from process_chat_message:")
            print(f"  - images: {result.get('images', 'NOT_FOUND')}")
            print(f"  - has_images: {result.get('has_images', 'NOT_FOUND')}")
            print(f"  - image_count: {result.get('image_count', 'NOT_FOUND')}")
            print(f"  - html_content: {result.get('html_content', 'NOT_FOUND')}")
            if "images" not in result:
                result["images"] = []
            if "has_images" not in result:
                result["has_images"] = len(result["images"]) > 0
            if "image_count" not in result:
                result["image_count"] = len(result["images"])
            if "html_content" not in result:
                result["html_content"] = None

            print(f"✅ Chat processed successfully for session: {request.session_id}")
            print(f"🖼️ Images in result: {len(result.get('images', []))}")
            print(
                f"📊 Image data: {result.get('images', [])[:1]}"
            )  # Log first image for debug

            return ChatResponse(**result)

        except ImportError as e:
            print(f"❌ Import error in process_chat_message: {str(e)}")
            raise HTTPException(status_code=500, detail="Lỗi cấu hình hệ thống")

        except Exception as e:
            print(f"❌ Error in process_chat_message: {str(e)}")
            import traceback

            traceback.print_exc()

            # Return fallback response
            return ChatResponse(
                response="Xin lỗi, có lỗi xảy ra khi xử lý tin nhắn của bạn. Vui lòng thử lại.",
                session_id=request.session_id,
                user_profile={},
                is_profile_complete=False,
                suggested_products=[],
                cart_items=[],
                images=[],  # ✅ THÊM
                has_images=False,  # ✅ THÊM
                image_count=0,  # ✅ THÊM
                html_content=None,  # ✅ THÊM
            )

    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Unexpected error in chat endpoint: {str(e)}")
        import traceback

        traceback.print_exc()
        raise HTTPException(
            status_code=500, detail=f"Lỗi server không mong đợi: {str(e)}"
        )


@app.get("/products")
def get_products(
    limit: int = 20,
    gender: Optional[str] = None,
    category: Optional[str] = None,
    min_price: Optional[float] = None,
    max_price: Optional[float] = None,
):
    try:
        if not db_manager:
            raise HTTPException(status_code=503, detail="Database không khả dụng")

        filtered_products = db_manager.get_all_products(
            limit=limit,
            gender=gender,
            category=category,
            min_price=min_price,
            max_price=max_price,
        )

        return {
            "products": filtered_products,
            "total": len(filtered_products),
            "filters_applied": {
                "gender": gender,
                "category": category,
                "min_price": min_price,
                "max_price": max_price,
                "limit": limit,
            },
            "success": True,
        }

    except Exception as e:
        print(f"❌ Error in get_products: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Lỗi lấy sản phẩm: {str(e)}")


@app.get("/products/{product_id}")
async def get_product_by_id(product_id: str):
    """Lấy thông tin chi tiết một sản phẩm"""
    try:
        if not db_manager:
            raise HTTPException(status_code=503, detail="Database không khả dụng")

        product = db_manager.get_product_by_id(product_id)

        if not product:
            raise HTTPException(status_code=404, detail="Sản phẩm không tồn tại")

        return {"product": product, "success": True}

    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error getting product by ID: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Lỗi lấy sản phẩm: {str(e)}")


@app.post("/search")
def search_products(request: ProductSearchRequest):
    """Tìm kiếm sản phẩm từ database"""
    try:
        if not db_manager:
            raise HTTPException(status_code=503, detail="Database không khả dụng")

        # Tìm kiếm cơ bản từ database
        all_products = db_manager.get_all_products(
            gender=request.gender,
            category=request.category,
            min_price=request.min_price,
            max_price=request.max_price,
        )

        # Filter theo từ khóa tìm kiếm
        if request.query:
            query_lower = request.query.lower()
            filtered_products = []

            for product in all_products:
                if (
                    query_lower in product["title"].lower()
                    or query_lower in product["description"].lower()
                    or query_lower in product["category"].lower()
                ):
                    filtered_products.append(product)

            results = filtered_products[: request.limit]
        else:
            results = all_products[: request.limit]

        return {
            "products": results,
            "total": len(results),
            "query": request.query,
            "success": True,
        }

    except Exception as e:
        print(f"❌ Error in search: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Lỗi tìm kiếm: {str(e)}")


# ===== ORDER ENDPOINTS =====
@app.post("/orders", response_model=OrderResponse)
async def create_order(request: OrderRequest):
    """Tạo đơn hàng mới - FIXED version for your table schema"""
    try:
        if not db_manager:
            raise HTTPException(status_code=503, detail="Database không khả dụng")

        # Kiểm tra session tồn tại
        if request.session_id not in user_sessions:
            raise HTTPException(status_code=404, detail="Session không tồn tại")

        # Validate product_ids không rỗng
        if not request.product_ids:
            raise HTTPException(
                status_code=400, detail="Danh sách sản phẩm không được rỗng"
            )

        # Tính tổng tiền từ các sản phẩm thực tế
        total_amount = 0.0
        product_details = []

        for product_id in request.product_ids:
            product = db_manager.get_product_by_id(product_id)
            if product:
                total_amount += float(product["price"])
                product_details.append(product)
            else:
                print(f"⚠️ Product ID {product_id} not found")

        if total_amount == 0:
            raise HTTPException(
                status_code=400, detail="Không tìm thấy sản phẩm hợp lệ"
            )

        # Override total_amount nếu được truyền từ request
        if request.total_amount:
            total_amount = request.total_amount

        # Tạo đơn hàng với đầy đủ thông tin - Fixed parameter order
        order_id = db_manager.create_order(
            user_id=request.session_id,
            product_ids=request.product_ids,
            total_amount=total_amount,
            phone=request.phone,
            address=request.address,
            payment_method=request.payment_method.value,
            notes=request.notes or "",
        )

        print(f"✅ Order created successfully: {order_id}")

        return OrderResponse(
            order_id=order_id,
            status="pending",
            total_amount=total_amount,
            payment_method=request.payment_method.value,
            message=f"Đơn hàng #{order_id} đã được tạo thành công! Phương thức thanh toán: {request.payment_method.value}",
        )

    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        print(f"❌ Error creating order: {str(e)}")
        print(f"Request data: {request.dict()}")
        raise HTTPException(status_code=500, detail=f"Lỗi tạo đơn hàng: {str(e)}")


@app.get("/orders/{order_id}", response_model=OrderInfo)
async def get_order(order_id: str):
    """Lấy thông tin đơn hàng - FIXED version for your table schema"""
    try:
        if not db_manager:
            raise HTTPException(status_code=503, detail="Database không khả dụng")

        order = db_manager.get_order(order_id)
        if not order:
            raise HTTPException(status_code=404, detail="Đơn hàng không tồn tại")

        # Ensure all required fields exist with defaults
        order_info = {
            "id": order.get("id", ""),
            "user_id": order.get("user_id", ""),
            "product_ids": order.get("product_ids", []),
            "total_amount": float(order.get("total_amount", 0)),
            "phone": order.get("phone", ""),
            "address": order.get("address", ""),
            "payment_method": order.get("payment_method", "cod"),
            "notes": order.get("notes", ""),
            "status": order.get("status", "pending"),
            "created_at": order.get("created_at", order.get("order_date", "")),
            "updated_at": order.get("updated_at", order.get("order_date", "")),
        }

        return OrderInfo(**order_info)

    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        print(f"❌ Error getting order {order_id}: {str(e)}")
        raise HTTPException(
            status_code=500, detail=f"Lỗi lấy thông tin đơn hàng: {str(e)}"
        )


@app.get("/users/{user_id}/orders")
async def get_user_orders(user_id: str):
    """Lấy tất cả đơn hàng của user"""
    try:
        if not db_manager:
            raise HTTPException(status_code=503, detail="Database không khả dụng")

        orders = db_manager.get_user_orders(user_id)
        return {"orders": orders, "count": len(orders)}

    except Exception as e:
        print(f"❌ Error getting user orders: {str(e)}")
        raise HTTPException(
            status_code=500, detail=f"Lỗi lấy danh sách đơn hàng: {str(e)}"
        )


@app.put("/orders/{order_id}/status")
async def update_order_status(order_id: str, status: str):
    """Cập nhật trạng thái đơn hàng"""
    try:
        if not db_manager:
            raise HTTPException(status_code=503, detail="Database không khả dụng")

        valid_statuses = [
            "pending",
            "confirmed",
            "processing",
            "shipped",
            "delivered",
            "cancelled",
        ]
        if status not in valid_statuses:
            raise HTTPException(
                status_code=400,
                detail=f"Trạng thái không hợp lệ. Chỉ chấp nhận: {valid_statuses}",
            )

        success = db_manager.update_order_status(order_id, status)
        if not success:
            raise HTTPException(
                status_code=404,
                detail="Không tìm thấy đơn hàng hoặc không thể cập nhật",
            )

        return {
            "message": f"Đã cập nhật trạng thái đơn hàng #{order_id} thành '{status}'"
        }

    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error updating order status: {str(e)}")
        raise HTTPException(
            status_code=500, detail=f"Lỗi cập nhật trạng thái: {str(e)}"
        )


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "database_connected": db_manager is not None,
        "active_sessions": len(user_sessions),
    }


@app.options("/chat")
async def chat_options():
    return Response(
        status_code=200,
        headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "POST, OPTIONS",
            "Access-Control-Allow-Headers": "Content-Type, Accept",
        },
    )


@app.options("/{full_path:path}")
async def options_handler(request: Request, full_path: str):
    return Response(
        status_code=200,
        headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS",
            "Access-Control-Allow-Headers": "Content-Type, Authorization",
        },
    )


@app.get("/vector-store/status")
async def get_vector_store_status_endpoint():
    """Kiểm tra trạng thái của vector store"""
    try:
        status = initializer.get_vector_store_status()
        return {
            "status": status,
            "success": True,
            "message": "Vector store status retrieved successfully",
        }
    except Exception as e:
        print(f"❌ Error getting vector store status: {str(e)}")
        raise HTTPException(
            status_code=500, detail=f"Lỗi kiểm tra vector store: {str(e)}"
        )


@app.get("/test/search")
def trigger_test_search():
    try:
        # test_image_functionality()
        print("\n" + "=" * 50)
        print("TESTING DEBUG FUNCTION")
        print("=" * 50)
        debug_image_pipeline("áo khoác gió nam")
        return {
            "status": "success",
            "message": "test_search_function() đã được thực thi",
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}


# ===== RUN SERVER =====
if __name__ == "__main__":
    import uvicorn

    if not initializer.initialize_system():
        print("❌ Failed to initialize system during startup")
    else:
        print("✅ System initialized successfully")
    print("🚀 Starting Shopping Assistant API on http://localhost:8000")
    from src.settings import APP_SETTINGS

    uvicorn.run(
        app, host=APP_SETTINGS.api_host, port=APP_SETTINGS.api_port, reload=False
    )

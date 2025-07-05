# startup/initializer.py
import os
from dotenv import load_dotenv
import db.database as db
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_community.vectorstores import FAISS
from langchain.schema import Document
import json
import re
from services.globals import retriever, products, products_by_gender


def detect_gender(text):
    """Detect gender from product text - moved here to avoid circular import"""
    if not text:
        return "khác"
    
    text_lower = text.lower()
    
    # Keywords for male products
    male_keywords = [
        'nam', 'men', 'boy', 'male', 'gentleman', 'sir', 'man', 'boys',
        'nam giới', 'đàn ông', 'quần short nam', 'áo sơ mi nam', 'giày nam',
        'thắt lưng nam', 'đồng hồ nam', 'túi nam', 'mũ nam'
    ]
    
    # Keywords for female products  
    female_keywords = [
        'nữ', 'women', 'girl', 'female', 'lady', 'woman', 'girls',
        'nữ giới', 'phụ nữ', 'chị em', 'váy', 'đầm', 'áo kiểu',
        'giày cao gót', 'túi xách nữ', 'đồng hồ nữ', 'trang sức'
    ]
    
    male_score = sum(1 for keyword in male_keywords if keyword in text_lower)
    female_score = sum(1 for keyword in female_keywords if keyword in text_lower)
    
    if male_score > female_score:
        return "nam"
    elif female_score > male_score:
        return "nữ"
    else:
        return "khác"

def initialize_system():
    """Initialize all system components"""
    print("🔄 Initializing system...")
    
    # Load environment variables
    load_dotenv()
    
    # Check required environment variables
    required_env_vars = ['DB_SERVER', 'DB_NAME', 'DB_USER', 'DB_PASSWORD', 'GOOGLE_API_KEY']
    missing_vars = []
    
    for var in required_env_vars:
        if not os.getenv(var):
            missing_vars.append(var)
    
    if missing_vars:
        print(f"❌ Missing required environment variables: {missing_vars}")
        return False
    
    # Initialize database
    try:
        db.initialize_database()
        if db.db_manager is None:
            print("❌ Database manager not initialized.")
            return False
        print("✅ Database initialized successfully.")
    except Exception as e:
        print(f"❌ Database initialization failed: {e}")
        return False
    
    # Initialize vector store and retriever
    try:
        success = initialize_vector_store()
        if success:
            print("✅ Vector store initialized successfully.")
        else:
            print("⚠️ Vector store initialization failed, continuing with basic search...")
    except Exception as e:
        print(f"❌ Vector store initialization failed: {e}")
        print("⚠️ Continuing without vector store...")
    
    print("✅ System initialization completed successfully!")
    return True

def debug_vector_store():
    """Debug vector store để kiểm tra tình trạng"""
    print("🔍 DEBUGGING VECTOR STORE:")
    print(f"📊 Retriever object: {retriever}")
    print(f"📊 Retriever type: {type(retriever) if retriever else 'None'}")
    
    if retriever:
        try:
            # Test search với từ khóa đơn giản
            test_query = "áo"
            docs = retriever.get_relevant_documents(test_query)
            print(f"✅ Test search '{test_query}' trả về {len(docs)} documents")
            
            for i, doc in enumerate(docs[:3]):
                print(f"📄 Doc {i}:")
                print(f"   - Content: {doc.page_content[:100]}...")
                print(f"   - Metadata: {doc.metadata}")
                print()
                
        except Exception as e:
            print(f"❌ Test search thất bại: {str(e)}")
            import traceback
            print(f"❌ Traceback: {traceback.format_exc()}")
    
    print(f"📦 Products list: {len(products) if products else 0} items")
    if products:
        print(f"📦 First product: {products[0]}")

def initialize_vector_store():
    """Initialize vector store for product search"""
    global retriever, products, documents, products_by_gender
    
    try:
        # Get products from database
        if not db.db_manager:
            print("❌ Database manager not available for vector store")
            return False
            
        products = db.db_manager.get_all_products(limit=1000)  # Get more products for better search
        
        if not products:
            print("⚠️ No products found in database for vector store")
            return False
        
        print(f"📦 Found {len(products)} products for vector store")
        
        # Organize products by gender
        products_by_gender = {"nam": [], "nữ": [], "khác": []}
        
        # Create documents for vector store
        documents = []
        for product in products:
            try:
                # Detect gender for the product using local function
                gender = detect_gender(f"{product.get('title', '')} {product.get('description', '')}")
                product['gender'] = gender  # Add gender to product data
                products_by_gender[gender].append(product)
                
                # Create comprehensive text for each product
                product_text = f"""
                Title: {product.get('title', '')}
                Category: {product.get('category', '')}
                Gender: {gender}
                Price: ${product.get('price', 0)}
                Description: {product.get('description', '')}
                Brand: {product.get('brand', '')}
                Color: {product.get('color', '')}
                Size: {product.get('size', '')}
                """
                
                doc = Document(
                    page_content=product_text.strip(),
                    metadata={
                        'id': product.get('id', ''),
                        'title': product.get('title', ''),
                        'category': product.get('category', ''),
                        'price': product.get('price', 0),
                        'gender': gender,
                        'brand': product.get('brand', ''),
                        'color': product.get('color', ''),
                        'size': product.get('size', '')
                    }
                )
                documents.append(doc)
                
            except Exception as e:
                print(f"⚠️ Error processing product {product.get('id', 'unknown')}: {str(e)}")
                continue
        
        print(f"📊 Products by gender: Nam({len(products_by_gender['nam'])}), Nữ({len(products_by_gender['nữ'])}), Khác({len(products_by_gender['khác'])})")
        
        if not documents:
            print("⚠️ No valid documents created for vector store")
            return False
        
        # Initialize embeddings
        GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
        if not GOOGLE_API_KEY:
            print("❌ GOOGLE_API_KEY not found for embeddings")
            return False
            
        try:
            embeddings = GoogleGenerativeAIEmbeddings(
                model="models/embedding-001",
                google_api_key=GOOGLE_API_KEY
            )
            
            print("🔄 Creating vector store... (this may take a moment)")
            
            # Create vector store
            vectorstore = FAISS.from_documents(documents, embeddings)
            retriever = vectorstore.as_retriever(
                search_type="similarity",
                search_kwargs={"k": 5}  # Return top 5 most similar products
            )
            
            print(f"✅ Vector store created successfully with {len(documents)} documents")
            
            return True
            
        except Exception as e:
            print(f"❌ Error creating vector store: {str(e)}")
            return False
                
    except Exception as e:
        print(f"❌ Critical error in vector store initialization: {str(e)}")
        return False

def get_vector_store_status():
    """Get current status of vector store components"""
    global retriever, products, documents, products_by_gender
    
    return {
        "retriever_available": retriever is not None,
        "products_count": len(products),
        "documents_count": len(documents),
        "products_by_gender": {
            "nam": len(products_by_gender["nam"]),
            "nữ": len(products_by_gender["nữ"]),
            "khác": len(products_by_gender["khác"])
        }
    }

def reinitialize_vector_store():
    """Reinitialize vector store (useful for updating after product changes)"""
    global retriever, products, documents, products_by_gender
    
    print("🔄 Reinitializing vector store...")
    
    # Reset global variables
    retriever = None
    products = []
    documents = []
    products_by_gender = {"nam": [], "nữ": [], "khác": []}
    
    # Reinitialize
    return initialize_vector_store()

# Test function for development
def test_vector_search(query: str, limit: int = 3):
    """Test vector search functionality"""
    global retriever
    
    if not retriever:
        return {"error": "Vector store not initialized"}
    
    try:
        docs = retriever.get_relevant_documents(query)
        results = []
        
        for doc in docs[:limit]:
            results.append({
                "title": doc.metadata.get("title"),
                "category": doc.metadata.get("category"),
                "price": doc.metadata.get("price"),
                "gender": doc.metadata.get("gender"),
                "content_preview": doc.page_content[:200] + "..."
            })
        
        return {"results": results, "count": len(results)}
        
    except Exception as e:
        return {"error": f"Search failed: {str(e)}"}

# Export global variables for use in other modules
__all__ = ['retriever', 'products', 'documents', 'products_by_gender', 
           'initialize_system', 'initialize_vector_store', 'get_vector_store_status', 
           'reinitialize_vector_store', 'test_vector_search', 'detect_gender']
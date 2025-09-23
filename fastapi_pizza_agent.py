"""
FastAPI Pizza Ordering Agent - Main Application
"""
import asyncio
import logging
import uuid
from datetime import datetime
from typing import Dict, List, Optional, Any
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
import uvicorn

# Add src to Python path
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from config.settings import SUPABASE_URL, SUPABASE_HEADERS, RESTAURANT_ID
from services.menu_service import MenuService
from services.order_service import OrderService
from services.utility_service import UtilityService
from models.order_models import OrderState, CartItem, OrderSession, generate_cart_id

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global services
menu_service = MenuService()
order_sessions: Dict[str, OrderSession] = {}
websocket_connections: Dict[str, WebSocket] = {}

# Pydantic Models
class MenuSearchRequest(BaseModel):
    query: str = Field(..., description="Search query for menu items")
    limit: int = Field(5, description="Maximum number of results")
    min_score: float = Field(0.3, description="Minimum similarity score")

class MenuSearchResponse(BaseModel):
    items: List[Dict[str, Any]]
    total_found: int

class AddItemRequest(BaseModel):
    item_id: str = Field(..., description="ID of the menu item")
    size: Optional[str] = Field(None, description="Size selection")
    quantity: int = Field(1, description="Quantity to add")
    customizations: List[str] = Field(default_factory=list, description="Customizations")
    cart_id: Optional[str] = Field(None, description="Cart ID")

class UpdateQuantityRequest(BaseModel):
    item_name: str = Field(..., description="Name of the item to update")
    quantity: int = Field(..., description="New quantity")
    cart_id: Optional[str] = Field(None, description="Cart ID")

class RemoveItemRequest(BaseModel):
    item_name: str = Field(..., description="Name of the item to remove")
    cart_id: Optional[str] = Field(None, description="Cart ID")

class CustomerInfoRequest(BaseModel):
    name: str = Field(..., description="Customer name")
    phone: Optional[str] = Field(None, description="Customer phone number")
    cart_id: Optional[str] = Field(None, description="Cart ID")

class OrderCompletionRequest(BaseModel):
    special_instructions: Optional[str] = Field(None, description="Special instructions")
    cart_id: Optional[str] = Field(None, description="Cart ID")

class ChatMessage(BaseModel):
    message: str = Field(..., description="User message")
    cart_id: Optional[str] = Field(None, description="Cart ID")

class ChatResponse(BaseModel):
    response: str = Field(..., description="Agent response")
    cart_id: str = Field(..., description="Cart ID")
    cart_summary: Optional[str] = Field(None, description="Current cart summary")

# Application lifespan
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Starting FastAPI Pizza Ordering Agent...")
    await menu_service.fetch_menu_from_api()
    logger.info("Menu loaded successfully")
    yield
    # Shutdown
    logger.info("Shutting down FastAPI Pizza Ordering Agent...")

# Create FastAPI app
app = FastAPI(
    title="Pizza Ordering Agent API",
    description="A FastAPI-based pizza ordering system with AI-powered menu search and order management",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Dependency to get or create session
async def get_session(cart_id: Optional[str] = None) -> OrderSession:
    if not cart_id:
        cart_id = generate_cart_id()
    
    if cart_id not in order_sessions:
        order_sessions[cart_id] = OrderSession()
        order_sessions[cart_id].cart_id = cart_id
    
    return order_sessions[cart_id]

# Health check endpoint
@app.get("/health")
async def health_check():
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}

# Menu endpoints
@app.get("/api/menu")
async def get_menu():
    """Get the complete menu"""
    try:
        menu_summary = menu_service.get_menu_summary()
        return {"menu": menu_service.menu_data, "summary": menu_summary}
    except Exception as e:
        logger.error(f"Error fetching menu: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch menu")

@app.get("/api/menu/categories")
async def get_menu_categories():
    """Get all menu categories"""
    try:
        categories = menu_service.get_menu_categories()
        return {"categories": categories}
    except Exception as e:
        logger.error(f"Error fetching categories: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch categories")

@app.get("/api/menu/search")
async def search_menu(query: str, limit: int = 5, min_score: float = 0.3):
    """Search menu items with fuzzy matching"""
    try:
        matches = menu_service.fuzzy_search_items(
            query, 
            limit=limit, 
            min_score=min_score
        )
        return MenuSearchResponse(
            items=[match['item'] for match in matches],
            total_found=len(matches)
        )
    except Exception as e:
        logger.error(f"Error searching menu: {e}")
        raise HTTPException(status_code=500, detail="Failed to search menu")

@app.get("/api/menu/item")
async def get_item_details(item_id: str):
    """Get detailed information about a specific menu item"""
    try:
        item = menu_service.get_item_by_id(item_id)
        if not item:
            raise HTTPException(status_code=404, detail="Item not found")
        return {"item": item}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching item details: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch item details")

# Order management endpoints
@app.post("/api/order/add-item")
async def add_item_to_order(request: AddItemRequest):
    """Add an item to the order"""
    try:
        # Get or create session with cart_id from request
        session = await get_session(request.cart_id)
        
        item = menu_service.get_item_by_id(request.item_id)
        if not item:
            raise HTTPException(status_code=404, detail="Item not found")
        
        order_service = OrderService()
        order_service.cart = session.cart
        order_service.state = session.state
        
        cart_item = order_service.add_item_to_cart(
            item, request.size, request.quantity, request.customizations
        )
        
        # Update session
        session.cart = order_service.cart
        session.state = order_service.state
        
        return {
            "message": f"Added {cart_item.itemName} to your order",
            "cart_id": session.cart_id,
            "cart_item": {
                "itemId": cart_item.itemId,
                "itemName": cart_item.itemName,
                "itemPrice": cart_item.itemPrice,
                "quantity": cart_item.quantity,
                "customizations": cart_item.customizations
            },
            "cart_summary": order_service.get_cart_summary()
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error adding item to order: {e}")
        raise HTTPException(status_code=500, detail="Failed to add item to order")

@app.put("/api/order/update-quantity")
async def update_item_quantity(request: UpdateQuantityRequest):
    """Update quantity of an item in the order"""
    try:
        # Get or create session with cart_id from request
        session = await get_session(request.cart_id)
        
        order_service = OrderService()
        order_service.cart = session.cart
        order_service.state = session.state
        
        success = order_service.update_item_quantity(request.item_name, request.quantity)
        if not success:
            raise HTTPException(status_code=404, detail="Item not found in cart")
        
        # Update session
        session.cart = order_service.cart
        
        return {
            "message": f"Updated {request.item_name} quantity to {request.quantity}",
            "cart_id": session.cart_id,
            "cart_summary": order_service.get_cart_summary()
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating item quantity: {e}")
        raise HTTPException(status_code=500, detail="Failed to update item quantity")

@app.delete("/api/order/remove-item")
async def remove_item_from_order(request: RemoveItemRequest):
    """Remove an item from the order"""
    try:
        # Get or create session with cart_id from request
        session = await get_session(request.cart_id)
        
        order_service = OrderService()
        order_service.cart = session.cart
        order_service.state = session.state
        
        success = order_service.remove_item_from_cart(request.item_name)
        if not success:
            raise HTTPException(status_code=404, detail="Item not found in cart")
        
        # Update session
        session.cart = order_service.cart
        
        return {
            "message": f"Removed {request.item_name} from your order",
            "cart_id": session.cart_id,
            "cart_summary": order_service.get_cart_summary()
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error removing item from order: {e}")
        raise HTTPException(status_code=500, detail="Failed to remove item from order")

@app.get("/api/order/cart")
async def get_cart(cart_id: Optional[str] = None):
    """Get current cart contents"""
    try:
        # Get or create session with cart_id from query parameter
        session = await get_session(cart_id)
        
        order_service = OrderService()
        order_service.cart = session.cart
        
        return {
            "cart_id": session.cart_id,
            "cart_items": [
                {
                    "itemId": item.itemId,
                    "itemName": item.itemName,
                    "itemPrice": item.itemPrice,
                    "quantity": item.quantity,
                    "customizations": item.customizations
                } for item in session.cart
            ],
            "total": order_service.calculate_total(),
            "cart_summary": order_service.get_cart_summary()
        }
    except Exception as e:
        logger.error(f"Error fetching cart: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch cart")

@app.delete("/api/order/clear")
async def clear_cart(cart_id: Optional[str] = None):
    """Clear the entire cart"""
    try:
        # Get or create session with cart_id from query parameter
        session = await get_session(cart_id)
        
        session.cart = []
        session.state = OrderState.TAKING_ORDER
        return {
            "message": "Cart cleared successfully",
            "cart_id": session.cart_id
        }
    except Exception as e:
        logger.error(f"Error clearing cart: {e}")
        raise HTTPException(status_code=500, detail="Failed to clear cart")

# Customer information endpoints
@app.post("/api/customer/info")
async def update_customer_info(request: CustomerInfoRequest):
    """Update customer information"""
    try:
        # Get or create session with cart_id from request
        session = await get_session(request.cart_id)
        
        session.customer_name = request.name
        session.customer_phone = request.phone
        
        return {
            "message": "Customer information updated successfully",
            "cart_id": session.cart_id,
            "customer_info": {
                "name": session.customer_name,
                "phone": session.customer_phone
            }
        }
    except Exception as e:
        logger.error(f"Error updating customer info: {e}")
        raise HTTPException(status_code=500, detail="Failed to update customer information")

# Order completion endpoint
@app.post("/api/order/complete")
async def complete_order(request: OrderCompletionRequest):
    """Complete the order"""
    try:
        # Get or create session with cart_id from request
        session = await get_session(request.cart_id)
        
        if not session.cart:
            raise HTTPException(status_code=400, detail="Cart is empty")
        
        if not session.customer_name:
            raise HTTPException(status_code=400, detail="Customer name is required")
        
        # Calculate total
        order_service = OrderService()
        order_service.cart = session.cart
        total = order_service.calculate_total()
        
        # Create order summary
        order_summary = {
            "order_id": str(uuid.uuid4()),
            "cart_id": session.cart_id,
            "customer_name": session.customer_name,
            "customer_phone": session.customer_phone,
            "items": [
                {
                    "itemId": item.itemId,
                    "itemName": item.itemName,
                    "itemPrice": item.itemPrice,
                    "quantity": item.quantity,
                    "customizations": item.customizations
                } for item in session.cart
            ],
            "total": total,
            "special_instructions": request.special_instructions,
            "timestamp": datetime.now().isoformat()
        }
        
        # Here you would typically send the order to your order processing system
        # For now, we'll just return the order summary
        
        # Clear the cart after successful order
        session.cart = []
        session.state = OrderState.TAKING_ORDER
        
        return {
            "message": "Order completed successfully",
            "order_summary": order_summary
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error completing order: {e}")
        raise HTTPException(status_code=500, detail="Failed to complete order")

# WebSocket endpoint for real-time chat
@app.websocket("/api/ws/{cart_id}")
async def websocket_endpoint(websocket: WebSocket, cart_id: str):
    """WebSocket endpoint for real-time communication"""
    await websocket.accept()
    websocket_connections[cart_id] = websocket
    
    try:
        # Get or create session
        session = await get_session(cart_id)
        
        # Send welcome message
        await websocket.send_json({
            "type": "message",
            "content": "Hello! Welcome to our pizza restaurant. I can help you with our menu, take your order, and manage customizations. How can I help you today?",
            "cart_id": cart_id
        })
        
        while True:
            # Receive message from client
            data = await websocket.receive_json()
            message = data.get("message", "")
            
            if not message:
                continue
            
            # Process the message (simplified AI response for now)
            response = await process_chat_message(message, session)
            
            # Send response back to client
            await websocket.send_json({
                "type": "message",
                "content": response,
                "cart_id": cart_id,
                "cart_summary": session.cart and OrderService().get_cart_summary() or None
            })
            
    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected for cart {cart_id}")
    except Exception as e:
        logger.error(f"WebSocket error for cart {cart_id}: {e}")
    finally:
        if cart_id in websocket_connections:
            del websocket_connections[cart_id]

async def process_chat_message(message: str, session: OrderSession) -> str:
    """Process chat message and return AI response"""
    # This is a simplified version - in a real implementation, you'd use an LLM
    message_lower = message.lower()
    
    if "menu" in message_lower or "what do you have" in message_lower:
        return menu_service.get_menu_summary()
    
    elif "search" in message_lower or "find" in message_lower:
        # Extract search terms (simplified)
        search_terms = message_lower.replace("search", "").replace("find", "").strip()
        if search_terms:
            matches = menu_service.fuzzy_search_items(search_terms, limit=3)
            if matches:
                result = f"Here are items matching '{search_terms}':\n"
                for i, match in enumerate(matches, 1):
                    item = match['item']
                    name = match['short_name'] or match['name']
                    price = item.get('price', 0)
                    result += f"{i}. {name} - ${price}\n"
                return result
            else:
                return f"I couldn't find any items matching '{search_terms}'. Would you like to see our full menu?"
        else:
            return "What would you like to search for?"
    
    elif "cart" in message_lower or "order" in message_lower:
        if session.cart:
            order_service = OrderService()
            order_service.cart = session.cart
            return order_service.get_cart_summary()
        else:
            return "Your cart is empty. What would you like to order?"
    
    elif "add" in message_lower and ("pizza" in message_lower or "item" in message_lower):
        return "I'd be happy to help you add items to your order! Please use the menu search to find specific items, or tell me what you're looking for."
    
    else:
        return "I'm here to help you with your pizza order! You can ask me about our menu, search for specific items, or manage your cart. What would you like to do?"

# Chat endpoint for non-WebSocket communication
@app.post("/chat", response_model=ChatResponse)
async def chat_endpoint(
    request: ChatMessage,
    session: OrderSession = Depends(get_session)
):
    """Chat endpoint for AI-powered conversation"""
    try:
        response = await process_chat_message(request.message, session)
        
        return ChatResponse(
            response=response,
            session_id=session.session_id,
            cart_summary=session.cart and OrderService().get_cart_summary() or None
        )
    except Exception as e:
        logger.error(f"Error processing chat message: {e}")
        raise HTTPException(status_code=500, detail="Failed to process message")

if __name__ == "__main__":
    uvicorn.run(
        "fastapi_pizza_agent:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )

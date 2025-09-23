"""
Pydantic models for FastAPI Pizza Ordering Agent
"""
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field
from datetime import datetime

# Request Models
class MenuSearchRequest(BaseModel):
    query: str = Field(..., description="Search query for menu items")
    limit: int = Field(5, description="Maximum number of results")
    min_score: float = Field(0.3, description="Minimum similarity score")

class AddItemRequest(BaseModel):
    item_id: str = Field(..., description="ID of the menu item")
    size: Optional[str] = Field(None, description="Size selection")
    quantity: int = Field(1, description="Quantity to add")
    customizations: List[str] = Field(default_factory=list, description="Customizations")

class UpdateQuantityRequest(BaseModel):
    item_name: str = Field(..., description="Name of the item to update")
    quantity: int = Field(..., description="New quantity")

class RemoveItemRequest(BaseModel):
    item_name: str = Field(..., description="Name of the item to remove")

class CustomerInfoRequest(BaseModel):
    name: str = Field(..., description="Customer name")
    phone: Optional[str] = Field(None, description="Customer phone number")
    address: Optional[str] = Field(None, description="Customer address")

class OrderCompletionRequest(BaseModel):
    payment_method: str = Field(..., description="Payment method")
    special_instructions: Optional[str] = Field(None, description="Special instructions")

class ChatMessage(BaseModel):
    message: str = Field(..., description="User message")
    session_id: Optional[str] = Field(None, description="Session ID")

# Response Models
class MenuSearchResponse(BaseModel):
    items: List[Dict[str, Any]]
    total_found: int

class CartItemResponse(BaseModel):
    itemId: str
    itemName: str
    itemPrice: float
    quantity: int
    customizations: List[Dict[str, Any]]

class CartResponse(BaseModel):
    cart_items: List[CartItemResponse]
    total: float
    cart_summary: str

class OrderSummaryResponse(BaseModel):
    order_id: str
    customer_name: str
    customer_phone: Optional[str]
    customer_address: Optional[str]
    items: List[CartItemResponse]
    total: float
    payment_method: str
    special_instructions: Optional[str]
    timestamp: str

class ChatResponse(BaseModel):
    response: str = Field(..., description="Agent response")
    session_id: str = Field(..., description="Session ID")
    cart_summary: Optional[str] = Field(None, description="Current cart summary")

class HealthResponse(BaseModel):
    status: str
    timestamp: str

class CustomerInfoResponse(BaseModel):
    name: str
    phone: Optional[str]
    address: Optional[str]

# WebSocket Models
class WebSocketMessage(BaseModel):
    type: str = Field(..., description="Message type")
    content: str = Field(..., description="Message content")
    session_id: str = Field(..., description="Session ID")
    cart_summary: Optional[str] = Field(None, description="Current cart summary")

class WebSocketRequest(BaseModel):
    message: str = Field(..., description="User message")
    session_id: Optional[str] = Field(None, description="Session ID")

"""
Data models for the pizza ordering system
"""
from enum import Enum
from typing import Dict, List, Optional, Any
from dataclasses import dataclass

class OrderState(Enum):
    TAKING_ORDER = "taking_order"
    CUSTOMIZING = "customizing"
    COLLECTING_ITEMS = "collecting_items"
    FINALIZING = "finalizing"

@dataclass
class CartItem:
    itemId: str
    itemName: str
    itemPrice: float
    quantity: int
    customizations: List[Dict[str, Any]]

@dataclass
class Customization:
    subItemName: str
    price: float
    quantity: int

@dataclass
class MenuItem:
    id: str
    name: str
    short_name: Optional[str]
    description: Optional[str]
    price: float
    category: str
    sizes: Optional[List[Dict[str, Any]]]
    toppings: Optional[List[str]]
    sauces: Optional[List[str]]

@dataclass
class OrderSummary:
    customer_name: str
    items: List[CartItem]
    total: float
    special_instructions: Optional[str]

class ConversationContext:
    def __init__(self):
        self.last_item_mentioned: Optional[str] = None
        self.last_size_asked: Optional[str] = None
        self.last_customization_asked: Optional[str] = None
        self.items_in_cart: List[str] = []
        self.current_question: Optional[str] = None
        self.recent_messages: List[str] = []
        self.recent_context: Dict[str, List[str]] = {
            "sizes_mentioned": [],
            "toppings_mentioned": [],
            "sauces_mentioned": [],
            "items_mentioned": []
        }

class OrderSession:
    def __init__(self):
        self.session_id: Optional[str] = None
        self.customer_name: Optional[str] = None
        self.customer_phone: Optional[str] = None
        self.cart: List[CartItem] = []
        self.state: OrderState = OrderState.TAKING_ORDER
        self.menu_data: Optional[List[MenuItem]] = None
        self.conversation_context: ConversationContext = ConversationContext()

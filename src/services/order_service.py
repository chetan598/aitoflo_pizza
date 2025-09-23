"""
Order service for handling cart and order operations
"""
import logging
from typing import List, Dict, Optional
from models.order_models import CartItem, OrderSummary, OrderState

logger = logging.getLogger(__name__)

class OrderService:
    def __init__(self):
        self.cart: List[CartItem] = []
        self.state: OrderState = OrderState.TAKING_ORDER
    
    def add_item_to_cart(self, item: Dict, size: Optional[str] = None, 
                        quantity: int = 1, customizations: List[str] = None) -> CartItem:
        """Add item to cart"""
        # Handle size selection
        selected_price = item.get('price', 0)
        display_name = item.get('short_name') or item.get('name', '')
        
        if item.get('sizes') and size:
            selected_size = None
            for s in item['sizes']:
                if s and s.get('name', '').lower() == size.lower():
                    selected_size = s
                    break
            
            if selected_size:
                selected_price = selected_size.get('price', 0)
                display_name += f" ({selected_size.get('name', '')})"
        
        # Create cart item
        cart_item = CartItem(
            itemId=str(item.get('id', '')),
            itemName=display_name,
            itemPrice=selected_price,
            quantity=quantity,
            customizations=[]
        )
        
        # Add customizations if provided
        if customizations:
            for custom in customizations:
                cart_item.customizations.append({
                    "subItemName": custom,
                    "price": 0,  # Assuming no extra charge for basic customizations
                    "quantity": 1
                })
        
        self.cart.append(cart_item)
        self.state = OrderState.COLLECTING_ITEMS
        return cart_item
    
    def update_item_quantity(self, item_name: str, quantity: int) -> bool:
        """Update quantity of an item in cart"""
        for item in self.cart:
            if item_name.lower() in item.itemName.lower():
                item.quantity = quantity
                return True
        return False
    
    def remove_item_from_cart(self, item_name: str) -> bool:
        """Remove item from cart"""
        for i, item in enumerate(self.cart):
            if item_name.lower() in item.itemName.lower():
                self.cart.pop(i)
                return True
        return False
    
    def get_cart_summary(self) -> str:
        """Get cart summary as string"""
        if not self.cart:
            return "Your cart is empty. What would you like to order?"
        
        cart_text = "Here's your current order:\n"
        for i, item in enumerate(self.cart, 1):
            total_price = item.itemPrice * item.quantity
            cart_text += f"{i}. {item.itemName} x{item.quantity} - ${total_price:.2f}\n"
        
        total = self.calculate_total()
        cart_text += f"\nTotal: ${total:.2f}"
        return cart_text
    
    def calculate_total(self) -> float:
        """Calculate total price of cart"""
        total = 0
        for item in self.cart:
            total += item.itemPrice * item.quantity
        return total
    
    def clear_cart(self):
        """Clear the cart"""
        self.cart = []
        self.state = OrderState.TAKING_ORDER
    
    def get_cart_items(self) -> List[CartItem]:
        """Get all cart items"""
        return self.cart.copy()
    
    def is_cart_empty(self) -> bool:
        """Check if cart is empty"""
        return len(self.cart) == 0

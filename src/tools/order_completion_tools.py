"""
Order completion and finalization tools
"""
import logging
from livekit.agents import function_tool
from services.order_service import OrderService
from services.utility_service import UtilityService
from models.order_models import OrderSummary

logger = logging.getLogger(__name__)

class OrderCompletionTools:
    def __init__(self, order_service: OrderService, session):
        self.order_service = order_service
        self.session = session
        self.utility = UtilityService()
    
    @function_tool
    async def complete_order(self, action: str, special_instructions: str = "") -> str:
        """
        Comprehensive order completion tool.
        Actions: 'place_order', 'get_order_summary', 'confirm_order', 'cancel_order'
        """
        if action == "place_order":
            if self.order_service.is_cart_empty():
                return "Your cart is empty. What would you like to order?"
            
            if not self.session.customer_name:
                return "I need your name to complete the order. What name should I use?"
            
            # Create order summary
            cart_items = self.order_service.get_cart_items()
            total = self.order_service.calculate_total()
            
            order_summary = OrderSummary(
                customer_name=self.session.customer_name,
                items=cart_items,
                total=total,
                special_instructions=special_instructions
            )
            
            # Format order summary
            order_text = f"Order for {order_summary.customer_name}:\n"
            for item in order_summary.items:
                total_price = item.itemPrice * item.quantity
                order_text += f"- {item.itemName} x{item.quantity} - {self.utility.format_price_for_speech(total_price)}\n"
            
            order_text += f"\nTotal: {self.utility.format_price_for_speech(order_summary.total)}"
            
            if order_summary.special_instructions:
                order_text += f"\nSpecial instructions: {order_summary.special_instructions}"
            
            # Simulate order placement
            self.session.state = "FINALIZING"
            self.order_service.clear_cart()  # Clear cart after order
            
            return f"Order placed successfully! {order_text}\n\nThank you for choosing us! Your order will be ready soon."
        
        elif action == "get_order_summary":
            if self.order_service.is_cart_empty():
                return "Your cart is empty. What would you like to order?"
            
            return self.order_service.get_cart_summary()
        
        elif action == "confirm_order":
            if self.order_service.is_cart_empty():
                return "Your cart is empty. What would you like to order?"
            
            total = self.order_service.calculate_total()
            summary = self.order_service.get_cart_summary()
            
            return f"Please confirm your order:\n\n{summary}\n\nIs this correct? Say 'yes' to place the order or 'no' to make changes."
        
        elif action == "cancel_order":
            self.order_service.clear_cart()
            self.session.customer_name = None
            self.session.state = "TAKING_ORDER"
            return "Order cancelled. How can I help you today?"
        
        return "I can help you complete your order. Try 'place_order', 'get_order_summary', 'confirm_order', or 'cancel_order'."

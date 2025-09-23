"""
Order item management tools
"""
import logging
from livekit.agents import function_tool
from services.order_service import OrderService
from services.menu_service import MenuService
from services.utility_service import UtilityService

logger = logging.getLogger(__name__)

class OrderTools:
    def __init__(self, order_service: OrderService, menu_service: MenuService):
        self.order_service = order_service
        self.menu_service = menu_service
        self.utility = UtilityService()
    
    @function_tool
    async def manage_order_items(self, action: str, item_name: str = "", size: str = "", 
                               quantity: int = 1, customizations: str = "") -> str:
        """
        Comprehensive order item management tool.
        Actions: 'add_item', 'update_quantity', 'remove_item', 'get_cart'
        """
        if action == "add_item":
            if not item_name:
                return "What would you like to add to your order?"
            
            item = self.menu_service.find_menu_item_by_name(item_name)
            if not item:
                return f"I don't see '{item_name}' on our menu. Would you like to see our available items?"
            
            # Parse customizations
            customizations_list = []
            if customizations:
                customizations_list = self.utility.parse_customization_input(customizations)
            
            # Add to cart
            cart_item = self.order_service.add_item_to_cart(
                item, size, quantity, customizations_list
            )
            
            total_price = cart_item.itemPrice * quantity
            return f"Perfect! I've added {cart_item.itemName} for {self.utility.format_price_for_speech(total_price)}. Anything else for your order?"
        
        elif action == "update_quantity":
            if self.order_service.is_cart_empty():
                return "Your cart is empty. What would you like to order?"
            
            if not self.utility.validate_quantity(quantity):
                return "Please provide a valid quantity (greater than 0)."
            
            success = self.order_service.update_item_quantity(item_name, quantity)
            if success:
                # Find the updated item to show new total
                for item in self.order_service.get_cart_items():
                    if item_name.lower() in item.itemName.lower():
                        total_price = item.itemPrice * quantity
                        return f"Updated {item.itemName} quantity to {quantity} for {self.utility.format_price_for_speech(total_price)}"
            else:
                current_items = [item.itemName for item in self.order_service.get_cart_items()]
                return f"I couldn't find '{item_name}' in your cart. Current items: {', '.join(current_items)}"
        
        elif action == "remove_item":
            if self.order_service.is_cart_empty():
                return "Your cart is empty. What would you like to order?"
            
            success = self.order_service.remove_item_from_cart(item_name)
            if success:
                return f"Removed {item_name} from your order. What else would you like?"
            else:
                current_items = [item.itemName for item in self.order_service.get_cart_items()]
                return f"I couldn't find '{item_name}' in your cart. Current items: {', '.join(current_items)}"
        
        elif action == "get_cart":
            return self.order_service.get_cart_summary()
        
        return "I can help you manage your order. Try 'add_item', 'update_quantity', 'remove_item', or 'get_cart'."

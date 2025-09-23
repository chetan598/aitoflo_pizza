"""
Customization management tools
"""
import logging
from livekit.agents import function_tool
from services.order_service import OrderService
from services.utility_service import UtilityService

logger = logging.getLogger(__name__)

class CustomizationTools:
    def __init__(self, order_service: OrderService):
        self.order_service = order_service
        self.utility = UtilityService()
    
    @function_tool
    async def manage_customizations(self, action: str, item_name: str = "", 
                                  customization_type: str = "", customization_name: str = "") -> str:
        """
        Comprehensive customization management tool.
        Actions: 'add_customization', 'remove_customization', 'list_available', 'get_customization_options'
        """
        if action == "add_customization":
            if not item_name or not customization_name:
                return "What item would you like to customize and what customization would you like to add?"
            
            # Find item in cart
            cart_items = self.order_service.get_cart_items()
            for item in cart_items:
                if item_name.lower() in item.itemName.lower():
                    # Add customization
                    if not item.customizations:
                        item.customizations = []
                    
                    item.customizations.append({
                        "subItemName": customization_name,
                        "price": 0,  # Assuming no extra charge
                        "quantity": 1
                    })
                    
                    return f"Added {customization_name} to {item.itemName}. Anything else you'd like to customize?"
            
            current_items = [item.itemName for item in cart_items]
            return f"I couldn't find '{item_name}' in your cart. Current items: {', '.join(current_items)}"
        
        elif action == "remove_customization":
            if not item_name or not customization_name:
                return "What item and customization would you like me to remove?"
            
            # Find item in cart and remove customization
            cart_items = self.order_service.get_cart_items()
            for item in cart_items:
                if item_name.lower() in item.itemName.lower():
                    if item.customizations:
                        for custom in item.customizations:
                            if custom and customization_name.lower() in custom.get('subItemName', '').lower():
                                item.customizations.remove(custom)
                                return f"Removed {customization_name} from {item.itemName}. What else would you like to change?"
            
            return f"I couldn't find that customization to remove. What would you like to change?"
        
        elif action == "list_available":
            if customization_type == "toppings":
                toppings = self.utility.get_available_toppings()
                return f"Available toppings: {', '.join(toppings)}"
            elif customization_type == "sauces":
                sauces = self.utility.get_available_sauces()
                return f"Available sauces: {', '.join(sauces)}"
            elif customization_type == "sizes":
                sizes = self.utility.get_available_sizes_list()
                return f"Available sizes: {', '.join(sizes)}"
            else:
                return "Available customizations: Toppings, Sauces, Sizes. What type would you like to see?"
        
        elif action == "get_customization_options":
            if not item_name:
                return "What item would you like customization options for?"
            
            # This would typically check against menu data, but for simplicity:
            options = []
            if "pizza" in item_name.lower():
                options.extend(["toppings", "sauces", "sizes"])
            elif "wings" in item_name.lower():
                options.extend(["sauces", "sizes"])
            elif "salad" in item_name.lower():
                options.extend(["toppings", "sauces"])
            
            if options:
                return f"Available customizations for {item_name}: {', '.join(options)}"
            else:
                return f"No customizations available for {item_name}"
        
        return "I can help you with customizations. Try 'add_customization', 'remove_customization', 'list_available', or 'get_customization_options'."

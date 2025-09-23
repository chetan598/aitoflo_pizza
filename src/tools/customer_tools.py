"""
Customer information management tools
"""
import logging
from livekit.agents import function_tool
from models.order_models import OrderSession

logger = logging.getLogger(__name__)

class CustomerTools:
    def __init__(self, session: OrderSession):
        self.session = session
    
    @function_tool
    async def manage_customer_info(self, action: str, name: str = "", phone: str = "") -> str:
        """
        Comprehensive customer information management tool.
        Actions: 'set_name', 'get_name', 'set_contact', 'get_contact_info'
        """
        if action == "set_name":
            if not name:
                return "What name should I use for your order?"
            
            self.session.customer_name = name
            return f"Perfect! I'll use {name} for your order. Is there anything else you'd like to add?"
        
        elif action == "get_name":
            if self.session.customer_name:
                return f"Your order is under the name {self.session.customer_name}."
            else:
                return "I don't have a name for your order yet. What name should I use?"
        
        elif action == "set_contact":
            if not phone:
                return "What phone number should I use for your order?"
            
            self.session.customer_phone = phone
            
            return f"Got it! I'll use {phone} for your order. Is there anything else you'd like to add?"
        
        elif action == "get_contact_info":
            info = []
            if self.session.customer_name:
                info.append(f"Name: {self.session.customer_name}")
            if self.session.customer_phone:
                info.append(f"Phone: {self.session.customer_phone}")
            
            if info:
                return "Your contact information:\n" + "\n".join(info)
            else:
                return "I don't have your contact information yet. What name and phone number should I use?"
        
        return "I can help you with customer information. Try 'set_name', 'get_name', 'set_contact', or 'get_contact_info'."

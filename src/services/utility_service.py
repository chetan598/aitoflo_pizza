"""
Utility service for common operations
"""
import logging
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)

class UtilityService:
    @staticmethod
    def format_price_for_speech(price: float) -> str:
        """Format price for speech"""
        return f"${price:.2f}"
    
    @staticmethod
    def clean_item_name(name: str) -> str:
        """Clean item name for display"""
        if not name:
            return ""
        return name.strip()
    
    @staticmethod
    def get_available_sizes(item: Dict) -> List[str]:
        """Get available sizes for an item"""
        if not item.get('sizes'):
            return []
        return [s.get('name', '') for s in item['sizes'] if s and s.get('name')]
    
    @staticmethod
    def get_available_toppings() -> List[str]:
        """Get available toppings"""
        return [
            "Pepperoni", "Sausage", "Mushrooms", "Onions", "Green Peppers",
            "Black Olives", "Extra Cheese", "Bacon", "Ham", "Pineapple"
        ]
    
    @staticmethod
    def get_available_sauces() -> List[str]:
        """Get available sauces"""
        return [
            "Buffalo", "BBQ", "Garlic Parm", "Honey Mustard", "Mild",
            "Hot", "Ranch", "Blue Cheese"
        ]
    
    @staticmethod
    def get_available_sizes_list() -> List[str]:
        """Get available sizes"""
        return ["Small", "Medium", "Large", "Extra Large"]
    
    @staticmethod
    def validate_item_name(item_name: str) -> bool:
        """Validate item name"""
        return bool(item_name and item_name.strip())
    
    @staticmethod
    def validate_quantity(quantity: int) -> bool:
        """Validate quantity"""
        return isinstance(quantity, int) and quantity > 0
    
    @staticmethod
    def parse_customization_input(customization_text: str) -> List[str]:
        """Parse customization input into list"""
        if not customization_text:
            return []
        
        # Split by common separators
        customizations = []
        for separator in [',', 'and', '&']:
            if separator in customization_text:
                customizations = [c.strip() for c in customization_text.split(separator)]
                break
        
        if not customizations:
            customizations = [customization_text.strip()]
        
        return [c for c in customizations if c]
    
    @staticmethod
    def generate_order_id() -> str:
        """Generate a simple order ID"""
        import uuid
        return f"ORD_{uuid.uuid4().hex[:8].upper()}"
    
    @staticmethod
    def format_order_summary(order_summary: Dict) -> str:
        """Format order summary for display"""
        summary = f"Order Summary for {order_summary.get('customer_name', 'Customer')}:\n\n"
        
        for item in order_summary.get('items', []):
            total_price = item.get('itemPrice', 0) * item.get('quantity', 1)
            summary += f"- {item.get('itemName', '')} x{item.get('quantity', 1)} - ${total_price:.2f}\n"
        
        summary += f"\nTotal: ${order_summary.get('total', 0):.2f}"
        summary += f"\nPayment: {order_summary.get('payment_method', 'cash')}"
        
        if order_summary.get('special_instructions'):
            summary += f"\nSpecial instructions: {order_summary['special_instructions']}"
        
        return summary

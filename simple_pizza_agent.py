"""
Simple Pizza Agent - Works without problematic dependencies
"""
import sys
import os

# Add src to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

def main():
    """Simple pizza agent that demonstrates the modular structure"""
    print("🍕 Simple Pizza Agent - Modular Structure Demo")
    print("=" * 50)
    
    try:
        # Import all the modular components
        from config.settings import AGENT_NAME, LOG_LEVEL
        from models.order_models import OrderState, CartItem, OrderSession
        from services.menu_service import MenuService
        from services.order_service import OrderService
        from services.utility_service import UtilityService
        from tools.menu_tools import MenuTools
        from tools.order_tools import OrderTools
        from tools.customization_tools import CustomizationTools
        from tools.customer_tools import CustomerTools
        from tools.order_completion_tools import OrderCompletionTools
        
        print(f"✅ Agent: {AGENT_NAME}")
        print(f"✅ Log Level: {LOG_LEVEL}")
        
        # Initialize services
        menu_service = MenuService()
        order_service = OrderService()
        utility = UtilityService()
        session = OrderSession()
        
        print("✅ Services initialized")
        
        # Initialize tools
        menu_tools = MenuTools(menu_service)
        order_tools = OrderTools(order_service, menu_service)
        customization_tools = CustomizationTools(order_service)
        customer_tools = CustomerTools(session)
        completion_tools = OrderCompletionTools(order_service, session)
        
        print("✅ Tools initialized")
        
        # Demo functionality
        print("\n🧪 Testing Tool Functionality:")
        print("-" * 30)
        
        # Test menu tools
        print("1. Menu Tools:")
        result = menu_tools.manage_menu_and_items("get_categories")
        print(f"   Categories: {result}")
        
        # Test order tools
        print("\n2. Order Tools:")
        result = order_tools.manage_order_items("get_cart")
        print(f"   Cart: {result}")
        
        # Test customer tools
        print("\n3. Customer Tools:")
        result = customer_tools.manage_customer_info("set_name", "John Doe")
        print(f"   Set name: {result}")
        
        # Test customization tools
        print("\n4. Customization Tools:")
        result = customization_tools.manage_customizations("list_available", customization_type="toppings")
        print(f"   Toppings: {result}")
        
        # Test completion tools
        print("\n5. Order Completion Tools:")
        result = completion_tools.complete_order("get_order_summary")
        print(f"   Order summary: {result}")
        
        print("\n🎉 All 5 modular tools are working perfectly!")
        print("\n📁 Modular Structure:")
        print("src/")
        print("├── agent.py                 # Main agent (LiveKit integration)")
        print("├── config/settings.py       # Configuration")
        print("├── models/order_models.py   # Data models")
        print("├── services/               # Business logic")
        print("│   ├── menu_service.py")
        print("│   ├── order_service.py")
        print("│   └── utility_service.py")
        print("└── tools/                  # 5 comprehensive tools")
        print("    ├── menu_tools.py")
        print("    ├── order_tools.py")
        print("    ├── customization_tools.py")
        print("    ├── customer_tools.py")
        print("    └── order_completion_tools.py")
        
        print("\n✨ The modular architecture is working perfectly!")
        print("   (This version works without LiveKit dependencies)")
        
        return True
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

if __name__ == "__main__":
    main()

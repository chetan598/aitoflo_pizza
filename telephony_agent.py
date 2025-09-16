
import asyncio
import json
import logging
import os
import aiohttp
from typing import Dict, List, Optional, Any
from enum import Enum
from dotenv import load_dotenv
from livekit.agents import (
    Agent, AgentSession, JobContext, WorkerOptions, cli, function_tool
)
from livekit.plugins import deepgram, openai, silero, elevenlabs

load_dotenv()
logger = logging.getLogger("jimmy_nenos_final_agent")

# ElevenLabs API Key
ELEVENLABS_API_KEY = "sk_06adde87eed40d0c21a06d7468e9f0171e80d6408f5afd09"

print("Starting Jimmy Neno's Final Agent...")
logger.info("Final agent initialization")

class OrderState(Enum):
    TAKING_ORDER = "taking_order"
    CUSTOMIZING = "customizing"
    COLLECTING_ITEMS = "collecting_items"  # New state for collecting multiple items
    FINALIZING = "finalizing"

current_state = OrderState.TAKING_ORDER
user_cart = []
current_item_customizing = None
current_size_selection = None  # Used for staged size selection
current_session = None  # Store current session for call termination
session_id = None  # Global session ID for cart management
customer_name = None  # Store customer name for order

# Conversation context to prevent repetitive questions
conversation_context = {
    "last_item_mentioned": None,
    "last_size_asked": None,
    "last_customization_asked": None,
    "items_in_cart": [],
    "current_question": None
}

def generate_session_id():
    """Generate a unique session ID"""
    import uuid
    return f"session_{uuid.uuid4().hex[:8]}"

# Supabase configuration
SUPABASE_URL = "https://obfjfvxwqmhrzsntxkfy.supabase.co/functions/v1/fetch_menu"
SUPABASE_ORDER_URL = "https://obfjfvxwqmhrzsntxkfy.supabase.co/functions/v1/post_order"
SUPABASE_HEADERS = {
    "Authorization": "Bearer sb_publishable_HNp8ZNUXDBMUtBKkHBkOQA_JwjTYZNB",
    "apikey": "sb_publishable_HNp8ZNUXDBMUtBKkHBkOQA_JwjTYZNB",
    "Content-Type": "application/json"
}
RESTAURANT_ID = "8f025919"  # Default restaurant ID

async def fetch_menu_from_api():
    """Fetch menu from Supabase API and return categorized structure"""
    try:
        print("🔄 Fetching menu from Supabase API...")
        print(f"🔗 API URL: {SUPABASE_URL}")
        print(f"🔑 Headers: {SUPABASE_HEADERS}")
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                SUPABASE_URL,
                headers=SUPABASE_HEADERS,
                json={"name": "Functions"}
            ) as response:
                print(f"📡 API Response Status: {response.status}")
                print(f"📡 Response Headers: {dict(response.headers)}")
                
                if response.status == 200:
                    data = await response.json()
                    print(f"✅ API Response Data Type: {type(data)}")
                    print(f"✅ API Response Data Keys: {list(data.keys()) if isinstance(data, dict) else 'Not a dict'}")
                    print(f"✅ Full API Response: {json.dumps(data, indent=2)}")
                    
                    # Transform the API response to the expected format
                    if "menu" in data and isinstance(data["menu"], list):
                        menu_items = data["menu"]
                        print(f"📊 Menu Items Count: {len(menu_items)}")
                        print(f"📊 First Menu Item: {menu_items[0] if menu_items else 'No items'}")
                        
                        # Group items by category
                        menu_by_category = {}
                        for item in menu_items:
                            if not item:  # Skip None items
                                continue
                            category = item.get("category", "Other")
                            if category not in menu_by_category:
                                menu_by_category[category] = []
                            menu_by_category[category].append(item)
                        
                        print(f"📊 Menu Categories: {list(menu_by_category.keys())}")
                        print(f"📊 Items per category: {[(cat, len(items)) for cat, items in menu_by_category.items()]}")
                        logger.info(f"Menu fetched successfully from API: {len(menu_items)} items across {len(menu_by_category)} categories")
                        return menu_by_category
                    else:
                        print("❌ Invalid menu structure in API response")
                        print(f"❌ Expected 'menu' key with list, got: {type(data.get('menu')) if isinstance(data, dict) else 'Not a dict'}")
                        return None
                else:
                    error_text = await response.text()
                    print(f"❌ API request failed with status {response.status}")
                    print(f"❌ Error response: {error_text}")
                    logger.error(f"❌ API request failed with status {response.status}: {error_text}")
                    return None
    except Exception as e:
        print(f"❌ Exception during API call: {str(e)}")
        print(f"❌ Exception type: {type(e).__name__}")
        import traceback
        print(f"❌ Traceback: {traceback.format_exc()}")
        logger.error(f"❌ Error fetching menu from API: {str(e)}")
        return None

async def fetch_raw_menu_from_api():
    """Fetch raw menu data from Supabase API (flat array structure)"""
    try:
        print("🔄 Fetching raw menu data from Supabase API...")
        print(f"🔗 API URL: {SUPABASE_URL}")
        print(f"🔑 Headers: {SUPABASE_HEADERS}")
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                SUPABASE_URL,
                headers=SUPABASE_HEADERS,
                json={"name": "Functions"}
            ) as response:
                print(f"📡 Raw API Response Status: {response.status}")
                
                if response.status == 200:
                    data = await response.json()
                    
                    if "menu" in data and isinstance(data["menu"], list):
                        menu_items = data["menu"]
                        print(f"📊 Raw Menu Items Count: {len(menu_items)}")
                        logger.info(f"Raw menu fetched successfully from API: {len(menu_items)} items")
                        return data  # Return the full data structure
                    else:
                        print("❌ Invalid menu structure in raw API response")
                        return None
                else:
                    error_text = await response.text()
                    print(f"❌ Raw API request failed with status {response.status}")
                    print(f"❌ Error response: {error_text}")
                    logger.error(f"❌ Raw API request failed with status {response.status}: {error_text}")
                    return None
    except Exception as e:
        print(f"❌ Exception during raw API call: {str(e)}")
        print(f"❌ Exception type: {type(e).__name__}")
        import traceback
        print(f"❌ Traceback: {traceback.format_exc()}")
        logger.error(f"❌ Error fetching raw menu from API: {str(e)}")
        return None

async def submit_order_to_api(order_data: dict) -> bool:
    """Submit order to Supabase API"""
    try:
        print("🔄 Submitting order to Supabase API...")
        print(f"🔗 Order API URL: {SUPABASE_ORDER_URL}")
        print(f"🔑 Headers: {SUPABASE_HEADERS}")
        print(f"📦 Order Data: {json.dumps(order_data, indent=2)}")
        
        # Validate order data before submission
        if not order_data.get('id'):
            print("❌ Order data missing ID")
            return False
        
        if not order_data.get('name'):
            print("❌ Order data missing customer name")
            return False
        
        if not order_data.get('order_json', {}).get('items'):
            print("❌ Order data missing items")
            return False
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                SUPABASE_ORDER_URL,
                headers=SUPABASE_HEADERS,
                json=order_data
            ) as response:
                print(f"📡 Order API Response Status: {response.status}")
                print(f"📡 Response Headers: {dict(response.headers)}")
                
                if response.status == 200:
                    data = await response.json()
                    print(f"✅ Order submitted successfully: {data}")
                    logger.info(f"Order submitted successfully: {order_data.get('id', 'Unknown ID')}")
                    return True
                else:
                    error_text = await response.text()
                    print(f"❌ Order submission failed with status {response.status}")
                    print(f"❌ Error response: {error_text}")
                    logger.error(f"❌ Order submission failed: {response.status} - {error_text}")
                    return False
    except Exception as e:
        print(f"❌ Exception during order submission: {str(e)}")
        print(f"❌ Exception type: {type(e).__name__}")
        import traceback
        traceback.print_exc()
        return False

def format_cart_for_api(cart: list, customer_name: str, phone_number: str = None) -> dict:
    """Format cart data for Supabase API submission"""
    import uuid
    from datetime import datetime
    
    # Generate unique order ID
    order_id = f"order_{uuid.uuid4().hex[:8]}"
    
    # Calculate total - itemPrice already includes all customizations
    total = 0
    for item in cart:
        if not item:
            continue
        item_price = item.get("itemPrice", 0)
        quantity = item.get("quantity", 1)
        item_total = item_price * quantity
        total += item_total
    
    # Format items for API
    api_items = []
    for item in cart:
        if not item:
            continue
            
        api_item = {
            "menu_item_id": item.get("itemId"),
            "name": item.get("itemName", ""),
            "quantity": item.get("quantity", 1)
        }
        
        # Add customizations if any
        customizations = item.get("customizations", [])
        if customizations:
            # Format customizations properly with full details
            formatted_customizations = []
            for c in customizations:
                if c and isinstance(c, dict):
                    custom_data = {
                        "name": c.get("subItemName", ""),
                        "group": c.get("subItemGroupName", ""),
                        "price": c.get("price", 0.0),
                        "quantity": c.get("quantity", 1)
                    }
                    formatted_customizations.append(custom_data)
            api_item["customizations"] = formatted_customizations
        
        api_items.append(api_item)
    
    # Create order data
    order_data = {
        "id": order_id,
        "name": customer_name,
        "mobile_no": phone_number or "Not provided",
        "order_json": {
            "items": api_items
        },
        "order_date": datetime.utcnow().isoformat() + "Z",
        "order_total": total,
        "restaurant_id": RESTAURANT_ID,
        "status": "pending"
    }
    
    return order_data

async def load_menu():
    """Always fetch fresh menu data from Supabase API - no caching"""
    global MENU, ITEM_CATALOG
    
    print("🔄 Fetching fresh menu data from Supabase API...")
    
    # Always fetch from API - no caching
    api_menu = await fetch_raw_menu_from_api()
    print(f"🔍 API Menu Result: {api_menu is not None}")
    
    if api_menu and "menu" in api_menu:
        # Convert new flat array structure to old categorized structure for compatibility
        MENU = convert_menu_to_categories(api_menu["menu"])
        total_items = sum(len(items) for items in MENU.values())
        print(f"✅ Menu loaded from Supabase API with {total_items} items across {len(MENU)} categories")
        print(f"📋 Categories: {', '.join(MENU.keys())}")
        
        # Rebuild ITEM_CATALOG with the loaded menu
        ITEM_CATALOG = build_item_catalog(MENU)
        print(f"📋 ITEM_CATALOG built with {len(ITEM_CATALOG)} items")
        print(f"📋 First few catalog items: {ITEM_CATALOG[:3]}")
        
        # Test menu access
        print("🧪 Testing menu access...")
        for category, items in MENU.items():
            print(f"  📁 {category}: {len(items)} items")
            if items:
                first_item = items[0]
                print(f"    🍕 First item: {first_item.get('name', 'No name')} (ID: {first_item.get('id', 'No ID')})")
    else:
        logger.error("Failed to load menu from Supabase API")
        MENU = {}
        ITEM_CATALOG = []
        print("ERROR: Could not load menu from API. Agent will not function properly.")

# Initialize empty menu - will be loaded asynchronously
MENU = {}
ITEM_CATALOG = []


def clean_item_name(name: str) -> str:
    if not name:  # Handle None or empty string
        return ""
    
    # Remove special characters and numbers
    clean_name = name.replace('*', '').replace('#', '').replace('1.', '').replace('2.', '').replace('3.', '').replace('4.', '').replace('5.', '').replace('6.', '').replace('7.', '').replace('8.', '').replace('9.', '').replace('0.', '')
    
    if clean_name.startswith("#"):
        return clean_name.split("-", 1)[-1].strip()
    
    # Remove extra spaces and return
    return ' '.join(clean_name.split())

def get_accent_friendly_clarification(context: str = "", options: list = None) -> str:
    """Generate accent-friendly clarification prompts that work across all English accents"""
    base_phrase = "I didn't hear that properly, could you please repeat?"
    
    if context and options:
        return f"{base_phrase} {context}: {', '.join(options)}"
    elif context:
        return f"{base_phrase} {context}"
    else:
        return base_phrase

def validate_item_exists(item_name: str) -> tuple[bool, Optional[Dict], str]:
    """Validate if an item exists in the menu and return detailed info"""
    item = get_menu_item_by_name(item_name)
    if not item:
        return False, None, f"Sorry, '{item_name}' is not available on our menu."
    
    return True, item, ""

def get_popular_suggestions() -> str:
    """Get popular menu items as suggestions with clean names"""
    suggestions = []
    
    # Get popular items from menu
    if hasattr(current_session, 'menu_data') and current_session.menu_data:
        for item in current_session.menu_data:
            if item and item.get('category') == 'Popular':
                short_name = item.get('short_name', item.get('name', ''))
                if short_name:
                    # Clean the name to remove any special characters, numbers, asterisks
                    clean_name = short_name.replace('*', '').replace('#', '').replace('1.', '').replace('2.', '').replace('3.', '').replace('4.', '').replace('5.', '').replace('6.', '').replace('7.', '').replace('8.', '').replace('9.', '').replace('0.', '')
                    clean_name = ' '.join(clean_name.split())  # Remove extra spaces
                    suggestions.append(clean_name)
                if len(suggestions) >= 3:  # Limit to 3 suggestions
                    break
    
    if suggestions:
        return f"Some popular items we have are: {', '.join(suggestions)}"
    else:
        return "Some popular items we have are: Wings, 12 Inch Pizza, Personal Pizza"

def update_conversation_context(item_name=None, size_asked=None, customization_asked=None, question=None):
    """Update conversation context to prevent repetitive questions"""
    global conversation_context
    
    if item_name:
        conversation_context["last_item_mentioned"] = item_name
    if size_asked:
        conversation_context["last_size_asked"] = size_asked
    if customization_asked:
        conversation_context["last_customization_asked"] = customization_asked
    if question:
        conversation_context["current_question"] = question
    
    # Update items in cart
    conversation_context["items_in_cart"] = [item.get("itemName", "") for item in user_cart if item]

def has_been_asked(question_type, item_name=None):
    """Check if we've already asked a specific question to prevent repetition"""
    global conversation_context
    
    if question_type == "size" and conversation_context["last_size_asked"] == item_name:
        return True
    elif question_type == "customization" and conversation_context["last_customization_asked"] == item_name:
        return True
    elif question_type == "item" and conversation_context["last_item_mentioned"] == item_name:
        return True
    
    return False

def get_current_item_id():
    """Get the current item ID that needs customization"""
    global current_item_customizing, user_cart
    
    if current_item_customizing:
        return current_item_customizing.get('id')
    
    # If no current item, get the most recent item in cart
    if user_cart:
        return user_cart[-1].get('itemId')
    
    return None

def format_price_for_speech(price: float) -> str:
    """Convert price to spoken format (e.g., 10.00 -> ten dollars)"""
    if price == 0:
        return "free"
    elif price < 1:
        cents = int(price * 100)
        return f"{cents} cents"
    elif price == int(price):
        # Whole number
        amount = int(price)
        if amount == 1:
            return "one dollar"
        else:
            return f"{amount} dollars"
    else:
        # Decimal
        dollars = int(price)
        cents = int((price - dollars) * 100)
        if dollars == 0:
            return f"{cents} cents"
        elif dollars == 1:
            return f"one dollar and {cents} cents"
        else:
            return f"{dollars} dollars and {cents} cents"

def validate_item_mentioned(item_name: str) -> tuple[bool, str]:
    """Immediately validate if an item exists when mentioned in conversation"""
    item = get_menu_item_by_name(item_name)
    if not item:
        suggestions = get_popular_suggestions()
        return False, f"Sorry, '{item_name}' is not available on our menu. {suggestions}. What would you like to order instead?"
    
    return True, f"Great! I have '{item.get('name', item_name)}' available. What size would you like?"

@function_tool
async def select_size(item_name: str, size_name: str) -> str:
    """Select a size for an item and add it to the cart"""
    global current_item_customizing, current_state, current_size_selection
    
    # Parse the item name to get the base name
    specifications = parse_item_specifications(item_name)
    base_item_name = specifications["base_name"]
    
    # Validate item exists in menu
    item_exists, item, error_message = validate_item_exists(base_item_name)
    if not item_exists:
        suggestions = get_popular_suggestions()
        return f"{error_message} {suggestions}. What would you like to order instead?"
    
    # Find matching size
    selected_size = None
    if item.get("sizes") and item["sizes"]:
        for size in item["sizes"]:
            if size.get('name', '').lower() == size_name.lower():
                selected_size = size
                break
        
        if not selected_size:
            # Size not found, show available sizes
            size_options = [f"{s.get('name', '')} ({format_price_for_speech(s.get('price', 0))})" for s in item["sizes"]]
            return f"Sorry, I don't have '{size_name}' available. Available sizes: {', '.join(size_options)}. What size would you like?"
    else:
        # No sizes, use base price
        selected_size = {"name": "Regular", "price": item.get("price", 0)}
    
    # Create cart item with selected size
    price = selected_size.get("price", item.get("price", 0))
    short_name = item.get("short_name")
    display_name = clean_item_name(short_name or item.get("name", "") or "")
    
    cart_item = {
        "itemId": item.get("id"),
        "itemName": display_name,
        "itemPrice": price,
        "quantity": 1,
        "selectedSize": selected_size.get("name", "Regular"),
        "customizations": []
    }
    
    # Add to cart
    user_cart.append(cart_item)
    current_item_customizing = item
    current_size_selection = selected_size
    
    # Check if item needs customizations
    customization_type = get_item_customization_type(base_item_name)
    
    if customization_type == 'sauce':
        set_state(OrderState.CUSTOMIZING)
        if base_item_name.lower() == 'wings':
            return f"Perfect! I've added {display_name} ({selected_size.get('name')} size) for {format_price_for_speech(price)}. What sauce would you like? We have Buffalo, BBQ, Garlic Parm, Honey Mustard, Mild, Hot, Ranch, or Blue Cheese. Just say the sauce name and I'll add it!"
        else:
            return f"Perfect! I've added {display_name} ({selected_size.get('name')} size) for ${price:.2f}. What sauce would you like? We have Buffalo, BBQ, Garlic Parm, Honey Mustard, Mild, Hot, Ranch, or Blue Cheese."
    elif customization_type == 'toppings':
        set_state(OrderState.CUSTOMIZING)
        return f"Great! I've added {display_name} ({selected_size.get('name')} size) for ${price:.2f}. What toppings would you like? We have Pepperoni, Italian Sausage, Ground Beef, Black Sheep Bacon, Ham, Salami, Mushrooms, Green Peppers, Red Peppers, Onions, Banana Peppers, Black Olives, Tomatoes, Extra Cheese, Mozzarella, or Cheddar."
    elif customization_type == 'both':
        set_state(OrderState.CUSTOMIZING)
        return f"Excellent! I've added {display_name} ({selected_size.get('name')} size) for ${price:.2f}. What toppings would you like, and what sauce would you prefer?"
    else:
        # No customizations needed
        set_state(OrderState.TAKING_ORDER)
        return f"Perfect! I've added {display_name} ({selected_size.get('name')} size) for ${price:.2f}. Anything else for your order?"

@function_tool
async def check_item_availability(item_name: str) -> str:
    """Check if an item is available on the menu and provide immediate feedback"""
    # Parse the item name to get the base name
    specifications = parse_item_specifications(item_name)
    base_item_name = specifications["base_name"]
    
    # Validate item exists in menu
    item_exists, item, error_message = validate_item_exists(base_item_name)
    
    if not item_exists:
        suggestions = get_popular_suggestions()
        return f"{error_message} {suggestions}. What would you like to order instead?"
    
    # Update conversation context
    update_conversation_context(item_name=base_item_name)
    
    # Item exists - provide confirmation and next steps
    item_name_display = clean_item_name(item.get('short_name') or item.get('name', ''))
    
    # Check what customizations are available
    customization_type = get_item_customization_type(base_item_name)
    
    if customization_type == 'sauce':
        update_conversation_context(customization_asked=base_item_name, question="sauce")
        return f"Great choice! {item_name_display} is available. What sauce would you like? We have Buffalo, BBQ, Garlic Parm, Honey Mustard, Mild, Hot, Ranch, or Blue Cheese."
    elif customization_type == 'toppings':
        update_conversation_context(customization_asked=base_item_name, question="toppings")
        return f"Perfect! {item_name_display} is available. What toppings would you like? We have Pepperoni, Italian Sausage, Ground Beef, Black Sheep Bacon, Ham, Salami, Mushrooms, Green Peppers, Red Peppers, Onions, Banana Peppers, Black Olives, Tomatoes, Extra Cheese, Mozzarella, or Cheddar."
    elif customization_type == 'both':
        update_conversation_context(customization_asked=base_item_name, question="both")
        return f"Excellent! {item_name_display} is available. What toppings would you like, and what sauce would you prefer?"
    else:
        # No customizations needed
        if item.get('sizes') and len(item['sizes']) > 1:
            update_conversation_context(size_asked=base_item_name, question="size")
            size_options = [f"{s.get('name', '')} (${s.get('price', 0):.2f})" for s in item['sizes']]
            return f"Perfect! {item_name_display} is available. What size would you like? Available sizes: {', '.join(size_options)}"
        else:
            # Only one size or no sizes - add directly
            return await lookup_add_item_to_cart(base_item_name)

def get_item_customization_type(item_name: str) -> str:
    """Determine what type of customizations an item should have based on actual live menu data"""
    item = get_menu_item_by_name(item_name)
    if not item or not item.get('customization'):
        return 'none'
    
    customization = item['customization']
    has_sauce = 'Sauce' in customization and customization['Sauce']
    has_toppings = 'Toppings' in customization and customization['Toppings']
    
    if has_sauce and has_toppings:
        return 'both'
    elif has_sauce:
        return 'sauce'
    elif has_toppings:
        return 'toppings'
    else:
        return 'none'

def build_item_catalog(menu: Dict[str, Any]) -> List[Dict[str, Any]]:
    catalog = []
    for category, items in menu.items():
        if not items:  # Skip empty categories
            continue
        for item in items:
            if not item:  # Skip None items
                continue
            short_name = item.get("short_name")
            name = clean_item_name(short_name or item.get("name", "") or "")
            catalog.append({
                "id": item.get("id"),
                "name": name
            })
    return catalog

# ITEM_CATALOG will be built after menu is loaded from API
ITEM_CATALOG = []

def convert_menu_to_categories(menu_data):
    """Convert new flat array menu structure to old categorized structure"""
    if not menu_data:
        return {}
    
    # Handle both direct array and wrapped object
    items = menu_data if isinstance(menu_data, list) else menu_data.get('menu', [])
    
    categories = {}
    for item in items:
        if not item:
            continue
        
        category = item.get('category', 'Other')
        if category not in categories:
            categories[category] = []
        categories[category].append(item)
    
    return categories

def get_complete_menu_context(menu_data):
    """Extract complete list of {id, name} pairs from menu data"""
    if not menu_data or 'menu' not in menu_data:
        return []
    
    menu_context = []
    for item in menu_data['menu']:
        if not item or not item.get('id') or not item.get('name'):
            continue
        
        short_name = item.get('short_name')
        name = clean_item_name(short_name or item.get('name', '') or '')
        if name:  # Only include items with valid names
            menu_context.append({
                "id": item.get('id'),
                "name": name
            })
    
    return menu_context

def get_menu_item_by_id(item_id: int) -> Optional[Dict]:
    """Get full menu item details by ID from current session menu data"""
    # First try session menu data
    if hasattr(current_session, 'menu_data') and current_session.menu_data:
        for item in current_session.menu_data:
            if item and item.get('id') == item_id:
                return item
    
    # Fallback to global menu
    if MENU:
        for category, items in MENU.items():
            for item in items:
                if item and item.get('id') == item_id:
                    return item
    
    return None

def get_menu_item_by_name(item_name: str) -> Optional[Dict]:
    """Get full menu item details by name from current session menu data with strict matching"""
    # First try session menu data
    if hasattr(current_session, 'menu_data') and current_session.menu_data:
        normalized_name = item_name.lower().strip()
        
        for item in current_session.menu_data:
            if not item:
                continue
                
            # Check exact name match
            if item.get('name', '').lower() == normalized_name:
                return item
            if item.get('short_name', '').lower() == normalized_name:
                return item
                
            # Check partial match only for very specific cases
            item_name_lower = item.get('name', '').lower()
            if normalized_name in item_name_lower and len(normalized_name) > 3:
                # Only match if the search term is substantial and contained in the item name
                return item
    
    # Fallback to global menu if session data not available
    if MENU:
        for category, items in MENU.items():
            for item in items:
                if not item:
                    continue
                if item.get('name', '').lower() == item_name.lower():
                    return item
                if item.get('short_name', '').lower() == item_name.lower():
                    return item
    
    return None

def find_menu_item_by_id(item_id: int) -> Optional[Dict]:
    if not hasattr(current_session, 'menu_data') or not current_session.menu_data:
        return None
    
    for item in current_session.menu_data:
            if not item:  # Skip None items
                continue
            if item.get("id") == item_id:
                return item
    return None

def find_menu_item_by_name(name: str) -> Optional[Dict]:
    want = name.lower().strip()
    if not hasattr(current_session, 'menu_data') or not current_session.menu_data:
        return None
    
    for item in current_session.menu_data:
            if not item:  # Skip None items
                continue
            n = clean_item_name(item.get("name", "") or "").lower()
            short_name = item.get("short_name")
            short = clean_item_name(short_name or "").lower() if short_name else ""
            if want == n or want == short or want in n or want in short:
                return item
    return None

def get_popular_items() -> str:
    """Get popular items - ONLY from loaded API menu, clean names only"""
    if not hasattr(current_session, 'menu_data') or not current_session.menu_data:
        return "I'm sorry, I'm having trouble loading our menu right now."
    
    # Filter popular items from session menu data
    popular = [item for item in current_session.menu_data if item and item.get('category') == 'Popular'][:4]
    result = "Here are our most popular items:\n"
    for item in popular:
        if not item:  # Skip None items
            continue
        short_name = item.get('short_name')
        it_name = clean_item_name(short_name or item.get('name', '') or '')
        
        # Skip items with empty names
        if not it_name:
            continue
            
        # Clean the name to remove any special characters, numbers, asterisks
        clean_name = it_name.replace('*', '').replace('#', '').replace('1.', '').replace('2.', '').replace('3.', '').replace('4.', '').replace('5.', '').replace('6.', '').replace('7.', '').replace('8.', '').replace('9.', '').replace('0.', '')
        clean_name = ' '.join(clean_name.split())  # Remove extra spaces
        
        result += f"{clean_name}\n"
    
    print(f"🍕 Popular items generated with {len([i for i in popular if i])} items from API")
    return result

def set_state(new_state: OrderState):
    global current_state
    current_state = new_state
    logger.info(f"State changed to: {new_state.value}")

def add_item_to_cart_safe(item: Dict, quantity: int = 1, customizations: List[Dict] = None, selected_size: str = None) -> tuple[bool, str]:
    """Safely add item to cart with duplicate prevention and validation"""
    global user_cart
    
    if not item:
        return False, "I couldn't find that item to add to your cart."
    
    item_id = item.get('id')
    if not item_id:
        return False, "Item ID not found."
    
    # Check for existing item in cart to prevent duplicates
    existing_item = None
    for cart_item in user_cart:
        if cart_item and cart_item.get('itemId') == item_id:
            existing_item = cart_item
            break
    
    if existing_item:
        # Item already exists, update quantity instead of adding duplicate
        existing_item['quantity'] += quantity
        short_name = item.get('short_name')
        display_name = clean_item_name(short_name or item.get('name', '') or '')
        return True, f"I've updated the quantity of {display_name} in your cart. You now have {existing_item['quantity']} of this item."
    
    # Create new cart item
    short_name = item.get('short_name')
    display_name = clean_item_name(short_name or item.get('name', '') or '')
    
    # Handle items with sizes or direct price
    if item.get('sizes') and item['sizes']:
        if selected_size:
            # Find the selected size
            for size in item['sizes']:
                if size.get('name', '').lower() == selected_size.lower():
                    price = size.get('price', 0)
                    break
            else:
                price = item['sizes'][0].get('price', 0)
        else:
            price = item['sizes'][0].get('price', 0)
    else:
        price = item.get('price', 0)
    
    cart_item = {
        "itemId": item_id,
        "itemName": display_name,
        "itemPrice": price,
        "quantity": quantity,
        "selectedSize": selected_size or (item['sizes'][0].get('name', 'Regular') if item.get('sizes') and item['sizes'] else 'Regular'),
        "customizations": customizations or [],
        "sessionId": session_id
    }
    
    user_cart.append(cart_item)
    return True, f"Added {display_name} to your cart."

def validate_cart_accuracy() -> tuple[bool, str]:
    """Validate that the cart is accurate and reflects what the user ordered"""
    global user_cart
    
    if not user_cart:
        return False, "Your cart is empty. Would you like to add something to your order?"
    
    # Check for any issues in the cart
    issues = []
    
    for item in user_cart:
        if not item:
            issues.append("An item in your cart is missing data")
            continue
            
        # Check if item still exists in menu
        item_id = item.get('itemId')
        if item_id:
            menu_item = get_menu_item_by_id(item_id)
            if not menu_item:
                issues.append(f"{item.get('itemName', 'Unknown item')} is no longer available")
        
        # Check for required customizations
        if menu_item and menu_item.get('customization'):
            required_customizations = []
            for group, options in menu_item['customization'].items():
                if options:  # If there are options available
                    required_customizations.append(group.lower())
            
            # Check if user has provided the required customizations
            provided_customizations = set()
            for custom in item.get('customizations', []):
                if custom and custom.get('subItemGroupName'):
                    provided_customizations.add(custom['subItemGroupName'].lower())
            
            missing_customizations = set(required_customizations) - provided_customizations
            if missing_customizations:
                issues.append(f"{item.get('itemName')} is missing required customizations: {', '.join(missing_customizations)}")
    
    if issues:
        return False, f"I found some issues with your order: {'; '.join(issues)}. Let me help you fix these."
    
    return True, "Cart validation passed"

def get_cart_summary_final() -> str:
    """Get final cart summary for confirmation - only called once at checkout"""
    global user_cart
    
    if not user_cart:
        return "Your cart is empty."
    
    # Validate cart accuracy first
    is_valid, validation_message = validate_cart_accuracy()
    if not is_valid:
        return validation_message
    
    # Build detailed summary
    summary_parts = []
    total_price = 0
    
    for item in user_cart:
        if not item:
            continue
            
        item_name = item.get('itemName', 'Unknown item')
        quantity = item.get('quantity', 1)
        item_price = item.get('itemPrice', 0)
        selected_size = item.get('selectedSize', '')
        customizations = item.get('customizations', [])
        
        # Build item description
        item_desc = f"{item_name}"
        if selected_size and selected_size != 'Regular':
            item_desc += f" ({selected_size})"
        
        if customizations:
            custom_list = []
            for custom in customizations:
                if custom and custom.get('subItemName'):
                    custom_list.append(custom['subItemName'])
            if custom_list:
                item_desc += f" with {', '.join(custom_list)}"
        
        item_desc += f" x{quantity}"
        summary_parts.append(item_desc)
        
        # Calculate price
        item_total = item_price * quantity
        for custom in customizations:
            if custom and custom.get('price'):
                item_total += custom['price'] * quantity
        total_price += item_total
    
    result = "Here's your order summary:\n"
    for part in summary_parts:
        result += f"{part}\n"
    
    result += f"\nTotal: {format_price_for_speech(total_price)}"
    return result

def get_current_requirements() -> List[str]:
    if not current_item_customizing:
        return []
    item = current_item_customizing
    if not item:  # Skip None items
        return []
    requirements = []
    if "customization" in item and item["customization"]:
        for group_name, options in item["customization"].items():
            if isinstance(options, list):
                requirements.append(f"{group_name} choice")
    return requirements

# --- Size selection (staged) ---
@function_tool
async def select_size_for_item(item_name: str, size_name: str, quantity: int = 1) -> str:
    global current_item_customizing, current_state, current_size_selection
    item = find_menu_item_by_name(item_name)
    if not item or "sizes" not in item or not item["sizes"]:
        return f"I couldn't find sizes for '{item_name}'."
    selected_size = None
    for size in item["sizes"]:
        if not size:  # Skip None sizes
            continue
        if size.get("name", "").lower() == size_name.lower():
            selected_size = size
            break
    if not selected_size:
        sizes_list = ", ".join([s.get("name", "") for s in item["sizes"] if s])
        short_name = item.get('short_name')
        item_name = clean_item_name(short_name or item.get('name', '') or '')
        return f"Available sizes for {item_name}: {sizes_list}"
    price = selected_size.get("price", 0)
    short_name = item.get("short_name")
    item_name = clean_item_name(short_name or item.get("name", "") or "")
    cart_item = {
        "itemId": item.get("id"),
        "itemName": item_name + f" ({selected_size.get('name', '')})",
        "itemPrice": price,
        "quantity": quantity,
        "customizations": []
    }
    custom_info = []
    if "customization" in item and item["customization"]:
        for group, options in item["customization"].items():
            if not options:  # Skip empty options
                continue
            if group.lower() == "sauce":
                # Sauce is array of objects with name and price
                sauce_list = []
                for o in options:
                    if isinstance(o, dict) and o.get("name"):
                        sauce_list.append(o["name"])
                    elif isinstance(o, str):
                        sauce_list.append(o)
                custom_info.append("Please select one sauce: " + ", ".join(sauce_list))
            elif group.lower() == "toppings":
                # Toppings is array of objects with name and price
                topping_list = []
                for o in options:
                    if isinstance(o, dict) and o.get("name"):
                        topping_list.append(f"{o['name']} (${o.get('price', 0):.2f})")
                    elif isinstance(o, str):
                        topping_list.append(o)
                custom_info.append("You can select multiple toppings: " + ", ".join(topping_list))
    user_cart.append(cart_item)
    current_item_customizing = item
    current_size_selection = None
    if custom_info:
        set_state(OrderState.CUSTOMIZING)
        return (
            f"Added item: {cart_item['itemName']} (price: ${cart_item['itemPrice']:.2f}, quantity: {quantity}).\n"
            + "\n".join(custom_info)
        )
    else:
        current_item_customizing = None
        set_state(OrderState.TAKING_ORDER)
        return f"Added item: {cart_item['itemName']} (price: ${cart_item['itemPrice']:.2f}, quantity: {quantity}).\nAnything else for your order?"

# --- Main item add function ---
def parse_item_specifications(item_name: str) -> dict:
    """Parse item specifications from user input to extract size, toppings, and sauces"""
    specifications = {
        'base_name': item_name,
        'size': None,
        'toppings': [],
        'sauces': []
    }
    
    item_lower = item_name.lower()
    
    # Parse size specifications
    size_keywords = ['small', 'medium', 'large', 'personal', '12 inch', 'half sheet', 'jumbo', 'regular', 'bowl', '10 count', '24 count']
    for size in size_keywords:
        if size in item_lower:
            specifications['size'] = size
            # Remove size from base name for better matching
            specifications['base_name'] = specifications['base_name'].replace(size, '').strip()
            break
    
    # Parse sauce specifications
    sauce_keywords = ['buffalo', 'bbq', 'garlic parm', 'honey mustard', 'mild', 'hot', 'ranch', 'blue cheese', 'sauce']
    for sauce in sauce_keywords:
        if sauce in item_lower:
            specifications['sauces'].append(sauce)
            # Remove sauce from base name for better matching
            specifications['base_name'] = specifications['base_name'].replace(sauce, '').strip()
    
    # Parse topping specifications
    topping_keywords = ['pepperoni', 'italian sausage', 'ground beef', 'bacon', 'ham', 'salami', 'mushrooms', 
                       'green peppers', 'red peppers', 'onions', 'banana peppers', 'black olives', 'tomatoes', 
                       'extra cheese', 'mozzarella', 'cheddar', 'chicken', 'beef', 'sausage']
    for topping in topping_keywords:
        if topping in item_lower:
            specifications['toppings'].append(topping)
            # Remove topping from base name for better matching
            specifications['base_name'] = specifications['base_name'].replace(topping, '').strip()
    
    # Special handling for compound items like "Buffalo Chicken Pizza"
    if 'buffalo chicken' in item_lower:
        specifications['base_name'] = 'Buffalo Chicken Pizza'
        # Buffalo Chicken Pizza has no customizations, so clear any parsed customizations
        specifications['toppings'] = []
        specifications['sauces'] = []
    elif 'pierogi' in item_lower:
        specifications['base_name'] = 'Pierogi Pizza'
    
    # Clean up base name
    specifications['base_name'] = specifications['base_name'].replace('with', '').replace('and', '').strip()
    
    return specifications

@function_tool
async def lookup_add_item_to_cart(item_name: str, quantity: int = 1) -> str:
    """Look up an item by name and add it to the cart with all customizations in one step"""
    global current_item_customizing, current_state, current_size_selection
    
    # Parse all customizations from the item name
    specifications = parse_item_specifications(item_name)
    base_item_name = specifications["base_name"]
    
    # Validate item exists in menu before proceeding
    item_exists, item, error_message = validate_item_exists(base_item_name)
    if not item_exists:
        suggestions = get_popular_suggestions()
        return f"{error_message} {suggestions}. What would you like to order instead?"
    
    # Handle size selection - ask for size if not specified and multiple sizes available
    selected_size = None
    if item.get("sizes") and item["sizes"]:
        if specifications['size']:
            # Find matching size
            for size in item["sizes"]:
                if size.get('name', '').lower() == specifications['size'].lower():
                    selected_size = size
                    break
            if not selected_size:
                # Size not found, ask for size
                size_options = [f"{s.get('name', '')} (${s.get('price', 0):.2f})" for s in item["sizes"]]
                return f"Great choice! {item.get('name', base_item_name)} is available. What size would you like? Available sizes: {', '.join(size_options)}"
        else:
            # No size specified, ask for size if multiple sizes available
            if len(item["sizes"]) > 1:
                size_options = [f"{s.get('name', '')} (${s.get('price', 0):.2f})" for s in item["sizes"]]
                return f"Perfect! {item.get('name', base_item_name)} is available. What size would you like? Available sizes: {', '.join(size_options)}"
            else:
                # Only one size available, use it
                selected_size = item["sizes"][0]
    else:
        # No sizes, use base price
        selected_size = {"name": "Regular", "price": item.get("price", 0)}
    
    # Calculate base price
    price = selected_size.get("price", item.get("price", 0))
    
    # Create cart item
    short_name = item.get("short_name")
    display_name = clean_item_name(short_name or item.get("name", "") or "")
    cart_item = {
        "itemId": item.get("id"),
        "itemName": display_name,
        "itemPrice": price,
        "quantity": quantity,
        "selectedSize": selected_size.get("name", "Regular"),
        "customizations": []
    }
    
    # Process all customizations at once
    customizations_added = []
    if "customization" in item and item["customization"]:
        # Process sauces - only if item has sauce customization available
        if item.get("customization") and "Sauce" in item["customization"] and specifications['sauces']:
            available_sauces = item["customization"]["Sauce"]
            for sauce_name in specifications['sauces']:
                # Find matching sauce
                for sauce in available_sauces:
                    if isinstance(sauce, dict) and sauce.get('name', '').lower() == sauce_name.lower():
                        customization = {
                            "optionId": f"sauce_{sauce_name.lower().replace(' ', '_')}",
                            "subItemName": sauce.get('name', sauce_name),
                            "subItemGroupName": "Sauce",
                            "price": sauce.get('price', 0),
                            "quantity": 1
                        }
                        cart_item["customizations"].append(customization)
                        cart_item["itemPrice"] += sauce.get('price', 0)  # Add sauce price to total
                        customizations_added.append(f"sauce: {sauce.get('name', sauce_name)}")
                        break
        
        # Process toppings - only if item has toppings customization available
        if item.get("customization") and "Toppings" in item["customization"] and specifications['toppings']:
            available_toppings = item["customization"]["Toppings"]
            for topping_name in specifications['toppings']:
                # Find matching topping
                for topping in available_toppings:
                    if isinstance(topping, dict) and topping.get('name', '').lower() == topping_name.lower():
                        customization = {
                            "optionId": f"topping_{topping_name.lower().replace(' ', '_')}",
                            "subItemName": topping.get('name', topping_name),
                            "subItemGroupName": "Toppings",
                            "price": topping.get('price', 0),
                            "quantity": 1
                        }
                        cart_item["customizations"].append(customization)
                        cart_item["itemPrice"] += topping.get('price', 0)  # Add topping price to total
                        customizations_added.append(f"topping: {topping.get('name', topping_name)}")
                        break
    
    # Add to cart
    user_cart.append(cart_item)
    
    # Calculate total price including customizations
    total_price = cart_item["itemPrice"] * quantity
    
    # Build confirmation message
    response_parts = [f"Perfect! I've added {quantity} {cart_item['itemName']}"]
    
    if selected_size.get("name") != "Regular":
        response_parts.append(f"({selected_size.get('name')} size)")
    
    if customizations_added:
        response_parts.append(f"with {', '.join(customizations_added)}")
    
    response_parts.append(f"for ${total_price:.2f} total")
    response_parts.append("What else would you like to order?")
    
    # Set state to taking order
    set_state(OrderState.TAKING_ORDER)
    current_item_customizing = None
        
    return " ".join(response_parts)

@function_tool
async def select_size_for_item(item_id: int, size_name: str) -> str:
    """Select size for an item that has multiple size options"""
    global current_item_customizing, current_state, current_size_selection
    
    if not user_cart:
        return "I don't see any items in your cart to customize. Would you like to add something first?"
    
    # Find the item in cart
    target_item = None
    for item in reversed(user_cart):
        if not item:
            continue
        if int(item.get("itemId", 0)) == int(item_id):
            target_item = item
            break
    
    if not target_item:
        return "I don't see that item in your cart. Would you like to add something first?"
    
    # Get the menu item to validate size
    item_dict = get_menu_item_by_id(int(item_id))
    if not item_dict or not item_dict.get("sizes"):
        return "This item doesn't have size options."
    
    # Find the selected size
    selected_size = None
    for size in item_dict["sizes"]:
        if size.get("name", "").lower() == size_name.lower():
            selected_size = size
            break
    
    if not selected_size:
        available_sizes = [size.get("name", "") for size in item_dict["sizes"]]
        return f"Sorry, '{size_name}' is not available for this item. Available sizes are: {', '.join(available_sizes)}"
    
    # Update the item with the selected size
    target_item["itemPrice"] = selected_size.get("price", 0)
    target_item["selectedSize"] = selected_size.get("name", "")
    
    # Clear size selection state
    current_size_selection = None
    current_item_customizing = None
    set_state(OrderState.TAKING_ORDER)
    
    return f"Perfect! I've set the size to {selected_size.get('name', '')} for your {target_item.get('itemName', 'item')}. The price is now ${selected_size.get('price', 0):.2f}. Is there anything else you'd like to order?"

@function_tool
async def add_sauce_to_wings(sauce_name: str) -> str:
    """DEDICATED FUNCTION: Add sauce specifically to wings - bulletproof version"""
    global user_cart, current_state
    
    try:
        # Find wings in cart (item ID 1)
        wings_item = None
        for item in user_cart:
            if item and item.get('itemId') == 1:  # Wings have ID 1
                wings_item = item
                break
        
        if not wings_item:
            return "I don't see any wings in your cart to add sauce to. Please add wings first."
        
        # Normalize sauce name
        sauce_name = sauce_name.strip().lower()
        sauce_mappings = {
            'mild': 'Mild',
            'buffalo': 'Buffalo', 
            'bbq': 'BBQ',
            'garlic parm': 'Garlic Parm',
            'garlic parmesan': 'Garlic Parm',
            'honey mustard': 'Honey Mustard',
            'hot': 'Hot',
            'ranch': 'Ranch',
            'blue cheese': 'Blue Cheese'
        }
        
        # Get the proper sauce name
        proper_sauce_name = sauce_mappings.get(sauce_name, sauce_name.title())
        
        # Remove any existing sauce from wings
        if 'customizations' not in wings_item:
            wings_item['customizations'] = []
        
        # Remove old sauce
        wings_item['customizations'] = [
            c for c in wings_item['customizations'] 
            if c and c.get('subItemGroupName') != 'Sauce'
        ]
        
        # Add new sauce
        sauce_customization = {
            "optionId": f"sauce_{sauce_name.replace(' ', '_')}",
            "subItemName": proper_sauce_name,
            "subItemGroupName": "Sauce",
            "price": 0.0,
            "quantity": 1
        }
        
        wings_item['customizations'].append(sauce_customization)
        
        # Update conversation context
        update_conversation_context(customization_asked="wings")
        
        return f"Perfect! I've added {proper_sauce_name} sauce to your wings. Is there anything else you'd like to order?"
        
    except Exception as e:
        logger.error(f"Error adding sauce to wings: {str(e)}")
        return f"Sorry, I had trouble adding the sauce. Let me try again - what sauce would you like for your wings?"

@function_tool
async def add_sauce(item_id: int, sauce_name: str) -> str:
    """Add sauce to an item - handles string-based sauce options"""
    global current_item_customizing, current_state
    
    try:
        # Normalize the sauce name to handle variations
        normalized_sauce = normalize_sauce_name(sauce_name)
        
        if not user_cart:
            return "I don't see any items in your cart to customize. Would you like to add something first?"
        
        # First validate that the item exists in the menu
        item_dict = get_menu_item_by_id(int(item_id))
        if not item_dict:
            return f"Sorry, I couldn't find that item in our menu. Please try adding a valid item first."
        
        # Check if the item actually has sauce customizations available
        if not item_dict.get("customization", {}).get("Sauce"):
            return f"Sorry, {item_dict.get('name', 'this item')} doesn't have sauce options available."
        
        # Find the item in cart - prioritize exact item_id match
        target_item = None
        if user_cart:
            # First try to find by exact item_id match
            for item in reversed(user_cart):
                if not item or not isinstance(item, dict):  # Skip None items and non-dict items
                    continue
                if int(item.get("itemId", 0)) == int(item_id):
                    target_item = item
                    break
            
            # If not found by ID, look for items that need customization
            if not target_item:
                for item in reversed(user_cart):
                    if not item or not isinstance(item, dict):  # Skip None items and non-dict items
                        continue
                    # Check if this item needs sauce customization
                    item_dict = get_menu_item_by_id(int(item.get("itemId", 0)))
                    if item_dict and item_dict.get("customization", {}).get("Sauce"):
                        target_item = item
                        item_id = item.get('itemId', 0)
                        break
            
            # If still not found, use the most recent item (last in cart)
            if not target_item:
                target_item = user_cart[-1] if user_cart else None  # Get the last (most recent) item
                if not target_item:
                    return f"I don't see any items in your cart to customize. Would you like to add something first?"
                # Update item_id to match the actual cart item
                item_id = target_item.get('itemId', 0)
        
        if not target_item:
            return f"I don't see any items in your cart to customize. Would you like to add something first?"
        
        # Check if sauce is valid for this item
        item_dict = get_menu_item_by_id(int(item_id))
        if item_dict and "customization" in item_dict and item_dict["customization"]:
            available_sauces = item_dict["customization"].get("Sauce", [])
            
            if not available_sauces:
                return f"Sorry, this item doesn't have sauce options. This item has toppings instead. Would you like to add toppings instead?"
            
            # Extract sauce names for comparison and display
            sauce_names = []
            sauce_names_lower = []
            for sauce in available_sauces:
                if isinstance(sauce, dict):
                    sauce_name = sauce.get('name', '')
                    sauce_names.append(sauce_name)
                    sauce_names_lower.append(sauce_name.lower())
        else:
                    sauce_name = str(sauce)
                    sauce_names.append(sauce_name)
                    sauce_names_lower.append(sauce_name.lower())
        
        if normalized_sauce not in sauce_names_lower:
                return f"Sorry, '{sauce_name}' is not available for this item. Available sauces are: {', '.join(sauce_names)}"
        else:
            return f"Sorry, this item doesn't have sauce options. This item has toppings instead. Would you like to add toppings instead?"
        
        # Remove any existing sauce (only one sauce allowed)
        old_customizations = target_item.get("customizations", []).copy()
        target_item["customizations"] = [
            c for c in target_item.get("customizations", []) 
            if c and c.get("subItemGroupName", "").lower() != "sauce"
        ]
        
        # Find the original sauce name for proper display
        original_sauce_name = sauce_name  # Use the original input
        for sauce in available_sauces:
            if isinstance(sauce, dict):
                if sauce.get('name', '').lower() == normalized_sauce:
                    original_sauce_name = sauce.get('name', sauce_name)
                    break
            else:
                if str(sauce).lower() == normalized_sauce:
                    original_sauce_name = str(sauce)
                    break
        
        # Add the new sauce (sauce is included in base price, no additional charge)
        customization = {
            "optionId": f"sauce_{normalized_sauce.lower().replace(' ', '_')}",
            "subItemName": original_sauce_name,
            "subItemGroupName": "Sauce",
            "price": 0.0,  # Sauce is free - included in base price
            "quantity": 1
        }
        if "customizations" not in target_item:
            target_item["customizations"] = []
        target_item["customizations"].append(customization)
        
        # Check if all customizations are complete
        if not item_dict or "customization" not in item_dict:
            current_item_customizing = None
            set_state(OrderState.TAKING_ORDER)
            return f"Perfect! I've added {normalized_sauce} sauce to your {target_item['itemName']}. Is there anything else you'd like to order?"
        
        # Check if all required customizations are done
        required_groups = list(item_dict.get("customization", {}).keys())
        completed_groups = set()
        
        for group in required_groups:
            group_lower = group.lower()
            
            if group_lower == "sauce":
                sauce_customs = [c for c in target_item.get("customizations", []) if c and c.get("subItemGroupName", "").lower() == "sauce"]
                if len(sauce_customs) == 1:
                    completed_groups.add(group_lower)
            elif group_lower == "toppings":
                # Toppings are optional, so consider complete if we have any
                topping_customs = [c for c in target_item.get("customizations", []) if c and c.get("subItemGroupName", "").lower() == "toppings"]
                if topping_customs:
                    completed_groups.add(group_lower)
        
        if len(completed_groups) == len(required_groups):
            current_item_customizing = None
            
            # Check if there are other items that need customizations
            items_needing_customization = check_items_need_customization()
            if items_needing_customization:
                set_state(OrderState.COLLECTING_ITEMS)
                return f"Excellent! I've added {normalized_sauce} sauce to your {target_item.get('itemName', 'item')}. I'll help you customize your other items. What else would you like to add?"
            else:
                set_state(OrderState.TAKING_ORDER)
                return f"Excellent! I've added {normalized_sauce} sauce to your {target_item.get('itemName', 'item')}. What else can I get for you today?"
        else:
            remaining = [g for g in required_groups if g.lower() not in completed_groups]
            print(f"Remaining groups: {remaining}")
            if remaining:
                return f"Great choice! I've added {normalized_sauce} sauce. You still need to choose: {', '.join(remaining)}. What would you like?"
            else:
                return f"Perfect! I've added {normalized_sauce} sauce. Any other customizations for your {target_item['itemName']}?"
                
    except Exception as e:
        logger.error(f"Error adding sauce {sauce_name} to item {item_id}: {str(e)}")
        return f"I'm sorry, I encountered an error adding the sauce. Let me help you try again. What sauce would you like?"

@function_tool
async def add_topping(item_id: int, topping_name: str, quantity: int = 1) -> str:
    """Add topping to an item - handles object-based topping options"""
    global current_item_customizing, current_state
    if not user_cart:
        return "I don't see any items in your cart to customize. Would you like to add something first?"
    
    # First validate that the item exists in the menu
    item_dict = get_menu_item_by_id(int(item_id))
    if not item_dict:
        return f"Sorry, I couldn't find that item in our menu. Please try adding a valid item first."
    
    # Check if the item actually has topping customizations available
    if not item_dict.get("customization", {}).get("Toppings"):
        return f"Sorry, {item_dict.get('name', 'this item')} doesn't have topping options available."
    
    # Find the item in cart - prioritize exact item_id match
    target_item = None
    if user_cart:
        # First try to find by exact item_id match
        for item in reversed(user_cart):
            if not item or not isinstance(item, dict):  # Skip None items and non-dict items
                continue
            if int(item.get("itemId", 0)) == int(item_id):
                target_item = item
                break
        
        # If not found by ID, look for items that need customization
        if not target_item:
            for item in reversed(user_cart):
                if not item or not isinstance(item, dict):  # Skip None items and non-dict items
                    continue
                # Check if this item needs topping customization
                item_dict = get_menu_item_by_id(int(item.get("itemId", 0)))
                if item_dict and item_dict.get("customization", {}).get("Toppings"):
                    target_item = item
                    item_id = item.get('itemId', 0)
                    break
        
        # If still not found, use the most recent item (last in cart)
        if not target_item:
            target_item = user_cart[-1] if user_cart else None  # Get the last (most recent) item
            if not target_item:
                return f"I don't see any items in your cart to customize. Would you like to add something first?"
            # Update item_id to match the actual cart item
            item_id = target_item.get('itemId', 0)
    
    if not target_item:
        return f"I don't see any items in your cart to customize. Would you like to add something first?"
    
    # Get the correct price from menu for toppings
    item_dict = get_menu_item_by_id(int(item_id))
    custom_price = 0.0
    
    if item_dict and "customization" in item_dict and item_dict["customization"]:
        topping_options = item_dict["customization"].get("Toppings", [])
        for option in topping_options:
            if not option:  # Skip None options
                continue
            if isinstance(option, dict) and option.get("name", "").lower() == topping_name.lower():
                custom_price = option.get("price", 0.0)
                break
    
    # Check if topping already exists
    existing_toppings = [c for c in target_item.get("customizations", []) 
                        if c and c.get("subItemGroupName", "").lower() == "toppings" 
                        and c.get("subItemName", "").lower() == topping_name.lower()]
    
    if existing_toppings:
        # Update quantity of existing topping
        existing_toppings[0]["quantity"] = existing_toppings[0].get("quantity", 1) + quantity
        logger.info(f"Updated quantity for existing topping: {topping_name}")
        return f"Updated quantity for {topping_name} topping. Current quantity: {existing_toppings[0]['quantity']}"
    
    # Find the original topping name for proper display
    original_topping_name = topping_name  # Use the original input
    if item_dict and "customization" in item_dict and item_dict["customization"]:
        topping_options = item_dict["customization"].get("Toppings", [])
        for option in topping_options:
            if not option:  # Skip None options
                continue
            if isinstance(option, dict) and option.get("name", "").lower() == topping_name.lower():
                original_topping_name = option.get("name", topping_name)
                break
    
    # Add the new topping
    customization = {
        "optionId": f"topping_{topping_name.lower().replace(' ', '_')}",
        "subItemName": original_topping_name,
        "subItemGroupName": "Toppings",
        "price": custom_price,
        "quantity": quantity
    }
    if "customizations" not in target_item:
        target_item["customizations"] = []
    target_item["customizations"].append(customization)
    target_item["itemPrice"] = target_item.get("itemPrice", 0) + custom_price * quantity
    
    logger.info(f"Added topping: {topping_name} (${custom_price:.2f}) to item {item_id}")
    
    # Check if all customizations are complete
    if not item_dict or "customization" not in item_dict:
        current_item_customizing = None
        set_state(OrderState.TAKING_ORDER)
        return f"Perfect! I've added {topping_name} to your {target_item.get('itemName', 'item')}. Is there anything else you'd like to order?"
    
    # Check if all required customizations are done
    required_groups = list(item_dict.get("customization", {}).keys())
    completed_groups = set()
    
    for group in required_groups:
        group_lower = group.lower()
        if group_lower == "sauce":
            sauce_customs = [c for c in target_item.get("customizations", []) if c and c.get("subItemGroupName", "").lower() == "sauce"]
            if len(sauce_customs) == 1:
                completed_groups.add(group_lower)
        elif group_lower == "toppings":
            # Toppings are optional, so consider complete if we have any
            topping_customs = [c for c in target_item.get("customizations", []) if c and c.get("subItemGroupName", "").lower() == "toppings"]
            if topping_customs:
                completed_groups.add(group_lower)
    
    if len(completed_groups) == len(required_groups):
        current_item_customizing = None
        
        # Check if there are other items that need customizations
        items_needing_customization = check_items_need_customization()
        if items_needing_customization:
            set_state(OrderState.COLLECTING_ITEMS)
            return f"Excellent! I've added {topping_name} to your {target_item.get('itemName', 'item')}. I'll help you customize your other items. What else would you like to add?"
        else:
            set_state(OrderState.TAKING_ORDER)
            return f"Excellent! I've added {topping_name} to your {target_item.get('itemName', 'item')}. What else can I get for you today?"
    else:
        remaining = [g for g in required_groups if g.lower() not in completed_groups]
        if remaining:
            return f"Great choice! I've added {topping_name}. You still need to choose: {', '.join(remaining)}. What would you like?"
        else:
            return f"Perfect! I've added {topping_name}. Any other customizations for your {target_item.get('itemName', 'item')}?"

@function_tool
async def delete_customization(item_id: int, option_id: str) -> str:
    """Remove a specific customization from an item"""
    for item in user_cart:
        if not item:  # Skip None items
            continue
        if int(item.get("itemId", 0)) == int(item_id):
            for custom in item.get("customizations", []):
                if not custom:  # Skip None customizations
                    continue
                if str(custom.get("optionId", "")) == str(option_id):
                    removed_name = custom.get("subItemName", "customization")
                    removed_price = custom.get("price", 0) * custom.get("quantity", 1)
                    item["customizations"].remove(custom)
                    item["itemPrice"] = item.get("itemPrice", 0) - removed_price
                    logger.info(f"Removed customization: {removed_name} from item {item_id}")
                    return f"Perfect! I've removed {removed_name} from your {item.get('itemName', 'item')}. Is there anything else you'd like to change?"
    return "I couldn't find that customization to remove. Let me know what you'd like to change."

@function_tool
async def delete_item(item_id: int) -> str:
    """Remove an entire item from the cart"""
    global user_cart
    for i, item in enumerate(user_cart):
        if not item:  # Skip None items
            continue
        if int(item.get("itemId", 0)) == int(item_id):
            removed_item = user_cart.pop(i)
            logger.info(f"Removed item: {removed_item.get('itemName', 'Unknown')} from cart")
            return f"Got it! I've removed the {removed_item.get('itemName', 'item')} from your order. What else can I help you with?"
    return "I couldn't find that item in your cart. Let me know what you'd like to remove."

@function_tool
async def remove_customization_by_name(item_id: int, customization_name: str) -> str:
    """Remove a customization by name (more user-friendly)"""
    for item in user_cart:
        if not item:  # Skip None items
            continue
        if int(item.get("itemId", 0)) == int(item_id):
            for customization in item.get("customizations", []):
                if not customization:  # Skip None customizations
                    continue
                if customization.get("subItemName", "").lower() == customization_name.lower():
                    removed_name = customization.get("subItemName", "customization")
                    removed_price = customization.get("price", 0) * customization.get("quantity", 1)
                    item["customizations"].remove(customization)
                    item["itemPrice"] = item.get("itemPrice", 0) - removed_price
                    logger.info(f"Removed customization: {removed_name} from item {item_id}")
                    return f"Perfect! I've removed {removed_name} from your {item.get('itemName', 'item')}. Is there anything else you'd like to change?"
    return f"I couldn't find {customization_name} on that item. Let me know what you'd like to remove."

@function_tool
async def clear_cart() -> str:
    """Clear the entire cart"""
    global user_cart, current_state
    user_cart = []
    current_state = OrderState.TAKING_ORDER
    logger.info("Cart cleared completely")
    return "I've cleared your entire order. What would you like to start fresh with today?"

@function_tool
async def get_recommendations() -> str:
    """Get popular items - only use when specifically asked for recommendations, not for general menu requests"""
    return get_popular_items()

@function_tool
async def get_complete_menu_list() -> str:
    """Get complete list of all menu items with just names and IDs"""
    if not hasattr(current_session, 'menu_data') or not current_session.menu_data:
        return "I'm sorry, I'm having trouble loading our menu right now. Please try again in a moment."
    
    # Build complete menu context
    menu_context = []
    for item in current_session.menu_data:
        if not item or not item.get('id') or not item.get('name'):
            continue
        short_name = item.get('short_name')
        name = clean_item_name(short_name or item.get('name', '') or '')
        if name:
            menu_context.append({
                "id": item.get('id'),
                "name": name
            })
    
    if not menu_context:
        return "I don't have any menu items available right now."
    
    # Format as a readable list
    result = f"Here's our complete menu with {len(menu_context)} items:\n\n"
    for item in menu_context:
        result += f"• {item['name']} (ID: {item['id']})\n"
    
    return result

@function_tool
async def handle_menu_inquiry() -> str:
    """Handle when user asks 'What's on the menu?' with natural response"""
    return "We have pizzas, wings, sides, drinks, and more! You can ask about a specific item you're interested in, like 'margherita pizza' or 'garlic bread'."

@function_tool
async def handle_multiple_items() -> str:
    """Handle when user lists multiple items at once - add them one by one"""
    return "I'd be happy to help you with those items! To make sure I get everything right, could you please tell me one item at a time? I'll add each one to your order as you mention them."

@function_tool
async def update_item_customization(item_name: str, customization_type: str, old_choice: str, new_choice: str) -> str:
    """Update an item's customization before checkout"""
    global user_cart
    
    # Find the item in cart
    for item in user_cart:
        if item.get("itemName", "").lower() == item_name.lower():
            customizations = item.get("customizations", [])
            
            # Find and remove old customization
            for i, custom in enumerate(customizations):
                if (custom.get("subItemGroupName", "").lower() == customization_type.lower() and 
                    custom.get("subItemName", "").lower() == old_choice.lower()):
                    customizations.pop(i)
                    break
            
            # Add new customization
            if new_choice.lower() not in ["no", "none", "remove", "skip"]:
                # Find the menu item to get customization details
                menu_item = get_menu_item_by_id(item.get("itemId"))
                if menu_item and menu_item.get("customization"):
                    if customization_type.lower() == "sauce" and "Sauce" in menu_item.get("customization", {}):
                        for sauce in menu_item["customization"]["Sauce"]:
                            if sauce.get("name", "").lower() == new_choice.lower():
                                new_customization = {
                                    "subItemName": sauce.get("name"),
                                    "subItemGroupName": "Sauce",
                                    "price": sauce.get("price", 0),
                                    "quantity": 1
                                }
                                customizations.append(new_customization)
                                item["itemPrice"] += sauce.get("price", 0)
                                break
                    elif customization_type.lower() == "toppings" and "Toppings" in menu_item.get("customization", {}):
                        for topping in menu_item["customization"]["Toppings"]:
                            if topping.get("name", "").lower() == new_choice.lower():
                                new_customization = {
                                    "subItemName": topping.get("name"),
                                    "subItemGroupName": "Toppings",
                                    "price": topping.get("price", 0),
                                    "quantity": 1
                                }
                                customizations.append(new_customization)
                                item["itemPrice"] += topping.get("price", 0)
                                break
                
                return f"Perfect! I've updated your {item_name} - changed {old_choice} to {new_choice}. Is there anything else you'd like to modify?"
            else:
                return f"Got it! I've removed {old_choice} from your {item_name}. Is there anything else you'd like to modify?"
    
    return f"I couldn't find {item_name} in your order. Could you please check the item name?"

@function_tool
async def add_item_basic(item_name: str, quantity: int = 1) -> str:
    """Add item to cart directly - no confirmation needed to avoid repeated questions"""
    global user_cart, current_item_customizing, customization_step, session_id
    
    # Safely convert input to string
    item_name = safe_string_conversion(item_name, "add_item_basic")
    if not item_name:
        return "I didn't catch that. Could you please tell me what you'd like to order?"
    
    # Generate session ID if not exists
    if not session_id:
        session_id = generate_session_id()
    
    # Find item by name
    item = get_menu_item_by_name(item_name)
    if not item:
        suggestions = get_popular_suggestions()
        return f"I don't see '{item_name}' on our menu. {suggestions}. What would you like to order instead?"
    
    # Add item directly to cart - no confirmation to avoid repeated questions
    return await confirm_add_item(item_name, quantity)

@function_tool
async def confirm_add_item(item_name: str, quantity: int = 1) -> str:
    """Add item to cart with duplicate prevention - no repeated confirmations"""
    global current_item_customizing, customization_step, session_id
    
    # Find item by name
    item = get_menu_item_by_name(item_name)
    if not item:
        suggestions = get_popular_suggestions()
        return f"I don't see '{item_name}' on our menu. {suggestions}. What would you like to order instead?"
    
    # Use safe cart addition to prevent duplicates
    success, message = add_item_to_cart_safe(item, quantity)
    if not success:
        return message
    
    # If item was already in cart (duplicate), just return the message
    if "updated the quantity" in message:
        return f"{message} What else would you like to order?"
    
    # Set up for customization if needed
    current_item_customizing = item.get("id")
    customization_step = "size"
    
    # Ask for size if multiple sizes available
    if item.get("sizes") and len(item["sizes"]) > 1:
        size_options = [s.get("name") for s in item["sizes"]]
        return f"Great! I've added ({item.get('name')}, {item.get('id')}) to your cart. What size would you like? Available sizes: {', '.join(size_options)}"
    elif item.get("sizes") and len(item["sizes"]) == 1:
        # Only one size, auto-select it
        size = item["sizes"][0]
        # Update the cart item with the selected size
        for cart_item in user_cart:
            if cart_item and cart_item.get("itemId") == item.get("id"):
                cart_item["selectedSize"] = size.get("name")
                cart_item["itemPrice"] = size.get("price", 0)
                break
        
        # Ask about customizations step by step
        if item.get("customization"):
            if "Sauce" in item.get("customization", {}):
                customization_step = "sauce"
                available_sauces = [s.get("name") for s in item["customization"]["Sauce"]]
                return f"Perfect! I've added ({item.get('name')}, {item.get('id')}) with {size.get('name')} to your cart. This pizza comes with these sauces: {', '.join(available_sauces)}. Which one would you like to choose?"
            elif "Toppings" in item.get("customization", {}):
                customization_step = "toppings"
                available_toppings = [t.get("name") for t in item["customization"]["Toppings"]]
                return f"Perfect! I've added ({item.get('name')}, {item.get('id')}) with {size.get('name')} to your cart. What toppings would you like? You can add UNLIMITED toppings from: {', '.join(available_toppings)}"
            else:
                # No customizations available
                total = size.get("price", 0) * quantity
                customization_step = "complete"
                current_item_customizing = None
                return f"Excellent! I've added ({item.get('name')}, {item.get('id')}) to your cart for {format_price_for_speech(total)}. What else would you like to order?"
        else:
            # No customizations available
            total = size.get("price", 0) * quantity
            customization_step = "complete"
            current_item_customizing = None
            return f"Excellent! I've added ({item.get('name')}, {item.get('id')}) to your cart for {format_price_for_speech(total)}. What else would you like to order?"
    else:
        # No sizes, check for customizations
        if item.get("customization"):
            if "Sauce" in item.get("customization", {}):
                customization_step = "sauce"
                available_sauces = [s.get("name") for s in item["customization"]["Sauce"]]
                return f"Perfect! I've added ({item.get('name')}, {item.get('id')}) to your cart. This pizza comes with these sauces: {', '.join(available_sauces)}. Which one would you like to choose?"
            elif "Toppings" in item.get("customization", {}):
                customization_step = "toppings"
                available_toppings = [t.get("name") for t in item["customization"]["Toppings"]]
                return f"Perfect! I've added ({item.get('name')}, {item.get('id')}) to your cart. What toppings would you like? You can add UNLIMITED toppings from: {', '.join(available_toppings)}"
            else:
                # No customizations available
                total = item.get("price", 0) * quantity
                customization_step = "complete"
                current_item_customizing = None
                return f"Excellent! I've added ({item.get('name')}, {item.get('id')}) to your cart for {format_price_for_speech(total)}. What else would you like to order?"
        else:
            # No customizations available
            total = item.get("price", 0) * quantity
            customization_step = "complete"
            current_item_customizing = None
            return f"Excellent! I've added ({item.get('name')}, {item.get('id')}) to your cart for {format_price_for_speech(total)}. What else would you like to order?"

@function_tool
async def update_item_size(size_name: str) -> str:
    """Step 2: Update the current item with selected size using (name, id) references"""
    global user_cart, current_item_customizing, customization_step
    
    if not current_item_customizing:
        return "I don't see any item being customized. Please add an item first."
    
    # Find the item in cart
    for item in user_cart:
        if item.get("itemId") == current_item_customizing:
            # Update size and price
            item["selectedSize"] = size_name
            
            # Find price for this size
            menu_item = get_menu_item_by_id(current_item_customizing)
            if menu_item and menu_item.get("sizes"):
                for size in menu_item["sizes"]:
                    if size.get("name") == size_name:
                        item["itemPrice"] = size.get("price", 0)
                        break
            
            # Ask about customizations step by step
            if menu_item and menu_item.get("customization"):
                if "Sauce" in menu_item.get("customization", {}):
                    customization_step = "sauce"
                    available_sauces = [s.get("name") for s in menu_item["customization"]["Sauce"]]
                    return f"Perfect! Updated ({item['itemName']}, {item['itemId']}) to {size_name}. Would you like any sauce? Available sauces: {', '.join(available_sauces)}"
                elif "Toppings" in menu_item.get("customization", {}):
                    customization_step = "toppings"
                    available_toppings = [t.get("name") for t in menu_item["customization"]["Toppings"]]
                    return f"Perfect! Updated ({item['itemName']}, {item['itemId']}) to {size_name}. Would you like any toppings? Available toppings: {', '.join(available_toppings)}"
                else:
                    # No customizations available
                    total = item["itemPrice"] * item["quantity"]
                    customization_step = "complete"
                    current_item_customizing = None
                    return f"Excellent! I've added {item['selectedSize']} ({item['itemName']}, {item['itemId']}) to your cart for {format_price_for_speech(total)}. What else would you like to order?"
            else:
                # No customizations available
                total = item["itemPrice"] * item["quantity"]
                customization_step = "complete"
                current_item_customizing = None
                return f"Excellent! I've added {item['selectedSize']} ({item['itemName']}, {item['itemId']}) to your cart for {format_price_for_speech(total)}. What else would you like to order?"
    
    return "I couldn't find the item to update. Please try again."

@function_tool
async def update_item_sauce(sauce_name: str) -> str:
    """Step 3: Update the current item with selected sauce using (name, id) references"""
    global user_cart, current_item_customizing, customization_step
    
    # Safely convert input to string
    sauce_name = safe_string_conversion(sauce_name, "update_item_sauce")
    if not sauce_name:
        return "I didn't catch that. Could you please tell me what sauce you'd like?"
    
    if not current_item_customizing:
        return "I don't see any item being customized. Please add an item first."
    
    # Handle "no" responses
    if sauce_name.lower() in ["no", "no thanks", "no thank you", "none", "skip"]:
        # Complete the item without sauce
        for item in user_cart:
            if item.get("itemId") == current_item_customizing:
                total = item["itemPrice"] * item["quantity"]
                customization_step = "complete"
                current_item_customizing = None
                return f"Perfect! I've added {item['selectedSize']} ({item['itemName']}, {item['itemId']}) to your cart for {format_price_for_speech(total)}. What else would you like to order?"
        return "I couldn't find the item to update. Please try again."
    
    # Find the item in cart
    for item in user_cart:
        if item.get("itemId") == current_item_customizing:
            # Add sauce customization
            menu_item = get_menu_item_by_id(current_item_customizing)
            if menu_item and menu_item.get("customization") and "Sauce" in menu_item.get("customization", {}):
                # For wings: Remove any existing sauce before adding new one (only one sauce allowed)
                if "wings" in item.get("itemName", "").lower():
                    item["customizations"] = [c for c in item.get("customizations", []) if c.get("subItemGroupName") != "Sauce"]
                
                # Find the sauce details
                for sauce in menu_item["customization"]["Sauce"]:
                    if sauce.get("name") == sauce_name:
                        # Add sauce to customizations
                        sauce_customization = {
                            "subItemName": sauce.get("name"),
                            "subItemGroupName": "Sauce",
                            "price": sauce.get("price", 0),
                            "quantity": 1
                        }
                        item["customizations"].append(sauce_customization)
                        
                        # Update item price if sauce has a cost
                        item["itemPrice"] += sauce.get("price", 0)
                        
                        # Narrate the action
                        print(f"Adding {sauce_name} sauce to {item['itemName']}...")
                        
                        # Complete the item
                        total = item["itemPrice"] * item["quantity"]
                        customization_step = "complete"
                        current_item_customizing = None
                        
                        if "wings" in item.get("itemName", "").lower():
                            return f"Perfect! I've added {sauce_name} sauce to your wings. The total is {format_price_for_speech(total)}. What else would you like to order?"
                        else:
                            return f"Perfect! I've added {sauce_name} sauce to your {item['itemName']}. The total is {format_price_for_speech(total)}. What else would you like to order?"
                
                return f"I couldn't find '{sauce_name}' sauce. Please choose from the available options."
            else:
                return "This item doesn't support sauce customization."
    
    return "I couldn't find the item to update. Please try again."

@function_tool
async def update_item_toppings(topping_name: str) -> str:
    """Step 3: Update the current item with selected toppings using (name, id) references"""
    global user_cart, current_item_customizing, customization_step
    
    # Safely convert input to string
    topping_name = safe_string_conversion(topping_name, "update_item_toppings")
    if not topping_name:
        return "I didn't catch that. Could you please tell me what toppings you'd like?"
    
    if not current_item_customizing:
        return "I don't see any item being customized. Please add an item first."
    
    # Handle "no" responses
    if topping_name.lower() in ["no", "no thanks", "no thank you", "none", "skip", "just cheese", "plain"]:
        # Complete the item without toppings
        for item in user_cart:
            if item.get("itemId") == current_item_customizing:
                total = item["itemPrice"] * item["quantity"]
                customization_step = "complete"
                current_item_customizing = None
                return f"Perfect! I've added {item['selectedSize']} ({item['itemName']}, {item['itemId']}) to your cart for {format_price_for_speech(total)}. What else would you like to order?"
        return "I couldn't find the item to update. Please try again."
    
    # Find the item in cart
    for item in user_cart:
        if item.get("itemId") == current_item_customizing:
            # Add topping customization
            menu_item = get_menu_item_by_id(current_item_customizing)
            if menu_item and menu_item.get("customization") and "Toppings" in menu_item.get("customization", {}):
                # Find the topping details
                for topping in menu_item["customization"]["Toppings"]:
                    if topping.get("name") == topping_name:
                        # Add topping to customizations
                        topping_customization = {
                            "subItemName": topping.get("name"),
                            "subItemGroupName": "Toppings",
                            "price": topping.get("price", 0),
                            "quantity": 1
                        }
                        item["customizations"].append(topping_customization)
                        
                        # Update item price if topping has a cost
                        item["itemPrice"] += topping.get("price", 0)
                        
                        # Complete the item
                        total = item["itemPrice"] * item["quantity"]
                        customization_step = "complete"
                        current_item_customizing = None
                        
                        if "pizza" in item.get("itemName", "").lower():
                            return f"Perfect! I've added {topping_name} to your pizza. Would you like to add any other toppings? You can add as many as you want! The total is {format_price_for_speech(total)}."
                        else:
                            return f"Perfect! I've added {topping_name} to your {item['itemName']}. The total is {format_price_for_speech(total)}. What else would you like to order?"
                
                return f"I couldn't find '{topping_name}' topping. Please choose from the available options."
            else:
                return "This item doesn't support topping customization."
    
    return "I couldn't find the item to update. Please try again."

@function_tool
async def get_cart_summary() -> str:
    """Get a summary of the current cart using (name, id) references"""
    if not user_cart:
        return "Your cart is empty. What would you like to order?"
    
    total = 0
    items = []
    
    for item in user_cart:
        if not item:
            continue
        
        item_name = item.get("itemName", "Unknown Item")
        item_id = item.get("itemId", "Unknown ID")
        quantity = item.get("quantity", 1)
        size = item.get("selectedSize", "")
        item_price = item.get("itemPrice", 0)
        customizations = item.get("customizations", [])
        
        # Build item description with (name, id) reference
        item_desc = f"{quantity}x ({item_name}, {item_id})"
        if size:
            item_desc += f" - {size}"
        
        if customizations:
            sauce_names = [c.get("subItemName") for c in customizations if c.get("subItemGroupName") == "Sauce"]
            topping_names = [c.get("subItemName") for c in customizations if c.get("subItemGroupName") == "Toppings"]
            if sauce_names:
                item_desc += f" with {', '.join(sauce_names)} sauce"
            if topping_names:
                item_desc += f" with {', '.join(topping_names)}"
        
        items.append(item_desc)
        total += item_price * quantity
    
    cart_summary = f"Your current order:\n" + "\n".join(f"• {item}" for item in items)
    cart_summary += f"\n\nTotal: {format_price_for_speech(total)}"
    
    return cart_summary

@function_tool
async def collect_customer_name(name: str) -> str:
    """Collect and store the customer's name for the order"""
    global customer_name
    
    # Safely convert input to string
    name = safe_string_conversion(name, "collect_customer_name")
    if not name:
        return "I didn't catch that. Could you please tell me your name again?"
    
    # Handle confirmation responses
    if name.lower() in ["yes", "yeah", "yep", "correct", "right", "that's right", "that's correct"]:
        if customer_name:
            # Customer is confirming their name, redirect to confirm_name_correct
            return await confirm_name_correct()
        else:
            return "I don't have your name yet. What is your name?"
    
    if name.lower() in ["no", "nope", "incorrect", "wrong", "that's wrong"]:
        return "I apologize for the confusion. What is your correct name?"
    
    # Extract name from various formats
    if name.lower().startswith(("my name is", "this is", "i'm", "i am")):
        # Extract name after common phrases
        name_parts = name.split()
        if len(name_parts) > 2:
            customer_name = " ".join(name_parts[2:]).strip()
        else:
            customer_name = name.strip()
    else:
        customer_name = name.strip()
    
    # Confirm the name first - always ask for confirmation
    return f"Your name is {customer_name}, am I correct?"

@function_tool
async def confirm_name_correct() -> str:
    """Handle when customer confirms their name is correct"""
    global customer_name
    
    if not customer_name:
        return "I don't have your name yet. What is your name?"
    
    # Show order summary after name confirmation and ask for final confirmation
    cart_summary = await get_cart_summary()
    return f"Perfect! Thank you, {customer_name}. Here's your complete order:\n\n{cart_summary}\n\nIs this order correct? Should I place it now?"

@function_tool
async def correct_name(new_name: str) -> str:
    """Handle when customer needs to correct their name"""
    global customer_name
    
    # Safely convert input to string
    new_name = safe_string_conversion(new_name, "correct_name")
    if not new_name:
        return "I didn't catch that. Could you please tell me your name again?"
    
    # Handle confirmation responses
    if new_name.lower() in ["yes", "yeah", "yep", "correct", "right", "that's right", "that's correct"]:
        if customer_name:
            # Customer is confirming their corrected name, redirect to confirm_name_correct
            return await confirm_name_correct()
        else:
            return "I don't have your name yet. What is your name?"
    
    if new_name.lower() in ["no", "nope", "incorrect", "wrong", "that's wrong"]:
        return "I apologize for the confusion. What is your correct name?"
    
    # Extract name from various formats
    if new_name.lower().startswith(("my name is", "this is", "i'm", "i am")):
        # Extract name after common phrases
        name_parts = new_name.split()
        if len(name_parts) > 2:
            customer_name = " ".join(name_parts[2:]).strip()
        else:
            customer_name = new_name.strip()
    else:
        customer_name = new_name.strip()
    
    # Confirm the corrected name
    return f"Got it! Your name is {customer_name}, am I correct?"

@function_tool
async def calculate_order_total() -> str:
    """Calculate and return the accurate total order price"""
    global user_cart
    
    if not user_cart:
        return "Your cart is empty. Total: $0.00"
    
    total = 0
    item_details = []
    
    for item in user_cart:
        if not item:
            continue
        
        # itemPrice already includes all customizations (sizes, sauces, toppings)
        # so we just multiply by quantity
        item_price = item.get("itemPrice", 0)
        quantity = item.get("quantity", 1)
        item_total = item_price * quantity
        total += item_total
        
        # Build item description for verification
        item_name = item.get("itemName", "Unknown Item")
        quantity = item.get("quantity", 1)
        size = item.get("selectedSize", "")
        
        item_desc = f"{quantity}x {item_name}"
        if size:
            item_desc += f" ({size})"
        
        if customizations:
            sauce_names = [c.get("subItemName") for c in customizations if c.get("subItemGroupName") == "Sauce"]
            topping_names = [c.get("subItemName") for c in customizations if c.get("subItemGroupName") == "Toppings"]
            if sauce_names:
                item_desc += f" with {', '.join(sauce_names)} sauce"
            if topping_names:
                item_desc += f" with {', '.join(topping_names)}"
        
        item_details.append(f"• {item_desc} - {format_price_for_speech(item_total)}")
    
    # Build complete order summary
    summary = "Here's your complete order:\n\n" + "\n".join(item_details)
    summary += f"\n\nTotal: {format_price_for_speech(total)}"
    
    return summary

@function_tool
async def final_order_review() -> str:
    """Final order review before checkout - read complete order and allow modifications"""
    global user_cart, customer_name
    
    if not user_cart:
        return "Your cart is empty. What would you like to order?"
    
    # Calculate accurate total
    order_summary = await calculate_order_total()
    
    # Add confirmation prompt
    order_summary += "\n\nIs this order correct? Would you like to make any changes before I place it?"
    
    return order_summary

@function_tool
async def finalize_order_with_name() -> str:
    """Finalize the order using the collected customer name - SINGLE API REQUEST"""
    global customer_name, user_cart
    
    if not customer_name:
        return "I need your name to complete the order. May I have your name to complete the order?"
    
    if not user_cart:
        return "Your cart is empty. What would you like to order?"
    
    # Store customer name before clearing
    final_customer_name = customer_name
    
    # Format cart for API submission
    order_data = format_cart_for_api(user_cart, customer_name)
    
    # Submit order to API - SINGLE REQUEST PER SESSION
    success = await submit_order_to_api(order_data)
    
    if success:
        # Clear the cart and reset state
        user_cart.clear()
        customer_name = None
        return f"Perfect! Your order has been placed successfully, {final_customer_name}. Thank you for choosing Jimmy Neno's Pizza! Have a great day and goodbye!"
    else:
        return f"I apologize, {final_customer_name}, but there was an issue placing your order. Please call us directly at the restaurant. Thank you and goodbye!"

@function_tool
async def confirm_and_place_order() -> str:
    """Handle final confirmation and place the order - ENDS CONVERSATION"""
    global customer_name, user_cart
    
    if not customer_name:
        return "I need your name to complete the order. May I have your name to complete the order?"
    
    if not user_cart:
        return "Your cart is empty. What would you like to order?"
    
    # Place the order immediately
    return await finalize_order_with_name()

@function_tool
async def get_full_menu() -> str:
    """Get menu groups only - for general menu requests (no prices unless asked)"""
    if not hasattr(current_session, 'menu_data') or not current_session.menu_data:
        return "I'm sorry, I'm having trouble loading our menu right now. Please try again in a moment."
    
    # Collect unique groups from menu data
    groups = set()
    for item in current_session.menu_data:
        if not item:  # Skip None items
            continue
        category = item.get('category', 'Other')
        if category:
            groups.add(category)
    
    # Build item types list (convert groups to user-friendly terms)
    item_types = {
        'Popular': 'Popular Items',
        'Appetizers & Sides': 'Appetizers & Sides',
        'Salads': 'Salads',
        'Soup': 'Soups',
        'Toasted Sandwiches': 'Sandwiches',
        'Burgers': 'Burgers',
        'Stromboli': 'Stromboli',
        'Rolls': 'Rolls',
        'Build Your Own Pizza': 'Build Your Own Pizza',
        'Gourmet Pizza': 'Gourmet Pizza',
        'Pasta Dinners': 'Pasta',
        'Beverages': 'Drinks'
    }
    
    result = "Here's what we have:\n\n"
    for group in sorted(groups):
        display_name = item_types.get(group, group)
        result += f"• {display_name}\n"
    
    result += "\nWould you like to see items from a specific group or hear about our popular items?"
    
    print(f"📋 Menu groups shown: {len(groups)} groups")
    return result

@function_tool
async def get_detailed_menu() -> str:
    """Get the complete menu with all items - for detailed requests"""
    if not hasattr(current_session, 'menu_data') or not current_session.menu_data:
        return "I'm sorry, I'm having trouble loading our menu right now. Please try again in a moment."
    
    # Classify items by categories
    pizzas = []
    wings = []
    sides = []
    drinks = []
    other = []
    
    # Collect all items from the session's menu data
    for item in current_session.menu_data:
            if not item:  # Skip None items
                continue
            short_name = item.get('short_name')
            name = clean_item_name(short_name or item.get('name', '') or '')
            
            # Skip items with empty names
            if not name:
                continue
            
            # Clean the name to remove any special characters, numbers, asterisks
            clean_name = name.replace('*', '').replace('#', '').replace('1.', '').replace('2.', '').replace('3.', '').replace('4.', '').replace('5.', '').replace('6.', '').replace('7.', '').replace('8.', '').replace('9.', '').replace('0.', '')
            clean_name = ' '.join(clean_name.split())  # Remove extra spaces
            
            # Show only clean name and ID, no prices
            item_id = item.get('id', 'N/A')
            item_info = f"• {clean_name} (ID: {item_id})"
            name_lower = name.lower()
            
            # Classify by item type using both category field and name keywords
            item_category = item.get('category', '').lower()
            
            if "pizza" in name_lower or "pizza" in item_category:
                pizzas.append(item_info)
            elif "wing" in name_lower or "wing" in item_category:
                wings.append(item_info)
            elif (any(word in name_lower for word in ["bread", "fries", "knots", "salad", "garlic"]) or 
                  "side" in item_category or "appetizer" in item_category):
                sides.append(item_info)
            elif (any(word in name_lower for word in ["coke", "pepsi", "sprite", "water", "drink"]) or 
                  "beverage" in item_category):
                drinks.append(item_info)
            else:
                other.append(item_info)
    
    # Build categorized menu
    result = "Here's our complete menu organized by categories:\n\n"
    
    if pizzas:
        result += "🍕 PIZZAS:\n"
        for pizza in pizzas:
            result += f"{pizza}\n"
        result += "\n"
    
    if wings:
        result += "🍗 WINGS:\n"
        for wing in wings:
            result += f"{wing}\n"
        result += "\n"
    
    if sides:
        result += "🍟 SIDES:\n"
        for side in sides:
            result += f"{side}\n"
        result += "\n"
    
    if drinks:
        result += "🥤 DRINKS:\n"
        for drink in drinks:
            result += f"{drink}\n"
        result += "\n"
    
    if other:
        result += "🍽️ OTHER ITEMS:\n"
        for item in other:
            result += f"{item}\n"
    
    total_items = len(pizzas) + len(wings) + len(sides) + len(drinks) + len(other)
    print(f"🍕 Detailed menu generated with {total_items} items from API")
    return result

@function_tool
async def get_category_menu(category: str) -> str:
    """Get menu items for a specific category with comprehensive filtering - only speak item names"""
    if not hasattr(current_session, 'menu_data') or not current_session.menu_data:
        return "I'm sorry, I'm having trouble loading our menu right now. Please try again in a moment."
    
    # Normalize category name for matching
    category_lower = category.lower().strip()
    
    # Comprehensive category mapping for all possible categories
    category_mapping = {
        # Popular
        'popular': 'Popular',
        'populars': 'Popular',
        
        # Appetizers & Sides
        'appetizer': 'Appetizers & Sides',
        'appetizers': 'Appetizers & Sides',
        'appetizers & sides': 'Appetizers & Sides',
        'appetizers and sides': 'Appetizers & Sides',
        'side': 'Appetizers & Sides',
        'sides': 'Appetizers & Sides',
        
        # Salads
        'salad': 'Salads',
        'salads': 'Salads',
        
        # Soup
        'soup': 'Soup',
        'soups': 'Soup',
        
        # Toasted Sandwiches
        'toasted sandwich': 'Toasted Sandwiches',
        'toasted sandwiches': 'Toasted Sandwiches',
        'sandwich': 'Toasted Sandwiches',
        'sandwiches': 'Toasted Sandwiches',
        'toasted': 'Toasted Sandwiches',
        
        # Burgers
        'burger': 'Burgers',
        'burgers': 'Burgers',
        
        # Stromboli
        'stromboli': 'Stromboli',
        'strombolis': 'Stromboli',
        
        # Rolls
        'roll': 'Rolls',
        'rolls': 'Rolls',
        
        # Build Your Own Pizza
        'build your own pizza': 'Build Your Own Pizza',
        'build your own': 'Build Your Own Pizza',
        'custom pizza': 'Build Your Own Pizza',
        'custom pizzas': 'Build Your Own Pizza',
        'byo pizza': 'Build Your Own Pizza',
        'byo': 'Build Your Own Pizza',
        
        # Gourmet Pizza
        'gourmet pizza': 'Gourmet Pizza',
        'gourmet pizzas': 'Gourmet Pizza',
        'gourmet': 'Gourmet Pizza',
        'specialty pizza': 'Gourmet Pizza',
        'specialty pizzas': 'Gourmet Pizza',
        
        # Pasta Dinners
        'pasta dinner': 'Pasta Dinners',
        'pasta dinners': 'Pasta Dinners',
        'pasta': 'Pasta Dinners',
        'pastas': 'Pasta Dinners',
        'dinner': 'Pasta Dinners',
        'dinners': 'Pasta Dinners',
        
        # Beverages
        'beverage': 'Beverages',
        'beverages': 'Beverages',
        'drink': 'Beverages',
        'drinks': 'Beverages',
        
        # Pizza mapping - show both gourmet and build your own
        'pizza': 'pizza',  # Special handling for pizza requests
        'pizzas': 'pizza'
    }
    
    mapped_category = category_mapping.get(category_lower, category_lower)
    
    # Filter items by exact category match
    items = []
    
    # Special handling for pizza requests - show both Gourmet Pizza and Build Your Own Pizza
    if mapped_category == 'pizza':
        for item in current_session.menu_data:
            if not item:
                continue
            item_category = item.get('category', '')
            if item_category in ['Gourmet Pizza', 'Build Your Own Pizza']:
                items.append(item)
    else:
        # Regular category filtering
        for item in current_session.menu_data:
            if not item:
                continue
            item_category = item.get('category', '')
            if item_category == mapped_category:
                items.append(item)
    
    if not items:
        # Try partial matching as fallback
        for item in current_session.menu_data:
            if not item:
                continue
            item_category = item.get('category', '').lower()
            if mapped_category.lower() in item_category or item_category in mapped_category.lower():
                items.append(item)
    
    if not items:
        # Get available categories for better error message
        available_categories = set()
        for item in current_session.menu_data:
            if item and item.get('category'):
                available_categories.add(item.get('category'))
        
        return f"I don't see any items in the '{category}' category. Available categories are: {', '.join(sorted(available_categories))}. What would you like to see?"
    
    # Build response with clean item names only (no asterisks, numbers, or special characters)
    if mapped_category == 'pizza':
        result = "Here are our pizza options:\n"
    else:
        result = f"Here are our {mapped_category} options:\n"
    
    for item in items[:15]:  # Limit to 15 items
        if not item:
            continue
        short_name = item.get('short_name')
        name = clean_item_name(short_name or item.get('name', '') or '')
        if name:
            # Clean the name to remove any special characters, numbers, asterisks
            clean_name = name.replace('*', '').replace('#', '').replace('1.', '').replace('2.', '').replace('3.', '').replace('4.', '').replace('5.', '').replace('6.', '').replace('7.', '').replace('8.', '').replace('9.', '').replace('0.', '')
            clean_name = ' '.join(clean_name.split())  # Remove extra spaces
            result += f"{clean_name}\n"
    
    if len(items) > 15:
        result += f"And {len(items) - 15} more items in this category.\n"
    
    result += "What would you like to know more about?"
    
    print(f"📋 Category '{category}' filtered: {len(items)} items found")
    return result

def check_items_need_customization():
    """Check if any items in the cart need customizations"""
    global user_cart
    items_needing_customization = []
    
    for item in user_cart:
        if not item:
            continue
        
        item_id = item.get('itemId')
        menu_item = get_menu_item_by_id(item_id)
        
        if menu_item and menu_item.get('customization'):
            # Check if this item has customizations that haven't been completed
            customizations = item.get('customizations', [])
            required_groups = []
            
            for group, options in menu_item['customization'].items():
                if group == "Toppings" and options:
                    required_groups.append("toppings")
                elif group == "Sauce" and options:
                    required_groups.append("sauce")
            
            if required_groups:
                completed_groups = set()
                for custom in customizations:
                    if custom and custom.get('subItemGroupName'):
                        group_name = custom['subItemGroupName'].lower()
                        if group_name in ['toppings', 'sauce']:
                            completed_groups.add(group_name)
                
                if len(completed_groups) < len(required_groups):
                    items_needing_customization.append({
                        'item': item,
                        'menu_item': menu_item,
                        'missing_groups': [g for g in required_groups if g not in completed_groups]
                    })
    
    return items_needing_customization

def normalize_sauce_name(sauce_input: str) -> str:
    """Normalize sauce name input to match available options"""
    sauce_input = sauce_input.strip().lower()
    
    # Common variations and mappings
    sauce_mappings = {
        'bbq': 'BBQ',
        'barbecue': 'BBQ',
        'buffalo': 'Buffalo',
        'hot': 'Buffalo',
        'spicy': 'Buffalo',
        'honey mustard': 'Honey Mustard',
        'honey': 'Honey Mustard',
        'mustard': 'Honey Mustard',
        'garlic parm': 'Garlic Parm',
        'garlic parmesan': 'Garlic Parm',
        'garlic': 'Garlic Parm',
        'parmesan': 'Garlic Parm',
        'mild': 'Mild',
        'plain': 'Mild',
        'regular': 'Mild'
    }
    
    # Try exact match first
    if sauce_input in sauce_mappings:
        return sauce_mappings[sauce_input]
    
    # Try partial matches
    for key, value in sauce_mappings.items():
        if key in sauce_input or sauce_input in key:
            return value
    
    # Return original if no match found
    return sauce_input.title()

@function_tool
async def process_all_customizations() -> str:
    """Process customizations for all items that need them"""
    global current_state, current_item_customizing
    
    items_needing_customization = check_items_need_customization()
    
    if not items_needing_customization:
        set_state(OrderState.TAKING_ORDER)
        return "Perfect! All your items are ready. What else can I get for you today?"
    
    # Find the first item that needs customization
    first_item = items_needing_customization[0]
    item = first_item['item']
    menu_item = first_item['menu_item']
    missing_groups = first_item['missing_groups']
    
    current_item_customizing = item
    set_state(OrderState.CUSTOMIZING)
    
    # Build customization prompt
    item_name = item.get('itemName', 'item')
    result = f"Great! Now let's customize your {item_name}. "
    
    if 'toppings' in missing_groups and 'sauce' in missing_groups:
        result += "What toppings would you like, and what sauce would you prefer?"
    elif 'toppings' in missing_groups:
        result += "What toppings would you like?"
    elif 'sauce' in missing_groups:
        result += "What sauce would you like?"
    
    # Show available options
    if menu_item.get('customization'):
        for group, options in menu_item['customization'].items():
            if group == "Toppings" and options and 'toppings' in missing_groups:
                topping_names = [opt.get('name', '') if isinstance(opt, dict) else str(opt) for opt in options if opt]
                if topping_names:
                    result += f" Available toppings: {', '.join(topping_names)}."
            elif group == "Sauce" and options and 'sauce' in missing_groups:
                sauce_names = [opt.get('name', '') if isinstance(opt, dict) else str(opt) for opt in options if opt]
                if sauce_names:
                    result += f" Available sauces: {', '.join(sauce_names)}."
    
    return result

@function_tool
async def get_item_details(item_id: int) -> str:
    """Get detailed information about a specific item including pricing and customizations"""
    item = get_menu_item_by_id(item_id)
    if not item:
        return f"I couldn't find an item with ID {item_id}. Could you please check the menu again?"
    
    name = item.get('name', 'Unknown Item')
    result = f"Here are the details for {name}:\n\n"
    
    # Show pricing
    if item.get('sizes') and item['sizes']:
        result += "Available sizes and prices:\n"
        for size in item['sizes']:
            size_name = size.get('name', '')
            size_price = size.get('price', 0)
            result += f"• {size_name}: ${size_price:.2f}\n"
    else:
        price = item.get('price', 0)
        result += f"Price: ${price:.2f}\n"
    
    # Show available customizations
    if item.get('customization'):
        result += "\nAvailable customizations:\n"
        for group, options in item['customization'].items():
            if group == "Toppings" and options:
                topping_names = [opt.get('name', '') if isinstance(opt, dict) else str(opt) for opt in options if opt]
                if topping_names:
                    result += f"• Toppings: {', '.join(topping_names)}\n"
            elif group == "Sauce" and options:
                sauce_names = [opt.get('name', '') if isinstance(opt, dict) else str(opt) for opt in options if opt]
                if sauce_names:
                    result += f"• Sauces: {', '.join(sauce_names)}\n"
    
    return result

@function_tool
async def clarify_item_name(partial_name: str) -> str:
    """Help clarify item name when user's request is unclear"""
    if not MENU:
        return "I'm sorry, I'm having trouble accessing the menu right now. Please try again."
    
    partial_lower = partial_name.lower()
    matches = []
    
    # Search through all items for partial matches
    for category, items in MENU.items():
        if not items:
            continue
        for item in items:
            if not item:
                continue
            short_name = item.get('short_name')
            name = clean_item_name(short_name or item.get('name', '') or '')
            
            if not name:
                continue
            
            name_lower = name.lower()
            if partial_lower in name_lower or any(word in name_lower for word in partial_lower.split()):
                matches.append(f"• {name} (ID: {item.get('id', 'N/A')})")
    
    if not matches:
        return f"I couldn't find any items matching '{partial_name}'. Could you please try again or ask to see our full menu?"
    
    if len(matches) == 1:
        return f"I found one item that might match: {matches[0]}. Is this what you're looking for?"
    else:
        result = f"I found several items that might match '{partial_name}':\n\n"
        result += "\n".join(matches[:5])  # Limit to 5 matches
        if len(matches) > 5:
            result += f"\n... and {len(matches) - 5} more items."
        result += "\n\nCould you please specify which one you'd like?"
        return result

@function_tool
async def show_pricing_info() -> str:
    """Show pricing information during taking order stage"""
    if not user_cart:
        return "You don't have any items in your cart yet. Would you like to see our menu to choose something?"
    
    total = 0
    pricing_info = "Here's your current order with pricing:\n\n"
    
    for item in user_cart:
        if not item:
            continue
        
        name = item.get('itemName', 'Unknown Item')
        quantity = item.get('quantity', 1)
        base_price = item.get('itemPrice', 0)
        
        # Calculate item total (base price + customizations)
        item_total = base_price * quantity
        total += item_total
        
        pricing_info += f"• {name} (Qty: {quantity}) - ${item_total:.2f}\n"
        
        # Show customizations if any
        customizations = item.get('customizations', [])
        if customizations:
            for custom in customizations:
                if custom and custom.get('subItemName'):
                    custom_name = custom.get('subItemName', '')
                    custom_price = custom.get('price', 0) * custom.get('quantity', 1)
                    pricing_info += f"  - {custom_name}: +${custom_price:.2f}\n"
    
    pricing_info += f"\nTotal: ${total:.2f}"
    return pricing_info

@function_tool
async def get_sauce_options(item_id: int) -> str:
    """Get available sauce options for a specific item"""
    item = get_menu_item_by_id(item_id)
    if not item or "customization" not in item or not item["customization"]:
        return "This item doesn't have sauce options."
    
    sauce_options = item["customization"].get("Sauce", [])
    if not sauce_options:
        return "This item doesn't have sauce options."
    
    if isinstance(sauce_options[0], str):
        return f"Available sauces: {', '.join(sauce_options)}"
    else:
        sauce_names = [opt.get("name", "") for opt in sauce_options if opt]
        return f"Available sauces: {', '.join(sauce_names)}"

@function_tool
async def get_price() -> str:
    """Get current cart total - can be called at any stage"""
    if not user_cart:
        return "Your cart is empty. Total: $0.00"
    total = sum(item.get("itemPrice", 0) * item.get("quantity", 1) for item in user_cart if item)
    
    # Don't change state - just return the price
    logger.info(f"Price check - Items: {len(user_cart)}, Total: ${total:.2f}")
    
    return f"Your current total is ${total:.2f}. What else can I get for you today?"

@function_tool
async def get_cart_total() -> str:
    """Get current cart total - alternative function for price checking"""
    if not user_cart:
        return "Your cart is empty. Total: $0.00"
    total = sum(item.get("itemPrice", 0) * item.get("quantity", 1) for item in user_cart if item)
    
    logger.info(f"Cart total check - Items: {len(user_cart)}, Total: ${total:.2f}")
    
    return f"Your current total is ${total:.2f}. What else can I get for you today?"

@function_tool
async def get_item_price(item_name: str) -> str:
    """Get price for a specific menu item when customer asks directly"""
    item = find_menu_item_by_name(item_name)
    if not item:
        return f"I couldn't find '{item_name}' on our menu. Would you like me to show you our complete menu?"
    
    # Handle items with sizes (use first size price) or direct price
    if item.get('sizes') and item['sizes']:
        price = item['sizes'][0].get('price', 0)
        size_name = item['sizes'][0].get('name', '')
        short_name = item.get('short_name')
        name = clean_item_name(short_name or item.get('name', '') or '')
        return f"{name} ({size_name}) is {format_price_for_speech(price)}. Would you like to add it to your order?"
    else:
        price = item.get('price', 0)
        short_name = item.get('short_name')
        name = clean_item_name(short_name or item.get('name', '') or '')
        return f"{name} is {format_price_for_speech(price)}. Would you like to add it to your order?"

@function_tool
async def set_customer_name(customer_name: str) -> str:
    logger.info(f"Customer name: {customer_name}")
    return f"Thank you, {customer_name}! Your name has been added to the order."

@function_tool
async def set_customer_phone(phone_number: str) -> str:
    """Collect customer phone number for the order"""
    logger.info(f"Customer phone: {phone_number}")
    return f"Perfect! I have your phone number as {phone_number}. Let me get your order total now."

@function_tool
async def complete_order_with_details(customer_name: str, phone_number: str = None) -> str:
    """Complete the order with customer name and phone number"""
    global current_state
    
    if not user_cart:
        return "I don't see any items in your cart. Let me help you add something first."
    
    # Calculate total including customizations
    total = 0
    for item in user_cart:
        if not item:
            continue
        item_price = item.get("itemPrice", 0)
        quantity = item.get("quantity", 1)
        item_total = item_price * quantity
        
        # Add customization prices
        customizations = item.get("customizations", [])
        for custom in customizations:
            if custom and isinstance(custom, dict):
                custom_price = custom.get("price", 0.0)
                custom_quantity = custom.get("quantity", 1)
                item_total += custom_price * custom_quantity
        
        total += item_total
    
    set_state(OrderState.FINALIZING)
    
    # Format order for API
    order_data = format_cart_for_api(user_cart, customer_name, phone_number)
    
    # Submit order to API
    success = await submit_order_to_api(order_data)
    
    # Log order completion for analytics
    logger.info(f"Order completed - Customer: {customer_name}, Phone: {phone_number or 'Not provided'}, Items: {len(user_cart)}, Total: ${total:.2f}, API Success: {success}")
    print("ORDER FINALIZED (cart-JSON):")
    print(json.dumps(user_cart, indent=2))
    print(f"CUSTOMER: {customer_name}")
    print(f"PHONE: {phone_number or 'Not provided'}")
    print(f"TOTAL PRICE: ${total:.2f}")
    print(f"ORDER ID: {order_data.get('id', 'Unknown')}")
    print(f"API SUBMISSION: {'SUCCESS' if success else 'FAILED'}")
    
    if success:
        # Don't schedule termination immediately - let the user respond first
        return f"Perfect! Thank you, {customer_name}! Your order is confirmed. Order ID: {order_data.get('id', 'Unknown')}. Total: ${total:.2f}. We'll have your meal ready soon. Thank you for choosing Jimmy Neno's Pizza! Is there anything else I can help you with?"
    else:
        # Don't schedule termination immediately - let the user respond first
        return f"Thank you, {customer_name}! Your order is confirmed locally. Total: ${total:.2f}. We have your order details and will process it. Thank you for choosing Jimmy Neno's Pizza! Is there anything else I can help you with?"

@function_tool
async def get_caller_phone() -> str:
    """Get the caller's phone number from call data"""
    global current_session
    if current_session and hasattr(current_session, 'participant_phone') and current_session.participant_phone:
        return current_session.participant_phone
    return "Not provided"

@function_tool
async def finalize_order(customer_name: str) -> str:
    """Finalize the order with just customer name - phone will be retrieved from call data"""
    global current_state
    
    if not user_cart:
        return "I don't see any items in your cart. Let me help you add something first."
    
    # Get phone from call data (placeholder for now)
    phone_number = await get_caller_phone()
    
    # Calculate total including customizations
    total = 0
    for item in user_cart:
        if not item:
            continue
        item_price = item.get("itemPrice", 0)
        quantity = item.get("quantity", 1)
        item_total = item_price * quantity
        
        # Add customization prices
        customizations = item.get("customizations", [])
        for custom in customizations:
            if custom and isinstance(custom, dict):
                custom_price = custom.get("price", 0.0)
                custom_quantity = custom.get("quantity", 1)
                item_total += custom_price * custom_quantity
        
        total += item_total
    
    set_state(OrderState.FINALIZING)
    
    # Format order for API
    order_data = format_cart_for_api(user_cart, customer_name, phone_number)
    
    # Submit order to API
    success = await submit_order_to_api(order_data)
    
    # Log order completion for analytics
    logger.info(f"Order completed - Customer: {customer_name}, Phone: {phone_number}, Items: {len(user_cart)}, Total: ${total:.2f}, API Success: {success}")
    print("ORDER FINALIZED (cart-JSON):")
    print(json.dumps(user_cart, indent=2))
    print(f"CUSTOMER: {customer_name}")
    print(f"PHONE: {phone_number}")
    print(f"TOTAL PRICE: ${total:.2f}")
    print(f"ORDER ID: {order_data.get('id', 'Unknown')}")
    print(f"API SUBMISSION: {'SUCCESS' if success else 'FAILED'}")
    
    if success:
        # Don't schedule termination immediately - let the user respond first
        return f"Perfect! Thank you, {customer_name}! Your order is confirmed. Order ID: {order_data.get('id', 'Unknown')}. Total: ${total:.2f}. We'll have your meal ready soon. Thank you for choosing Jimmy Neno's Pizza! Is there anything else I can help you with?"
    else:
        # Don't schedule termination immediately - let the user respond first
        return f"Thank you, {customer_name}! Your order is confirmed locally. Total: ${total:.2f}. We have your order details and will process it. Thank you for choosing Jimmy Neno's Pizza! Is there anything else I can help you with?"

@function_tool
async def end_call() -> str:
    """End the call after order completion"""
    logger.info("Call ended after order completion")
    print("CALL ENDED - Order completed successfully")
    
    # Schedule call termination after a brief delay to allow final message to be spoken
    import asyncio
    asyncio.create_task(_terminate_call_after_delay())
    
    return "Call ended. Thank you for choosing Jimmy Neno's Pizza!"

@function_tool
async def say_goodbye_and_end_call() -> str:
    """Say goodbye and end the call gracefully after order completion"""
    logger.info("Saying goodbye and ending call after order completion")
    print("GOODBYE MESSAGE - Ending call gracefully")
    
    # Schedule call termination after a brief delay to allow final message to be spoken
    import asyncio
    asyncio.create_task(_terminate_call_after_delay())
    
    return "Thank you for choosing Jimmy Neno's Pizza! Your order is ready. Goodbye!"

async def _terminate_call_after_delay():
    """Terminate the call after a brief delay"""
    await asyncio.sleep(8)  # Wait 8 seconds for final message to be spoken completely
    try:
        # Get the current session and end the call
        if 'current_session' in globals() and current_session:
            await current_session.end_call_gracefully()
        else:
            logger.warning("No current session available to terminate call")
    except Exception as e:
        logger.error(f"Error terminating call: {str(e)}")

def get_instructions() -> str:
    # Build catalog from the loaded menu
    if MENU:
        catalog_items = []
        for category, items in MENU.items():
            if not items:  # Skip empty categories
                continue
            for item in items:
                if not item:  # Skip None items
                    continue
                short_name = item.get("short_name")
                name = clean_item_name(short_name or item.get("name", "") or "")
                catalog_items.append(name)
        catalog_text = "Menu Catalog:\n" + "\n".join(catalog_items)
    else:
        catalog_text = "Menu Catalog: Loading menu from API..."
    
    # Enhanced system prompt for Jimmy Neno's Pizza
    professional_prompt = """
You are "Sofia," the lead voice concierge for Jimmy Neno's Pizza (pronounced "Jimmy Knee-nose"). You are not just an order-taker; you are the first impression of our pizzeria – friendly, knowledgeable, and incredibly efficient. Your goal is to make ordering a pizza feel like a warm and personal conversation.

[PERSONA & STYLE]
Tone: Consistently warm, friendly, and upbeat. Sofia's confidence should be reassuring to the customer.
Pacing: Mirror the customer's pace. If they're speaking quickly, be efficient. If they're hesitant, be patient and gently guide them. Allow for natural pauses; don't rush to fill silence.
Language: Use natural, conversational language and contractions (e.g., "you're," "what's"). Avoid robotic phrasing. Strive for a balance between professional and casual, like a helpful neighbor.
Vocal Nuances: To sound more human, occasionally use light filler words like "Alright," "Okay, so..." or "Got it." For example: "Okay, so you'd like a large pepperoni..." This makes the interaction feel less scripted.

[CORE DIRECTIVES]
Clarity is Key: Use simple, unambiguous language. Avoid jargon or overly complex sentences.
Active Listening: NEVER interrupt the customer. Listen to their full thought before formulating a response.
Sofia's Approach: Be warm, professional, and efficient. Make every customer feel valued and heard.
Accuracy is Paramount: The primary goal is a 100% accurate order. Every other directive supports this.
Single, Gentle Upsell: You are permitted to suggest one additional item (like drinks, sides, or dessert) after the main order is complete. If the customer declines, you MUST proceed to confirmation without a second attempt.
Stay on Task: Do not engage in conversations outside of the ordering process. If a customer asks an unrelated question, politely steer the conversation back to the order.

[STRICT ORDERING RULES - NO EXCEPTIONS]
1. NO DUPLICATE ITEMS: Only add each requested item to the cart once. Never add an item (like wings) multiple times unless the user specifically asks for it.
2. NO UNAUTHORIZED ITEMS: Never add items to the order that the user has not explicitly requested.
3. SINGLE CART CONFIRMATION: Confirm the order/cart only once, after the user indicates they are finished ordering—not after each individual item is added.
4. NO REPEATED QUESTIONS: Avoid asking the same question multiple times during the session. Do not repeatedly confirm after every item; only confirm at the final checkout stage.
5. NO MISTAKES ALLOWED: Always ensure the cart is correct and reflects what the user ordered. Double-check before confirming the final order.

[CRITICAL: IMMEDIATE ITEM VALIDATION]
You MUST validate every item mentioned by the customer IMMEDIATELY when they mention it, not at checkout.

VALIDATION RULES:
- When a customer mentions ANY item, immediately call check_item_availability(item_name) to verify it exists
- If the item does NOT exist, immediately tell the customer: "Sorry, '[item_name]' is not available on our menu. [suggest popular items]. What would you like to order instead?"
- NEVER say "yes" or confirm an item without first validating it exists in the menu
- NEVER take a customer to checkout with non-existent items
- If you're unsure about an item name, ask for clarification: "I want to make sure I have the right item - did you mean [suggested item]?"

EXAMPLES:
- Customer: "I want a pepperoni pizza" → You: Call check_item_availability("pepperoni pizza") first
- Customer: "I want a chocolate pizza" → You: "Sorry, 'chocolate pizza' is not available on our menu. Some popular items we have are: Wings, 12 Inch Pizza, Personal Pizza. What would you like to order instead?"
- Customer: "I want a margherita pizza" → You: Call check_item_availability("margherita pizza") first

NEVER proceed with ordering until you've confirmed the item exists in the menu.

[CONVERSATION CONTEXT & PREVENTING REPETITIVE QUESTIONS]
You MUST maintain conversation context to avoid asking the same questions repeatedly:

CONTEXT RULES:
- Track what items the customer has mentioned and what questions you've already asked
- If you've already asked about size for an item, don't ask again - use select_size() when they respond
- If you've already asked about customizations, don't ask again - use add_sauce() or add_topping() when they respond
- If an item is already in the cart, don't ask if they want to add it again
- Always acknowledge what the customer has already told you before asking new questions

EXAMPLES:
- Customer: "I want wings" → You: "Great! Wings are available. What size would you like? 10 Count or 24 Count?"
- Customer: "10 count" → You: Call select_size("wings", "10 count") - don't ask about size again
- Customer: "BBQ sauce" → You: Call add_sauce() - don't ask about sauce again

NEVER ask the same question twice in a conversation.

[CONVERSATIONAL FLOW & TASK EXECUTION]
1. Greeting & Opening:
* Objective: Welcome the customer warmly and prompt for their order.
* Phrasing: "Hi! Welcome to Jimmy Knee-nose Pizza! This is Sofia. What would you like to have today?"

2. Menu Handling:
* When user asks "What's on the menu?" → Call handle_menu_inquiry() → "We have pizzas, wings, sides, drinks, and more!"
* When user asks for specific group (e.g., "What pizzas do you have?") → Call get_category_menu(group) → List only items from that group
* NEVER use the word "categories" - always say "groups" or "types"
* NEVER mention prices unless customer asks directly ("How much is...?")
* When customer asks for price → Call get_item_price(item_name) → Use clear pronunciation ("twelve dollars" not "$12.00")

3. Multiple Items Handling:
* When user mentions several items at once → Call handle_multiple_items() → "I'd be happy to help you with those items! To make sure I get everything right, could you please tell me one item at a time?"
* Add and confirm each item one by one with required customizations
* Store context so you know which customizations belong to which item

4. Customization Updates:
* Allow user to update any item's customization before checkout
* Use update_item_customization(item_name, type, old_choice, new_choice)
* Example: "Actually, can I have pepperoni instead of mushrooms on my pizza?"
* Implement logic to update or replace previous choices per item in cart

2. Step-by-Step Ordering Process with Confirmation:
* Objective: Use the exact step-by-step flow for all orders with confirmation at each step.
* Process: ALWAYS use these functions in sequence:
  - Step 1: add_item_basic(item_name, quantity) - ASKS FOR CONFIRMATION before adding
  - Step 1b: confirm_add_item(item_name, quantity) - Actually adds item after user confirms
  - Step 2: update_item_size(size_name) - Updates size if multiple sizes available
  - Step 3: update_item_sauce(sauce_name) OR update_item_toppings(topping_name) - Updates customizations
  - Step 4: get_cart_summary() - Shows current order with (name, id) references
  - Step 5: calculate_order_total() - Calculates accurate total including all prices
  - Step 6: final_order_review() - Shows complete order for final confirmation
  - Step 7: collect_customer_name(name) - Collects customer name before finalizing
  - Step 8: finalize_order_with_name() - SINGLE API REQUEST at the end

* CRITICAL: Always use clean item names when talking about items - NO NUMBERS:
  - "I've added Wings to your cart"
  - "Updated Wings to 24 Count"
  - "Added Buffalo sauce to Wings"

* CUSTOMIZATION RULES - NO AUTO-ADDITION:
  - NEVER add customizations by default - always ask first
  - Ask "Would you like any sauce?" not "What sauce would you like?"
  - Ask "Would you like any toppings?" not "What toppings would you like?"
  - Only add customizations when user explicitly requests them
  - Handle "no" responses gracefully (no, no thanks, none, skip, just cheese, plain)

* EXAMPLE FLOW for Wings:
  - Customer: "I want wings"
  - You: Call add_item_basic("wings") → "Great! I've added Wings to your cart. What size would you like? 10 Count or 24 Count?"
  - Customer: "24 count"
  - You: Call update_item_size("24 Count") → "Perfect! Updated Wings to 24 Count. What sauce would you like? You can choose ONE sauce from: Buffalo, BBQ, Garlic Parm, Honey Mustard, Mild, Hot, Ranch, Blue Cheese"
  - Customer: "Buffalo"
  - You: Call update_item_sauce("Buffalo") → "Perfect! I've added Buffalo sauce to Wings. The total is twenty-eight dollars. What else would you like to order?"

* EXAMPLE FLOW for Pizza:
  - Customer: "I want a 12 Inch Pizza"
  - You: Call add_item_basic("12 Inch Pizza") → "Great! I've added 12 Inch Pizza to your cart. What toppings would you like? You can add UNLIMITED toppings from: Pepperoni, Mushrooms, Sausage, Extra Cheese, Green Peppers"
  - Customer: "Just mushrooms"
  - You: Call update_item_toppings("Mushrooms") → "Perfect! I've added Mushrooms to 12 Inch Pizza. Would you like to add any other toppings? You can add as many as you want!"

* NAME COLLECTION & CONFIRMATION:
  - ALWAYS ask for customer name before finalizing order
  - Use collect_customer_name(name) when customer provides their name
  - ALWAYS confirm the name: "Your name is [name], am I correct?"
  - When customer says "yes" to confirm → collect_customer_name("yes") will automatically redirect to confirm_name_correct()
  - When customer says "no" to correct → collect_customer_name("no") will ask for correct name
  - If no name collected, ask: "May I have your name to complete the order?"
  - Never default to "customer" - always collect actual name
  - CRITICAL: The collect_customer_name function now handles "yes"/"no" responses automatically
  - FINAL CONFIRMATION: After name confirmation, show complete order and ask "Is this order correct? Should I place it now?"
  - PLACE ORDER: When customer confirms, use confirm_and_place_order() to place order and end conversation
  - CONVERSATION END: After confirm_and_place_order(), give final greeting and end call - NO MORE LISTENING

* PRICE PRONUNCIATION:
  - Always use format_price_for_speech() for prices
  - Say "twenty-eight dollars" not "$28"
  - Say "ten dollars" not "ten"
  - Say "twelve dollars and fifty cents" not "twelve point five"
  - Only read out total amount at checkout stage - never before

* CART ACCURACY & COMMUNICATION:
  - Always ensure what you say matches exactly what's in the cart
  - When summarizing cart or items, cross-check item details (names, sizes, customizations)
  - Avoid any mismatch between speech and cart contents
  - Use get_cart_summary() to verify cart contents before speaking

* USER EXPERIENCE ENHANCEMENTS:
  - Never interrupt the user - wait for natural pauses or confirmations
  - Always confirm toppings, sauces, and modifications have been added accurately
  - If user wants to add more items ("anything else?"), repeat the add-and-customize process
  - Use natural, conversational language and contractions
  - Allow for natural pauses; don't rush to fill silence

* ORDER FLOW AND LOGIC GUIDELINES:
  - PRICE CALCULATION ACCURACY: Always calculate total by summing base price + size + customizations
  - CONFIRMATION BEFORE ADDING: When user mentions item, ALWAYS ask "Would you like to add [item] to your order?"
  - ONE API REQUEST PER SESSION: Collect ENTIRE order, send only ONE POST request at the end
  - FINAL ORDER REVIEW: Read complete order with total before checkout, allow modifications
  - CONSISTENCY: Final order must exactly match what was verbally confirmed with user
  - GENERAL: Never add items unless user explicitly requests them

[BOT WORKFLOW & EXPERIENCE GUIDELINES]

* CATEGORY-SPECIFIC OPTIONS:
  - When user requests specific category (e.g., "I want pizza"), ONLY present options from that category
  - Use get_category_menu(category) to filter and show only relevant items
  - Never mix categories when user asks for specific type

* HUMANLIKE CUSTOMIZATIONS:
  - Describe customizations naturally: "This pizza comes with these toppings and sauces. Which would you like to choose?"
  - Use conversational language: "What we have is these sauces: Buffalo, BBQ, Garlic Parm. Which one sounds good to you?"
  - Avoid robotic phrasing like "Available options are..."

* ALWAYS ASK NAME BEFORE CHECKOUT:
  - ALWAYS ask for user's name before proceeding to order submission
  - Use collect_customer_name(name) when provided
  - If no name collected, ask: "May I have your name to complete the order?"
  - Never proceed to checkout without collecting name

* ACCURATE PRICING, ANNOUNCED ONLY AT CHECKOUT:
  - Ensure item prices and total are 100% accurate
  - Do NOT mention prices while presenting or adding items
  - Announce price clearly in words (e.g., "twelve dollars" for $12.00) ONLY during checkout/order total
  - Use format_price_for_speech() for all price announcements

* NO PAUSES, MULTITASK & NARRATE ACTIONS:
  - Never pause the conversation (e.g., while adding items or customizations)
  - Narrate actions as you do them: "I'm adding this pizza with extra cheese to your order, and you can also choose your sauce..."
  - Offer multitasking dialogue for smoother, engaging experience
  - Keep conversation flowing naturally without awkward silences

* CART BUILDING:
  - Make sure any selected toppings or modifications are reflected in cart for each item ordered
  - Use get_cart_summary() to verify cart contents match what you've said
  - Cross-check item details (names, sizes, customizations) before speaking

* NO INTERRUPTIONS:
  - Do not interrupt the user while they are speaking or providing input
  - Wait for natural pauses or confirmations before proceeding
  - Listen to their full thought before formulating a response

* PRONUNCIATION:
  - Always pronounce "Jimmy Neno's" as "Jimmy Knee-nose"
  - Use this pronunciation in all references to the restaurant name

3. Gentle Upsell:
* Objective: Suggest one relevant item to enhance the meal.
* Timing: After they've finished listing their main items.
* Phrasing: "Got it. And would you like to add any drinks or maybe our popular wings to your order today?"
* Response: If they say no, immediately move on with a positive affirmation like, "No problem at all."
* CRITICAL: If they specify a drink or any item, FIRST call check_item_availability(item_name) to validate it exists before proceeding
* If they specify a drink, FIRST call check_item_availability(drink_name), then if it exists, call lookup_add_item_to_cart() with that drink
* If you didn't hear their drink choice clearly, immediately ask for clarification while providing options: "I didn't hear that properly, could you please repeat? We have Coke, Pepsi, Sprite, or bottled water available."
* NEVER sit idle after asking about drinks - always maintain conversation flow

4. Order Confirmation:
* Objective: Ensure 100% accuracy before finalizing.
* Process: Read the complete order back clearly and item by item.
* Phrasing: "Okay, so just to confirm, I have a large pepperoni pizza and an order of garlic knots. Is that all correct?"

5. Finalizing the Order:
* Objective: Gather the customer's name for the order.
* Process: Once the order is confirmed, ask for their name. The phone number is captured automatically, so DO NOT ask for it.
* Phrasing: "Perfect. What's the name for the order?"
* IMPORTANT: When they tell you their name in ANY format, IMMEDIATELY call finalize_order() with that name - do NOT ask again or call any other functions
* Accept ANY name format: "John", "My name is Sarah", "It's Mike", "This is Jennifer", "I'm David", etc.
* Extract just the name from their response and call finalize_order() immediately
* Example: Customer says "John" → You say "Got it, John!" and immediately call finalize_order("John")
* Example: Customer says "My name is Sarah" → You say "Got it, Sarah!" and immediately call finalize_order("Sarah")
* Example: Customer says "It's Mike" → You say "Got it, Mike!" and immediately call finalize_order("Mike")
* Example: Customer says "This is Jennifer" → You say "Got it, Jennifer!" and immediately call finalize_order("Jennifer")

6. Closing the Call:
* Objective: End the call on a high note, providing essential information.
* Process: After the order is finalized and submitted, ask if there's anything else you can help with. If the customer says no or indicates they're done, use say_goodbye_and_end_call() to end gracefully.
* Phrasing: "Is there anything else I can help you with today?" Then if they say no: "Perfect! Thank you so much for choosing Jimmy Neno's Pizza! We'll see you soon, and have a wonderful day! Goodbye!"
* IMPORTANT: When saying goodbye, call say_goodbye_and_end_call() - do NOT call any other functions

[ERROR HANDLING & CONTINGENCIES]
Accent & Pronunciation Handling: The agent must accurately understand users regardless of their English accent, dialect, or regional pronunciation. Use advanced speech recognition and natural language understanding that works across all English-speaking regions worldwide.

Unclear Audio/Accent Ambiguity: If you can't confidently understand something due to accent, pronunciation, or unclear audio, ask for clarification politely while keeping the conversation flowing. NEVER assume or process a wrong order due to accent ambiguity.
Examples: 
- "I didn't hear that properly, could you please repeat?"
- "I want to make sure I get this right - could you say that one more time for me?"
- "I didn't quite catch that, could you please repeat that for me?"
- "Let me make sure I have this correct - could you repeat that last part?"

Customizations/Special Requests: Handle these with positive affirmations.
Customer: "Can I get the veggie pizza but with no onions?"
Sofia: "Absolutely. A veggie pizza with no onions. We can definitely do that for you."
Customer Changes Mind: If a customer wants to change an item, be flexible and re-confirm.
Example: "You got it. So, we're swapping the pepperoni for a large cheese pizza instead. Let me just update that for you." Then, re-confirm the full order at the end.
Off-Topic Questions: If asked something you can't answer (e.g., "How late are you open?"), respond with: "I can help you with placing an order. For questions about our hours, you can find that information on our website." Then, gently guide back: "Now, where were we with your order?"

[CRITICAL: NO IDLE SILENCE - KEEP TALKING ALWAYS]
- NEVER sit in silence or pause without talking - always maintain conversation flow
- If you didn't hear something clearly, immediately ask for clarification while keeping energy up
- Examples of what to say when you didn't hear properly (accent-friendly):
  * "I didn't hear that properly, could you please repeat? We have BBQ, Marinara, or Buffalo sauce available."
  * "I want to make sure I get this right - what toppings did you want on your pizza? I have several options here."
  * "Let me make sure I have this correct - what toppings would you like? I want to make sure I add the right ones to your order."
  * "I didn't quite catch that, could you please repeat that for me? We have Coke, Pepsi, Sprite, or bottled water."
  * "I want to make sure I get your drink order right - what did you say? I have several drink options available."
  * "Let me ask about drinks again - what would you like to drink with your meal? I want to make sure I add the right one."
- If you're unsure about any customization, ask again while being engaging and helpful
- Always provide context when asking again - mention what options are available
- Keep the conversation flowing even during clarification requests

[ACCENT & SPEECH RECOGNITION HANDLING]
The agent uses advanced speech recognition and natural language understanding models that are trained or fine-tuned for a broad diversity of English accents worldwide. The agent must accurately understand users regardless of their English accent, dialect, or regional pronunciation. This includes:
- American English (all regions: Southern, Northern, Midwestern, Western, etc.)
- British English (all regions: Received Pronunciation, Cockney, Scottish, Welsh, Irish, etc.)
- Canadian English
- Australian English
- New Zealand English
- South African English
- Indian English
- Caribbean English
- And all other English-speaking regions worldwide

Key Principles:
1. NEVER assume or process a wrong order due to accent ambiguity
2. Always clarify courteously if unsure about any detail
3. Use the standard clarification phrase: "I didn't hear that properly, could you please repeat?"
4. Provide context when asking for clarification (mention available options)
5. Maintain a warm, patient tone when asking for repetition
6. If still unclear after repetition, ask them to spell it out or use different words

Examples of accent-friendly responses:
- "I didn't hear that properly, could you please repeat?"
- "I want to make sure I get this right - could you say that one more time for me?"
- "Let me make sure I have this correct - what did you say?"
- "I didn't quite catch that, could you please repeat that for me?"

[BOUNDARIES & CONSTRAINTS]
DO NOT ask for payment information. This is handled at pickup.
DO NOT make up menu items or prices. If an item is not on the menu, politely inform the customer.
DO NOT express personal opinions or feelings.
DO NOT use apologetic language excessively. Be confident and solution-oriented. For example, instead of "I'm so sorry, I can't do that," say, "While I can't add that topping, I can offer you [alternative]."

[FUNCTION CALL OPTIMIZATION - CRITICAL]
- Use ONLY ONE function call per response - this is mandatory
- NEVER make multiple function calls in a single response
- If you need to do multiple actions, do them one at a time across multiple responses
- Be extremely efficient and direct in your responses
- Examples of what NOT to do: calling add_item AND select_size in the same response
- Examples of what TO do: call add_item, wait for response, then call select_size in next response

[CONVERSATION FLOW & ENGAGEMENT]
Keep the conversation flowing and engaging:
- NEVER leave long pauses or silence while processing. Always keep talking to maintain engagement.
- Use filler phrases during processing: "Let me get that for you...", "Just a moment...", "Perfect, I'm adding that to your order...", "Great choice, let me update that...", "Alright, I'm processing that...", "Got it, just updating your order..."
- If you need to think or process something, say it out loud: "Let me check our menu for that...", "Just making sure I have that right...", "Let me confirm those details..."
- Keep the energy up and maintain a conversational flow even during technical operations.
- If there's any delay, acknowledge it: "Just one second while I get that ready for you..."

[CRITICAL: NO PAUSES AFTER CUSTOMIZATIONS OR NAME COLLECTION]
- After adding ANY customization (sauce, topping, etc.), IMMEDIATELY continue talking. Examples:
  * "Perfect! I've added extra cheese to your pizza. What else can I get for you today?"
  * "Great choice on the BBQ sauce! Is there anything else you'd like to add to your order?"
  * "I've got that pepperoni added. Would you like any other toppings or should we move on to drinks?"
- After asking for the customer's name, IMMEDIATELY follow up with engaging conversation:
  * "Perfect, [Name]! I'm just finalizing your order details here... Your total comes to $X.XX and it'll be ready in about 20-25 minutes. Is there anything else I can help you with today?"
  * "Thanks, [Name]! Let me get this order processed for you... Everything looks great! Your order will be ready for pickup soon."
- NEVER end a response with just "What's the name for the order?" - always add follow-up conversation
- NEVER end a response after customizations without asking what's next or confirming the order

[CRITICAL: RESPONSE PROCESSING - NO REPEAT QUESTIONS]
- When a customer answers your question, PROCESS their answer immediately - do NOT ask the same question again
- If they tell you their name, immediately call finalize_order() with that name
- If they tell you their sauce preference (even if it's just the sauce name like "BBQ", "Buffalo", "Honey Mustard", "Mild"), immediately call add_sauce() with that sauce
- CRITICAL: When user says any sauce name for WINGS (Buffalo, BBQ, Mild, Hot, Ranch, Blue Cheese, Garlic Parm, Honey Mustard), IMMEDIATELY call add_sauce_to_wings(sauce_name)
- For other items with sauce, use add_sauce(get_current_item_id(), sauce_name)
- If they tell you their topping preference, immediately call add_topping() with that topping
- If they tell you their drink preference, immediately call lookup_add_item_to_cart() with that drink
- NEVER ask "What's your name?" twice - if they already told you, use it
- NEVER ask "What toppings would you like?" twice - if they already told you, use it
- NEVER ask "What drink would you like?" twice - if they already told you, use it
- NEVER re-ask for size, toppings, or sauces that the customer already specified in their initial request
- If customer says "Buffalo chicken pizza with extra cheese and large size", process ALL those details immediately
- Always acknowledge their answer: "Got it, [name]!" or "Perfect, I'll add [toppings] to your pizza!" or "Great choice on the [drink]!"

No Over-offering:
- Offer additional items only if the customer asks or if it naturally fits (e.g., "Would you like anything to drink with that?" after the main order, and only once).
- Never sound pushy.

Graceful Removal Handling:
- If the customer wants to remove anything, handle it gracefully and professionally.
- Use remove_customization_by_name() for removing specific toppings/sauces by name.
- Use delete_item() for removing entire items from the cart.
- Use clear_cart() if they want to start over completely.
- Always confirm what was removed and ask if there's anything else they'd like to change.
- Examples: "I'll remove the extra cheese from your pizza" or "I've taken that item off your order"

NOTE:
- Upon user confirmation ("yes," "okay," etc.), immediately proceed to ask for name only and then call finalize_order().
- After finalize_order(), immediately call end_call() to terminate the call.
- Never display any special characters, technical terms, or system notes to the user—be as seamless as possible.
- Avoid excessive function calls—combine related actions where possible.
- Keep conversation flow smooth, natural, and friendly. Minimize robotic or repetitive responses.
- Do not reconfirm or repeat unless the caller insists or requests more confirmation.
- Always end the call after order completion - do not keep the call open.
"""
    
    if current_state == OrderState.TAKING_ORDER:
        return (
            professional_prompt + "\n\n" +
            catalog_text + "\n\n"
            "Role: You are Sofia, a professional AI Voice Assistant for Jimmy Neno's Pizza restaurant. "
            "You are warm, efficient, and always initiate conversations professionally. "
            "When customers ask for the menu or 'what do you have', use get_full_menu() to show ONLY the menu categories, not individual items. For detailed menu requests, use get_detailed_menu() to show all items with names and IDs. "
            "When customers ask for specific categories (like 'pizza only' or 'wings only'), use get_category_menu() to show only that category with available customizations. "
            "When customers ask about pricing for a specific item, use get_item_details() with the item ID to show pricing and customizations. "
            "When customers ask about pricing during ordering, use show_pricing_info() to show their current order with detailed pricing. "
            "If you don't understand an item name clearly, use clarify_item_name() to help find the right item instead of sitting idle. "
            "When reciting menu items, DO NOT say item numbers (e.g. 'number one', '#2', 'pizza 1', 'pizza 2'), only use the item name (e.g. 'Personal Pizza', 'Margherita Pizza'). Never number items when speaking to customers. "
            "To add an item, use the name to look up its id, then if sizes exist, ask for the user's choice. "
            "IMPORTANT: Only ask for customizations (toppings/sauce) if they actually exist in the menu object for that specific item. Check the item's customization data before asking. "
            "For pizza items: only ask for toppings if 'Toppings' exist in customization. "
            "For wings items: only ask for sauce if 'Sauce' exist in customization. "
            "If customizations exist, clearly explain the rules: WINGS = only ONE sauce allowed, PIZZA = UNLIMITED toppings allowed. "
            "Always be proactive in guiding customers through the ordering process. "
            "When customers ask about price or total, use get_price() or get_cart_total() to show current total. "
            "When customers ask about a specific item's price, use get_item_price() to show individual item prices. "
            "When done with one item, ask: 'What else can I get for you today?'"
            "\n\nORDER COMPLETION FLOW:"
            "1. When customer confirms order with 'yes', 'okay', etc., acknowledge only once"
            "2. Ask for customer name only - phone number will be retrieved from call data"
            "3. Use finalize_order() to complete the order with just the customer name"
            "4. After final message, use end_call() to terminate the call"
            "\n\nIMPORTANT: Do not call functions repeatedly. If a function call fails, ask the customer what they want instead of retrying. "
            "Always maintain a professional, helpful tone and guide customers step by step."
        )
    elif current_state == OrderState.CUSTOMIZING:
        return (
            professional_prompt + "\n\n" +
            "CUSTOMIZATION MODE: Help customer customize their item professionally. "
            "Rules: WINGS = only ONE sauce allowed, PIZZA = UNLIMITED toppings allowed. "
            "For sauce selection, use add_sauce() with exact sauce name (e.g., 'Buffalo', 'BBQ', 'Garlic Parm'). "
            "For toppings, use add_topping() with exact topping name (e.g., 'Pepperoni', 'Mushrooms'). "
            "If they want to remove something, use remove_customization_by_name() with the exact name. "
            "Guide them through each required customization step. "
            "When all customizations are complete, say: 'Perfect! What else can I get for you today?' "
            "IMPORTANT: Do not call functions repeatedly. If customization is complete, move to taking order state."
        )
    elif current_state == OrderState.COLLECTING_ITEMS:
        return (
            professional_prompt + "\n\n" +
            "COLLECTING ITEMS MODE: Continue taking the customer's order. "
            "You can add more items using lookup_add_item_to_cart(). "
            "When the customer is done adding items, use process_all_customizations() to handle all customizations at once. "
            "This ensures no items are lost and all customizations are handled properly. "
            "Keep the conversation flowing and be helpful throughout the process."
        )
    else:
        return (
            professional_prompt + "\n\n" + 
            "FINALIZING: Complete the order professionally. "
            "Use finalize_order() to complete with customer name, then use end_call() to terminate. "
            "Always thank the customer warmly and provide clear total before ending the call."
        )

class CustomAgentSession(AgentSession):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.session_id = f"session_{id(self)}"
        self.start_time = asyncio.get_event_loop().time()
        self._last_activity = self.start_time
        self.menu_data = []  # Store raw menu data for ID-based lookup
        self._vad_response_delay = 0.8  # 800ms delay after VAD detects speech end
        self._last_speech_time = 0
        logger.info(f"New session started: {self.session_id}")
    
    def _update_speech_activity(self):
        """Update the last speech time when user is detected speaking"""
        self._last_speech_time = asyncio.get_event_loop().time()
    
    async def on_speech_detected(self):
        """Called when VAD detects user speech - update activity tracking"""
        self._update_speech_activity()
    
    async def _wait_for_vad_silence(self):
        """Wait for VAD to detect speech end, then add response delay"""
        current_time = asyncio.get_event_loop().time()
        time_since_speech = current_time - self._last_speech_time
        
        if time_since_speech < self._vad_response_delay:
            await asyncio.sleep(self._vad_response_delay - time_since_speech)
    
    async def _add_pause_for_options(self, text: str) -> str:
        """Add natural pauses when presenting options to make it more human-like"""
        # Add pauses before listing options
        if "sauces:" in text.lower() or "toppings:" in text.lower() or "sizes:" in text.lower():
            # Add a brief pause before listing options
            text = text.replace("sauces:", "sauces... ")
            text = text.replace("toppings:", "toppings... ")
            text = text.replace("sizes:", "sizes... ")
        
        # Add pauses between multiple options
        if "and" in text and ("sauce" in text or "topping" in text):
            text = text.replace(" and ", "... and ")
        
        return text
    
    async def generate_reply(self, instructions: str = ""):
        try:
            # Wait for VAD silence before responding
            await self._wait_for_vad_silence()
            
            # Update last activity time
            self._last_activity = asyncio.get_event_loop().time()
            
            # Build menu context directly from session menu data (name and ID only)
            if not hasattr(self, '_cached_menu_context') or not self._cached_menu_context:
                if hasattr(self, 'menu_data') and self.menu_data:
                    # Extract only name and ID from raw menu data - optimized
                    self._cached_menu_context = [
                        {"id": item.get('id'), "name": clean_item_name(item.get('short_name') or item.get('name', ''))}
                        for item in self.menu_data
                        if item and item.get('id') and item.get('name')
                    ]
                else:
                    # Fallback to ITEM_CATALOG if session data not available
                    self._cached_menu_context = [{"id": entry["id"], "name": entry["name"]} for entry in ITEM_CATALOG if entry["id"] is not None]
            
            menu_context = self._cached_menu_context
            
            # Simplified state for better performance
            prompt = instructions if instructions else self._agent.instructions

            # Include complete menu context (all items with just name and ID)
            enhanced_prompt = f"{prompt}\n\n[MENU CATALOG]\n{json.dumps(menu_context)}"
            
            # Generate response with timeout and retry logic
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    response = await asyncio.wait_for(
                        super().generate_reply(instructions=enhanced_prompt),
                        timeout=15.0  # Reduced timeout for faster recovery
                    )
                    break
                except asyncio.TimeoutError:
                    logger.warning(f"Response generation timeout in session {self.session_id}, attempt {attempt + 1}")
                    if attempt == max_retries - 1:
                        return "I'm having trouble processing your request. Could you please repeat what you'd like to order?"
                    await asyncio.sleep(1)  # Brief pause before retry
                except Exception as e:
                    logger.error(f"Response generation error in session {self.session_id}, attempt {attempt + 1}: {e}")
                    if attempt == max_retries - 1:
                        return "I'm having trouble processing your request. Could you please repeat what you'd like to order?"
                    await asyncio.sleep(1)  # Brief pause before retry
            
            # Add natural pauses for options
            response = await self._add_pause_for_options(response)
            
            return response
        except Exception as e:
            logger.error(f"Critical error in session {self.session_id}: {str(e)}")
            # Return a simple response that won't cause TTS issues
            return "I apologize, but I'm experiencing a technical issue. Let me help you start fresh. What would you like to order today?"

    async def end_call_gracefully(self):
        """End the call gracefully after order completion"""
        try:
            if hasattr(self, 'room') and self.room:
                logger.info(f"Ending call for session {self.session_id}")
                # Disconnect the room to end the call
                await self.room.disconnect()
                print(f"CALL DISCONNECTED - Session {self.session_id} ended")
            else:
                logger.warning(f"No room available to disconnect for session {self.session_id}")
        except Exception as e:
            logger.error(f"Error ending call for session {self.session_id}: {str(e)}")

def safe_string_conversion(input_value, function_name="unknown"):
    """Safely convert input to string, handling SpeechHandle and other objects"""
    if isinstance(input_value, str):
        return input_value
    
    # Handle SpeechHandle and other objects
    if hasattr(input_value, 'text'):
        return str(input_value.text)
    elif hasattr(input_value, 'content'):
        return str(input_value.content)
    elif hasattr(input_value, 'data'):
        return str(input_value.data)
    else:
        logger.error(f"{function_name} received unexpected type: {type(input_value)}")
        return str(input_value) if input_value is not None else ""

def create_tts_with_fallback():
    """Create TTS with robust fallback mechanism"""
    # Use Deepgram as primary TTS due to ElevenLabs connection issues
    try:
        tts = deepgram.TTS(model="aura-asteria-en")
        logger.info("✅ Using Deepgram TTS (primary)")
        return tts
    except Exception as e:
        logger.error(f"❌ Deepgram TTS failed: {e}")
        # Try ElevenLabs as fallback only if Deepgram fails
        try:
            tts = elevenlabs.TTS(
                api_key="sk_ff6dfb095ad4672281ba683af6413ec3e5e005d59c8302b3",
                voice_id="Sa60UgyWAdxwQkeWeD20",
                model="eleven_multilingual_v2"
            )
            logger.info("✅ Using ElevenLabs TTS as fallback")
            return tts
        except Exception as e2:
            logger.error(f"❌ Both TTS providers failed: {e2}")
            # Last resort - use basic Deepgram
            return deepgram.TTS(model="aura-asteria-en")

async def entrypoint(ctx: JobContext):
    print("Final agent starting...")
    try:
        # Load menu from API first
        await load_menu()
        
        # Fetch raw menu data for session
        raw_menu_data = await fetch_raw_menu_from_api()
        if raw_menu_data and 'menu' in raw_menu_data:
            session_menu_data = raw_menu_data['menu']
            print(f"📊 Fetched {len(session_menu_data)} items from Supabase API")
            
            # Verify all items have required fields
            valid_items = 0
            for item in session_menu_data:
                if item and item.get('id') and item.get('name'):
                    valid_items += 1
            print(f"📊 Valid items with ID and name: {valid_items}")
            
            # Build complete menu context for verification
            complete_context = get_complete_menu_context(raw_menu_data)
            print(f"📋 Complete menu context: {len(complete_context)} items")
            print(f"📋 Sample items: {complete_context[:5] if complete_context else 'None'}")
        else:
            session_menu_data = []
            print("❌ No menu data fetched from API")
        
        await ctx.connect()
        participant = await ctx.wait_for_participant()
        logger.info(f"Call connected: {participant.identity}")

        # Reset global state for new session
        global current_state, user_cart, current_item_customizing, current_size_selection, current_session
        current_state = OrderState.TAKING_ORDER
        user_cart = []
        current_item_customizing = None
        current_size_selection = None
        
        # Store participant info for phone extraction
        participant_metadata = getattr(participant, 'metadata', {})
        if isinstance(participant_metadata, dict):
            participant_phone = participant_metadata.get('phone') or getattr(participant, 'name', '')
        else:
            participant_phone = getattr(participant, 'name', '')
        
        # Clean phone number - remove "Phone " prefix if present
        if participant_phone and participant_phone.startswith('Phone '):
            participant_phone = participant_phone.replace('Phone ', '')
        
        if not participant_phone or participant_phone == participant.identity:
            # Try to extract phone from identity if it looks like a phone number
            identity = participant.identity or ''
            if identity.replace('+', '').replace('-', '').replace('(', '').replace(')', '').replace(' ', '').isdigit():
                participant_phone = identity
            else:
                participant_phone = None
        
        logger.info(f"Session initialized for participant: {participant.identity}, Phone: {participant_phone}")
    except Exception as e:
        logger.error(f"Failed to initialize session: {str(e)}")
        return
    agent = Agent(
        instructions=get_instructions(),
        tools=[
            # Step-by-step ordering flow (primary functions)
            add_item_basic,
            confirm_add_item,
            update_item_size,
            update_item_sauce,
            update_item_toppings,
            get_cart_summary,
            calculate_order_total,
            final_order_review,
            collect_customer_name,
            confirm_name_correct,
            correct_name,
            confirm_and_place_order,
            finalize_order_with_name,
            # Menu handling
            handle_menu_inquiry,
            handle_multiple_items,
            update_item_customization,
            get_full_menu,
            get_detailed_menu,
            get_category_menu,
            get_item_details,
            get_complete_menu_list,
            clarify_item_name,
            # Legacy functions (for compatibility)
            lookup_add_item_to_cart,
            select_size,
            select_size_for_item,
            add_sauce_to_wings,
            add_sauce,
            add_topping,
            delete_customization,
            delete_item,
            clear_cart,
            process_all_customizations,
            show_pricing_info,
            get_recommendations,
            get_price,
            finalize_order,
            say_goodbye_and_end_call
        ]
    )
    session = CustomAgentSession(
        vad=silero.VAD.load(),
        stt=deepgram.STT(
            model="nova-2",  # Fastest model
            language="en-US",
            interim_results=True,
            punctuate=True,
            smart_format=True,
            filler_words=False,  # Disabled for better performance
            endpointing_ms=100,  # Reduced for faster response
            sample_rate=16000
        ),
        llm=openai.LLM(
            model="gpt-4o-mini"  # Higher rate limits, faster, more cost-effective
        ),
        tts=create_tts_with_fallback()
        )
    
    # Set the menu data for this session
    session.menu_data = session_menu_data
    # Store room reference in session for call termination
    session.room = ctx.room
    
    # Store session globally for call termination
    global current_session
    current_session = session
    
    # Store participant phone in session for later use
    session.participant_phone = participant_phone
    
    await session.start(agent=agent, room=ctx.room)
    logger.info("Final agent ready")
    await session.generate_reply(
        instructions="Thank you for calling Jimmy Neno's Pizza! This is Sofia. How can I help you today?"
    )

if __name__ == "__main__":
    print("Initializing Final Agent...")
    logging.basicConfig(level=logging.INFO)
    print("Menu optimized for speed!")
    print("Agent ready for 10/10 performance!")
    cli.run_app(WorkerOptions(
        entrypoint_fnc=entrypoint,
        agent_name="telephony_agent"
    ))

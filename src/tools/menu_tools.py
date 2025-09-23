"""
Menu and item management tools with fuzzy matching
"""
import logging
from livekit.agents import function_tool
from services.menu_service import MenuService
from services.utility_service import UtilityService

logger = logging.getLogger(__name__)

class MenuTools:
    def __init__(self, menu_service: MenuService):
        self.menu_service = menu_service
        self.utility = UtilityService()
    
    @function_tool
    async def manage_menu_and_items(self, action: str, item_name: str = "", category: str = "") -> str:
        """
        Comprehensive menu and item management tool with fuzzy matching.
        Actions: 'get_menu', 'search_items', 'get_item_details', 'get_categories', 'get_suggestions'
        """
        if action == "get_menu":
            return self.menu_service.get_menu_summary()
        
        elif action == "search_items":
            print(f"🔍 FUZZY LOG: MenuTools.search_items called with item_name: '{item_name}'")
            
            if not item_name:
                print("🔍 FUZZY LOG: No item_name provided, asking user for input")
                return "What would you like to search for? Please tell me the name of the item you're looking for."
            
            # Use fuzzy search
            print(f"🔍 FUZZY LOG: Calling fuzzy_search_items for: '{item_name}'")
            matches = self.menu_service.fuzzy_search_items(item_name, limit=5)
            print(f"🔍 FUZZY LOG: fuzzy_search_items returned {len(matches)} matches")
            
            if not matches:
                print(f"🔍 FUZZY LOG: No matches found, getting suggestions for: '{item_name}'")
                suggestions = self.menu_service.get_suggestions(item_name)
                print(f"🔍 FUZZY LOG: get_suggestions returned: {suggestions}")
                
                if suggestions:
                    response = f"I couldn't find '{item_name}'. Did you mean: {', '.join(suggestions[:3])}?"
                    print(f"🔍 FUZZY LOG: Returning suggestion response: {response}")
                    return response
                else:
                    response = f"I couldn't find '{item_name}'. Please try a different search term or ask to see our full menu."
                    print(f"🔍 FUZZY LOG: Returning no-suggestion response: {response}")
                    return response
            
            # Format results
            print(f"🔍 FUZZY LOG: Formatting {len(matches)} matches for display")
            result = f"Here are the items matching '{item_name}':\n\n"
            for i, match in enumerate(matches, 1):
                item = match['item']
                name = match['short_name'] or match['name']
                price = item.get('price', 0)
                category = match['category']
                score = match['score']
                customizations = match.get('customizations', {})
                
                print(f"🔍 FUZZY LOG: Formatting match {i}: '{name}' (score: {score:.3f})")
                print(f"🔍 FUZZY LOG: Customizations for '{name}': {customizations}")
                
                result += f"{i}. **{name}** (ID: {match['id']})\n"
                result += f"   Category: {category}\n"
                result += f"   Price: ${price}\n"
                result += f"   Match: {score:.1%}\n"
                
                # Add customization information
                if customizations:
                    result += f"   Customizations Available:\n"
                    for group_name, options in customizations.items():
                        if options:
                            result += f"     - {group_name}:\n"
                            for option in options:
                                option_name = option.get('name', '')
                                option_price = option.get('price', 0)
                                option_id = option.get('id', '')
                                price_str = f" (+${option_price})" if option_price > 0 else " (Free)"
                                id_str = f" (ID: {option_id})" if option_id else ""
                                result += f"       • {option_name}{price_str}{id_str}\n"
                else:
                    result += f"   Customizations: None\n"
                
                result += "\n"
            
            print(f"🔍 FUZZY LOG: Returning formatted results: {len(result)} characters")
            return result
        
        elif action == "get_item_details":
            print(f"🔍 FUZZY LOG: MenuTools.get_item_details called with item_name: '{item_name}'")
            
            if not item_name:
                print("🔍 FUZZY LOG: No item_name provided for get_item_details")
                return "What item would you like details about?"
            
            # Try fuzzy search first
            print(f"🔍 FUZZY LOG: Trying find_item_fuzzy for: '{item_name}'")
            match = self.menu_service.find_item_fuzzy(item_name)
            
            if not match:
                print(f"🔍 FUZZY LOG: find_item_fuzzy failed, trying exact search for: '{item_name}'")
                # Fallback to exact search
                item = self.menu_service.find_menu_item_by_name(item_name)
                if not item:
                    print(f"🔍 FUZZY LOG: Exact search failed, getting suggestions for: '{item_name}'")
                    suggestions = self.menu_service.get_suggestions(item_name)
                    print(f"🔍 FUZZY LOG: get_suggestions returned: {suggestions}")
                    
                    if suggestions:
                        response = f"I couldn't find '{item_name}'. Did you mean: {', '.join(suggestions[:3])}?"
                        print(f"🔍 FUZZY LOG: Returning suggestion response: {response}")
                        return response
                    else:
                        response = f"I couldn't find '{item_name}'. Please try a different search term."
                        print(f"🔍 FUZZY LOG: Returning no-suggestion response: {response}")
                        return response
                else:
                    print(f"🔍 FUZZY LOG: Exact search found item: '{item.get('name', 'Unknown')}'")
            else:
                print(f"🔍 FUZZY LOG: find_item_fuzzy found item: '{match['name']}' (score: {match['score']:.3f})")
                item = match['item']
            
            # Format detailed information
            name = item.get('short_name') or item.get('name', '')
            price = item.get('price', 0)
            category = item.get('category', '')
            sizes = item.get('sizes', [])
            customizations = item.get('customization', {})
            
            result = f"**{name}** (ID: {item.get('id')})\n"
            result += f"Category: {category}\n"
            result += f"Price: ${price}\n\n"
            
            if sizes:
                result += "Available Sizes:\n"
                for size in sizes:
                    size_name = size.get('name', '')
                    size_price = size.get('price', 0)
                    result += f"- {size_name}: ${size_price}\n"
                result += "\n"
            
            if customizations:
                result += "Customizations Available:\n"
                for custom_type, options in customizations.items():
                    result += f"- {custom_type}:\n"
                    for option in options:
                        opt_name = option.get('name', '')
                        opt_price = option.get('price', 0)
                        opt_id = option.get('id', '')
                        price_str = f" (+${opt_price})" if opt_price > 0 else " (Free)"
                        id_str = f" (ID: {opt_id})" if opt_id else ""
                        result += f"  - {opt_name}{price_str}{id_str}\n"
            
            return result
        
        elif action == "get_categories":
            categories = self.menu_service.get_menu_categories()
            return f"Our menu categories are: {', '.join(categories)}"
        
        elif action == "get_suggestions":
            print(f"🔍 FUZZY LOG: MenuTools.get_suggestions called with item_name: '{item_name}'")
            
            if not item_name:
                print("🔍 FUZZY LOG: No item_name provided for get_suggestions")
                return "What are you looking for? I can suggest some items."
            
            print(f"🔍 FUZZY LOG: Calling get_suggestions for: '{item_name}'")
            suggestions = self.menu_service.get_suggestions(item_name)
            print(f"🔍 FUZZY LOG: get_suggestions returned: {suggestions}")
            
            if suggestions:
                response = f"Here are some suggestions for '{item_name}': {', '.join(suggestions)}"
                print(f"🔍 FUZZY LOG: Returning suggestions response: {response}")
                return response
            else:
                response = f"I couldn't find any suggestions for '{item_name}'. Please try a different search term."
                print(f"🔍 FUZZY LOG: Returning no-suggestions response: {response}")
                return response
        
        else:
            return f"Unknown action: {action}. Available actions: get_menu, search_items, get_item_details, get_categories, get_suggestions"
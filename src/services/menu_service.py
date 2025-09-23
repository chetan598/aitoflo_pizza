"""
Menu service for handling menu data and API calls with fuzzy matching
"""
import json
import logging
import aiohttp
import re
from typing import Dict, List, Optional, Tuple
from difflib import SequenceMatcher
from config.settings import SUPABASE_URL, SUPABASE_HEADERS

logger = logging.getLogger(__name__)

class MenuService:
    def __init__(self):
        self.menu_data: Optional[List[Dict]] = None
        self._search_index: Optional[List[Dict]] = None
    
    async def fetch_menu_from_api(self) -> Optional[List[Dict]]:
        """Fetch menu from Supabase API"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    SUPABASE_URL,
                    headers=SUPABASE_HEADERS,
                    json={"name": "Functions"}
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        if "menu" in data and isinstance(data["menu"], list):
                            self.menu_data = data["menu"]
                            self._build_search_index() 
                            print(self.menu_data) # Build fuzzy search index
                            return self.menu_data
            return None
        except Exception as e:
            logger.error(f"Error fetching menu: {str(e)}")
            return None
    
    def _build_search_index(self):
        """Build searchable index with normalized names for fuzzy matching"""
        if not self.menu_data:
            print("🔍 FUZZY LOG: No menu data available for building search index")
            return
        
        print(f"🔍 FUZZY LOG: Building search index for {len(self.menu_data)} menu items")
        self._search_index = []
        
        for i, item in enumerate(self.menu_data):
            if not item:
                print(f"🔍 FUZZY LOG: Skipping empty item at index {i}")
                continue
                
            # Create multiple searchable variations
            name = item.get('name', '')
            short_name = item.get('short_name', '')
            category = item.get('category', '')
            
            print(f"🔍 FUZZY LOG: Processing item {i+1}: '{name}' (short: '{short_name}', category: '{category}')")
            
            search_terms = []
            
            # Original names
            if name:
                search_terms.append(name.lower())
                print(f"🔍 FUZZY LOG: Added full name: '{name.lower()}'")
            if short_name:
                search_terms.append(short_name.lower())
                print(f"🔍 FUZZY LOG: Added short name: '{short_name.lower()}'")
            
            # Split and add individual words
            for term in [name, short_name]:
                if term:
                    words = re.findall(r'\b\w+\b', term.lower())
                    search_terms.extend(words)
                    print(f"🔍 FUZZY LOG: Added individual words from '{term}': {words}")
            
            # Add category as search term
            if category:
                search_terms.append(category.lower())
                print(f"🔍 FUZZY LOG: Added category: '{category.lower()}'")
                # Add category words
                cat_words = re.findall(r'\b\w+\b', category.lower())
                search_terms.extend(cat_words)
                print(f"🔍 FUZZY LOG: Added category words: {cat_words}")
            
            # Remove duplicates and create final search terms
            final_search_terms = list(set(search_terms))
            print(f"🔍 FUZZY LOG: Final search terms for '{name}': {final_search_terms}")
            
            self._search_index.append({
                'item': item,
                'search_terms': final_search_terms,
                'id': item.get('id'),
                'name': name,
                'short_name': short_name,
                'category': category
            })
        
        print(f"🔍 FUZZY LOG: Search index built with {len(self._search_index)} items")
    
    def fuzzy_search_items(self, query: str, limit: int = 5, min_score: float = 0.3) -> List[Dict]:
        """
        Find menu items using fuzzy matching
        
        Args:
            query: User's search query
            limit: Maximum number of results to return
            min_score: Minimum similarity score (0-1)
        
        Returns:
            List of matching items with scores and metadata
        """
        print(f"🔍 FUZZY LOG: Starting fuzzy search for query: '{query}' (limit: {limit}, min_score: {min_score})")
        
        if not query or not self._search_index:
            print("🔍 FUZZY LOG: No query or search index available")
            return []
        
        query_lower = query.lower().strip()
        print(f"🔍 FUZZY LOG: Normalized query: '{query_lower}'")
        print(f"🔍 FUZZY LOG: Searching through {len(self._search_index)} indexed items")
        
        matches = []
        
        for i, index_item in enumerate(self._search_index):
            item_name = index_item['name']
            print(f"🔍 FUZZY LOG: Checking item {i+1}: '{item_name}'")
            print(f"🔍 FUZZY LOG: Search terms for this item: {index_item['search_terms']}")
            
            best_score = 0
            best_match_type = ""
            best_term = ""
            
            # Check against all search terms
            for j, term in enumerate(index_item['search_terms']):
                print(f"🔍 FUZZY LOG:   Checking term {j+1}: '{term}'")
                
                # Exact match (highest priority)
                if term == query_lower:
                    score = 1.0
                    match_type = "exact"
                    print(f"🔍 FUZZY LOG:   ✅ EXACT MATCH! Score: {score}")
                # Starts with query
                elif term.startswith(query_lower):
                    score = 0.9
                    match_type = "starts_with"
                    print(f"🔍 FUZZY LOG:   ✅ STARTS WITH! Score: {score}")
                # Contains query
                elif query_lower in term:
                    score = 0.8
                    match_type = "contains"
                    print(f"🔍 FUZZY LOG:   ✅ CONTAINS! Score: {score}")
                # Fuzzy similarity
                else:
                    score = SequenceMatcher(None, query_lower, term).ratio()
                    match_type = "fuzzy"
                    print(f"🔍 FUZZY LOG:   🔍 Fuzzy similarity: {score:.3f}")
                
                if score > best_score:
                    best_score = score
                    best_match_type = match_type
                    best_term = term
                    print(f"🔍 FUZZY LOG:   🎯 New best match: '{term}' ({match_type}) = {score:.3f}")
            
            print(f"🔍 FUZZY LOG: Best match for '{item_name}': '{best_term}' ({best_match_type}) = {best_score:.3f}")
            
            # Only include matches above minimum score
            if best_score >= min_score:
                print(f"🔍 FUZZY LOG: ✅ '{item_name}' qualifies (score {best_score:.3f} >= {min_score})")
                
                # Extract customization information
                item_data = index_item['item']
                customizations = item_data.get('customization', {})
                customization_info = {}
                
                if customizations:
                    print(f"🔍 FUZZY LOG: Processing customizations for '{item_name}': {customizations}")
                    
                    # Process each customization group
                    for group_name, options in customizations.items():
                        if options and isinstance(options, list):
                            group_options = []
                            for option in options:
                                if isinstance(option, dict):
                                    option_info = {
                                        'name': option.get('name', ''),
                                        'price': option.get('price', 0),
                                        'id': option.get('id', '')
                                    }
                                    group_options.append(option_info)
                                else:
                                    group_options.append({'name': str(option), 'price': 0, 'id': ''})
                            
                            customization_info[group_name] = group_options
                            print(f"🔍 FUZZY LOG: Added {group_name} customizations: {len(group_options)} options")
                
                matches.append({
                    'item': index_item['item'],
                    'score': best_score,
                    'match_type': best_match_type,
                    'id': index_item['id'],
                    'name': index_item['name'],
                    'short_name': index_item['short_name'],
                    'category': index_item['category'],
                    'customizations': customization_info
                })
            else:
                print(f"🔍 FUZZY LOG: ❌ '{item_name}' rejected (score {best_score:.3f} < {min_score})")
        
        print(f"🔍 FUZZY LOG: Found {len(matches)} qualifying matches")
        
        # Sort by score (highest first) and return top results
        matches.sort(key=lambda x: x['score'], reverse=True)
        final_results = matches[:limit]
        
        print(f"🔍 FUZZY LOG: Returning top {len(final_results)} results:")
        for i, match in enumerate(final_results):
            print(f"🔍 FUZZY LOG:   {i+1}. '{match['name']}' - {match['match_type']} ({match['score']:.3f})")
        
        return final_results
    
    def find_item_fuzzy(self, query: str, min_score: float = 0.6) -> Optional[Dict]:
        """Find the single best matching item using fuzzy search"""
        print(f"🔍 FUZZY LOG: find_item_fuzzy called with query: '{query}', min_score: {min_score}")
        matches = self.fuzzy_search_items(query, limit=1, min_score=min_score)
        
        if matches:
            result = matches[0]
            print(f"🔍 FUZZY LOG: find_item_fuzzy found: '{result['name']}' (score: {result['score']:.3f})")
            return result
        else:
            print(f"🔍 FUZZY LOG: find_item_fuzzy found no matches for: '{query}'")
            return None
    
    def get_item_by_id(self, item_id: str) -> Optional[Dict]:
        """Get item by exact ID"""
        if not self.menu_data:
            return None
        
        for item in self.menu_data:
            if str(item.get('id')) == str(item_id):
                return item
        return None
    
    def get_suggestions(self, query: str, limit: int = 3) -> List[str]:
        """Get suggested item names based on partial query"""
        print(f"🔍 FUZZY LOG: get_suggestions called with query: '{query}', limit: {limit}")
        matches = self.fuzzy_search_items(query, limit=limit, min_score=0.2)
        print(f"🔍 FUZZY LOG: get_suggestions found {len(matches)} matches")
        
        suggestions = []
        
        for i, match in enumerate(matches):
            # Prefer short_name if available, otherwise use name
            suggestion = match['short_name'] or match['name']
            print(f"🔍 FUZZY LOG: Processing suggestion {i+1}: '{suggestion}' (from match: '{match['name']}')")
            
            if suggestion not in suggestions:
                suggestions.append(suggestion)
                print(f"🔍 FUZZY LOG: Added suggestion: '{suggestion}'")
            else:
                print(f"🔍 FUZZY LOG: Skipped duplicate suggestion: '{suggestion}'")
        
        print(f"🔍 FUZZY LOG: get_suggestions returning {len(suggestions)} suggestions: {suggestions}")
        return suggestions
    
    def find_menu_item_by_name(self, item_name: str) -> Optional[Dict]:
        """Find menu item by name (exact match - kept for backward compatibility)"""
        if not self.menu_data:
            return None
        
        item_name_lower = item_name.lower()
        for item in self.menu_data:
            if not item:
                continue
            if (item.get('name', '').lower() == item_name_lower or 
                item.get('short_name', '').lower() == item_name_lower):
                return item
        return None
    
    def get_menu_categories(self) -> List[str]:
        """Get all menu categories"""
        if not self.menu_data:
            return []
        
        categories = set()
        for item in self.menu_data:
            if item and item.get('category'):
                categories.add(item['category'])
        return sorted(list(categories))
    
    def get_items_by_category(self, category: str) -> List[Dict]:
        """Get items by category"""
        if not self.menu_data:
            return []
        
        items = []
        for item in self.menu_data:
            if item and item.get('category', '').lower() == category.lower():
                items.append(item)
        return items
    
    def get_menu_summary(self, max_items_per_category: int = 5) -> str:
        """Get a summary of the menu"""
        if not self.menu_data:
            return "I'm sorry, I'm having trouble loading our menu right now."
        
        # Group items by category
        categories = {}
        for item in self.menu_data:
            if not item:
                continue
            cat = item.get('category', 'Other')
            if cat not in categories:
                categories[cat] = []
            categories[cat].append(item)
        
        menu_text = "Here's our menu:\n"
        for cat, items in categories.items():
            menu_text += f"\n{cat}:\n"
            for item in items[:max_items_per_category]:
                name = item.get('short_name') or item.get('name', '')
                menu_text += f"- {name}\n"
            if len(items) > max_items_per_category:
                menu_text += f"... and {len(items) - max_items_per_category} more items\n"
        
        return menu_text
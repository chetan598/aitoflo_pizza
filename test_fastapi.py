#!/usr/bin/env python3
"""
Test script for FastAPI Pizza Ordering Agent
"""
import asyncio
import json
import httpx
import websockets
from typing import Dict, Any

BASE_URL = "http://localhost:8000"
WS_URL = "ws://localhost:8000"

class PizzaAPITester:
    def __init__(self):
        self.session_id = None
        self.client = httpx.AsyncClient(base_url=BASE_URL)
    
    async def test_health_check(self):
        """Test health check endpoint"""
        print("🔍 Testing health check...")
        response = await self.client.get("/health")
        print(f"✅ Health check: {response.json()}")
    
    async def test_menu_endpoints(self):
        """Test menu-related endpoints"""
        print("\n🔍 Testing menu endpoints...")
        
        # Get menu
        response = await self.client.get("/menu")
        menu_data = response.json()
        print(f"✅ Menu loaded: {len(menu_data['menu'])} items")
        
        # Get categories
        response = await self.client.get("/menu/categories")
        categories = response.json()['categories']
        print(f"✅ Categories: {categories}")
        
        # Search menu
        search_data = {"query": "pizza", "limit": 3}
        response = await self.client.post("/menu/search", json=search_data)
        search_results = response.json()
        print(f"✅ Search results: {search_results['total_found']} items found")
        
        if search_results['items']:
            item_id = search_results['items'][0]['id']
            # Get item details
            response = await self.client.get(f"/menu/item/{item_id}")
            item_details = response.json()
            print(f"✅ Item details: {item_details['item']['name']}")
    
    async def test_order_management(self):
        """Test order management endpoints"""
        print("\n🔍 Testing order management...")
        
        # First, get a menu item to add
        response = await self.client.post("/menu/search", json={"query": "pizza", "limit": 1})
        search_results = response.json()
        
        if not search_results['items']:
            print("❌ No menu items found for testing")
            return
        
        item = search_results['items'][0]
        item_id = item['id']
        
        # Add item to cart
        add_data = {
            "item_id": item_id,
            "quantity": 2,
            "customizations": ["extra cheese"]
        }
        response = await self.client.post("/order/add-item", json=add_data)
        add_result = response.json()
        print(f"✅ Added item: {add_result['message']}")
        
        # Get cart
        response = await self.client.get("/order/cart")
        cart = response.json()
        print(f"✅ Cart total: ${cart['total']:.2f}")
        print(f"✅ Cart items: {len(cart['cart_items'])}")
        
        # Update quantity
        update_data = {
            "item_name": add_result['cart_item']['itemName'],
            "quantity": 3
        }
        response = await self.client.put("/order/update-quantity", json=update_data)
        update_result = response.json()
        print(f"✅ Updated quantity: {update_result['message']}")
        
        # Get updated cart
        response = await self.client.get("/order/cart")
        cart = response.json()
        print(f"✅ Updated cart total: ${cart['total']:.2f}")
    
    async def test_customer_info(self):
        """Test customer information endpoints"""
        print("\n🔍 Testing customer info...")
        
        customer_data = {
            "name": "John Doe",
            "phone": "+1234567890",
            "address": "123 Main St, City, State"
        }
        response = await self.client.post("/customer/info", json=customer_data)
        customer_result = response.json()
        print(f"✅ Customer info updated: {customer_result['message']}")
    
    async def test_chat_endpoint(self):
        """Test chat endpoint"""
        print("\n🔍 Testing chat endpoint...")
        
        chat_data = {
            "message": "What's on your menu?",
            "session_id": self.session_id
        }
        response = await self.client.post("/chat", json=chat_data)
        chat_result = response.json()
        print(f"✅ Chat response: {chat_result['response'][:100]}...")
    
    async def test_websocket_chat(self):
        """Test WebSocket chat functionality"""
        print("\n🔍 Testing WebSocket chat...")
        
        try:
            async with websockets.connect(f"{WS_URL}/ws/test_session") as websocket:
                # Receive welcome message
                welcome = await websocket.recv()
                welcome_data = json.loads(welcome)
                print(f"✅ WebSocket welcome: {welcome_data['content'][:100]}...")
                
                # Send a message
                message = {
                    "message": "I want to order a pizza"
                }
                await websocket.send(json.dumps(message))
                
                # Receive response
                response = await websocket.recv()
                response_data = json.loads(response)
                print(f"✅ WebSocket response: {response_data['content'][:100]}...")
                
        except Exception as e:
            print(f"❌ WebSocket test failed: {e}")
    
    async def test_order_completion(self):
        """Test order completion"""
        print("\n🔍 Testing order completion...")
        
        # First ensure we have items in cart
        response = await self.client.get("/order/cart")
        cart = response.json()
        
        if not cart['cart_items']:
            print("❌ No items in cart for completion test")
            return
        
        # Complete order
        completion_data = {
            "payment_method": "credit_card",
            "special_instructions": "Please deliver to back door"
        }
        response = await self.client.post("/order/complete", json=completion_data)
        completion_result = response.json()
        print(f"✅ Order completed: {completion_result['message']}")
        print(f"✅ Order ID: {completion_result['order_summary']['order_id']}")
    
    async def run_all_tests(self):
        """Run all tests"""
        print("🍕 Starting FastAPI Pizza Agent Tests")
        print("=" * 50)
        
        try:
            await self.test_health_check()
            await self.test_menu_endpoints()
            await self.test_order_management()
            await self.test_customer_info()
            await self.test_chat_endpoint()
            await self.test_websocket_chat()
            await self.test_order_completion()
            
            print("\n✅ All tests completed successfully!")
            
        except Exception as e:
            print(f"\n❌ Test failed: {e}")
        finally:
            await self.client.aclose()

async def main():
    """Main test function"""
    tester = PizzaAPITester()
    await tester.run_all_tests()

if __name__ == "__main__":
    print("Make sure the FastAPI server is running on http://localhost:8000")
    print("Run: python start_fastapi.py")
    print()
    asyncio.run(main())

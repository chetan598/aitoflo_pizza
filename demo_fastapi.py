#!/usr/bin/env python3
"""
Simple demonstration of the FastAPI Pizza Ordering Agent
"""
import asyncio
import httpx
import json

async def demo_pizza_api():
    """Demonstrate the FastAPI pizza ordering system"""
    print("🍕 FastAPI Pizza Ordering Agent Demo")
    print("=" * 50)
    
    # Create a session ID for consistent session management
    import uuid
    session_id = str(uuid.uuid4())
    print(f"Using session ID: {session_id}")
    print()
    
    async with httpx.AsyncClient(base_url="http://localhost:8000") as client:
        try:
            # 1. Health check
            print("1. Health Check:")
            response = await client.get("/health")
            print(f"   Status: {response.json()}")
            print()
            
            # 2. Get menu
            print("2. Menu Overview:")
            response = await client.get("/menu")
            menu_data = response.json()
            print(f"   Total items: {len(menu_data['menu'])}")
            print(f"   Categories: {len(menu_data['menu'])} items available")
            print()
            
            # 3. Search for pizza
            print("3. Search for 'pizza':")
            search_data = {"query": "pizza", "limit": 3}
            response = await client.post("/menu/search", json=search_data)
            search_results = response.json()
            print(f"   Found {search_results['total_found']} items")
            
            if search_results['items']:
                item = search_results['items'][0]
                print(f"   First item: {item['name']} (ID: {item['id']}, Price: ${item['price']})")
                print()
                
                # 4. Add item to cart
                print("4. Adding item to cart:")
                add_data = {
                    "item_id": str(item['id']),  # Convert to string
                    "quantity": 2,
                    "customizations": ["extra cheese"]
                }
                response = await client.post(f"/order/add-item?session_id={session_id}", json=add_data)
                print(f"   Response status: {response.status_code}")
                print(f"   Response text: {response.text}")
                add_result = response.json()
                print(f"   {add_result['message']}")
                print(f"   Item: {add_result['cart_item']['itemName']}")
                print(f"   Price: ${add_result['cart_item']['itemPrice']}")
                print()
                
                # 5. View cart
                print("5. Current cart:")
                response = await client.get(f"/order/cart?session_id={session_id}")
                cart = response.json()
                print(f"   Items in cart: {len(cart['cart_items'])}")
                print(f"   Total: ${cart['total']:.2f}")
                print()
                
                # 6. Update customer info
                print("6. Update customer information:")
                customer_data = {
                    "name": "John Doe",
                    "phone": "+1234567890",
                    "address": "123 Main St, City, State"
                }
                response = await client.post(f"/customer/info?session_id={session_id}", json=customer_data)
                customer_result = response.json()
                print(f"   {customer_result['message']}")
                print()
                
                # 7. Chat with AI
                print("7. AI Chat:")
                chat_data = {
                    "message": "What's in my cart?",
                    "session_id": session_id
                }
                response = await client.post("/chat", json=chat_data)
                chat_result = response.json()
                print(f"   User: {chat_data['message']}")
                print(f"   AI: {chat_result['response']}")
                print()
                
                # 8. Complete order
                print("8. Complete order:")
                completion_data = {
                    "payment_method": "credit_card",
                    "special_instructions": "Please deliver to back door"
                }
                response = await client.post(f"/order/complete?session_id={session_id}", json=completion_data)
                completion_result = response.json()
                print(f"   {completion_result['message']}")
                print(f"   Order ID: {completion_result['order_summary']['order_id']}")
                print(f"   Total: ${completion_result['order_summary']['total']:.2f}")
                print()
                
            else:
                print("   No pizza items found in menu")
            
            print("✅ Demo completed successfully!")
            
        except Exception as e:
            print(f"❌ Demo failed: {e}")

if __name__ == "__main__":
    print("Make sure the FastAPI server is running on http://localhost:8000")
    print("Run: python start_fastapi.py")
    print()
    asyncio.run(demo_pizza_api())

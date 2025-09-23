#!/usr/bin/env python3
"""
Simple test to debug the FastAPI response structure
"""
import asyncio
import httpx
import json

async def test_api():
    async with httpx.AsyncClient(base_url="http://localhost:8000") as client:
        # Test add item with explicit session
        print("Testing add item with session...")
        
        # First, let's see what the actual response looks like
        add_data = {
            "item_id": "2",
            "quantity": 1,
            "customizations": []
        }
        
        try:
            response = await client.post("/order/add-item", json=add_data)
            print(f"Status Code: {response.status_code}")
            print(f"Response Headers: {dict(response.headers)}")
            print(f"Raw Response: {response.text}")
            
            if response.status_code == 200:
                data = response.json()
                print(f"JSON Response: {json.dumps(data, indent=2)}")
            else:
                print(f"Error: {response.text}")
                
        except Exception as e:
            print(f"Exception: {e}")

if __name__ == "__main__":
    asyncio.run(test_api())

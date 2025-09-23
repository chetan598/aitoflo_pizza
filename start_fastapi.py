#!/usr/bin/env python3
"""
Startup script for FastAPI Pizza Ordering Agent
"""
import os
import sys
import uvicorn
from pathlib import Path

# Add src to Python path
current_dir = Path(__file__).parent
src_dir = current_dir / "src"
sys.path.insert(0, str(src_dir))

def main():
    """Start the FastAPI application"""
    print("🍕 Starting FastAPI Pizza Ordering Agent...")
    print("=" * 50)
    
    # Check if .env file exists
    env_file = current_dir / ".env"
    if not env_file.exists():
        print("⚠️  Warning: .env file not found. Using default configuration.")
        print("   Create a .env file with your API keys for full functionality.")
        print()
    
    # Start the server
    try:
        uvicorn.run(
            "fastapi_pizza_agent:app",
            host="0.0.0.0",
            port=8000,
            reload=True,
            log_level="info",
            access_log=True
        )
    except KeyboardInterrupt:
        print("\n🛑 Server stopped by user")
    except Exception as e:
        print(f"❌ Error starting server: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()

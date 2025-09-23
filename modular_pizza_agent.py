"""
Modular Pizza Ordering Agent - Main Entry Point
"""
import sys
import os

# Add src to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from agent import main

if __name__ == "__main__":
    main()

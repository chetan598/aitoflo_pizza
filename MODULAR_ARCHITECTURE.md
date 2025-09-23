# Modular Pizza Ordering Agent

This project has been refactored into a clean, modular architecture with separate files for different concerns.

## Project Structure

```
src/
├── __init__.py
├── agent.py                 # Main agent class and entry point
├── config/
│   ├── __init__.py
│   └── settings.py          # Configuration and constants
├── models/
│   ├── __init__.py
│   └── order_models.py      # Data models and classes
├── services/
│   ├── __init__.py
│   ├── menu_service.py      # Menu data and API operations
│   ├── order_service.py     # Cart and order management
│   └── utility_service.py   # Common utilities and helpers
└── tools/
    ├── __init__.py
    ├── menu_tools.py        # Menu and item management tools
    ├── order_tools.py       # Order item management tools
    ├── customization_tools.py # Customization management tools
    ├── customer_tools.py    # Customer information tools
    └── order_completion_tools.py # Order completion tools
```

## Key Features

### 5 Comprehensive Tools (reduced from 52)

1. **Menu Tools** (`menu_tools.py`)
   - `manage_menu_and_items()` - Get menu, check availability, get item details, get categories

2. **Order Tools** (`order_tools.py`)
   - `manage_order_items()` - Add items, update quantities, remove items, get cart

3. **Customization Tools** (`customization_tools.py`)
   - `manage_customizations()` - Add/remove customizations, list available options

4. **Customer Tools** (`customer_tools.py`)
   - `manage_customer_info()` - Set/get name, contact information

5. **Order Completion Tools** (`order_completion_tools.py`)
   - `complete_order()` - Place order, get summary, confirm, cancel

### Modular Architecture Benefits

- **Separation of Concerns**: Each file has a single responsibility
- **Maintainability**: Easy to find and modify specific functionality
- **Testability**: Individual components can be tested in isolation
- **Scalability**: Easy to add new features without affecting existing code
- **Reusability**: Services and utilities can be reused across different tools

### Services Layer

- **MenuService**: Handles all menu-related operations and API calls
- **OrderService**: Manages cart operations and order calculations
- **UtilityService**: Provides common helper functions

### Models

- **Data Classes**: Clean data structures for orders, items, and sessions
- **Enums**: Type-safe state management
- **Context Management**: Conversation and session state tracking

## Usage

Run the modular agent:
```bash
python modular_pizza_agent.py
```

The agent maintains all the original functionality but with a much cleaner, more maintainable codebase.

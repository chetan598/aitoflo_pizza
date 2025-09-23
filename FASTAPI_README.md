# FastAPI Pizza Ordering Agent

A modern FastAPI-based pizza ordering system with AI-powered menu search, real-time chat, and comprehensive order management.

## Features

- 🍕 **Smart Menu Search**: Fuzzy matching for finding menu items
- 🛒 **Order Management**: Add, update, remove items from cart
- 💬 **Real-time Chat**: WebSocket support for interactive conversations
- 👤 **Customer Management**: Store and manage customer information
- 📱 **RESTful API**: Complete REST API for all operations
- 🔍 **Advanced Search**: Category-based filtering and suggestions

## Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements_fastapi.txt
```

### 2. Environment Setup

Create a `.env` file with your API keys:

```env
# Supabase Configuration
SUPABASE_URL=https://your-supabase-url.com/functions/v1/fetch_menu
SUPABASE_ORDER_URL=https://your-supabase-url.com/functions/v1/post_order
SUPABASE_ANON_KEY=your-supabase-anon-key
RESTAURANT_ID=your-restaurant-id

# Optional: OpenAI for enhanced AI features
OPENAI_API_KEY=your-openai-api-key
```

### 3. Start the Server

```bash
python start_fastapi.py
```

Or directly with uvicorn:

```bash
uvicorn fastapi_pizza_agent:app --host 0.0.0.0 --port 8000 --reload
```

### 4. Access the API

- **API Documentation**: http://localhost:8000/docs
- **Alternative Docs**: http://localhost:8000/redoc
- **Health Check**: http://localhost:8000/health

## API Endpoints

### Menu Operations

- `GET /menu` - Get complete menu
- `GET /menu/categories` - Get all categories
- `POST /menu/search` - Search menu items with fuzzy matching
- `GET /menu/item/{item_id}` - Get specific item details

### Order Management

- `POST /order/add-item` - Add item to cart
- `PUT /order/update-quantity` - Update item quantity
- `DELETE /order/remove-item` - Remove item from cart
- `GET /order/cart` - Get current cart
- `DELETE /order/clear` - Clear entire cart

### Customer & Order Completion

- `POST /customer/info` - Update customer information
- `POST /order/complete` - Complete the order

### Chat & Real-time Communication

- `POST /chat` - Send chat message (REST)
- `WS /ws/{session_id}` - WebSocket for real-time chat

## Usage Examples

### Search Menu Items

```bash
curl -X POST "http://localhost:8000/menu/search" \
  -H "Content-Type: application/json" \
  -d '{"query": "margherita", "limit": 5}'
```

### Add Item to Cart

```bash
curl -X POST "http://localhost:8000/order/add-item" \
  -H "Content-Type: application/json" \
  -d '{
    "item_id": "123",
    "size": "large",
    "quantity": 2,
    "customizations": ["extra cheese", "pepperoni"]
  }'
```

### WebSocket Chat

```javascript
const ws = new WebSocket('ws://localhost:8000/ws/session123');
ws.onmessage = (event) => {
    const data = JSON.parse(event.data);
    console.log('Response:', data.content);
};

// Send a message
ws.send(JSON.stringify({
    message: "I want to order a pizza"
}));
```

## Architecture

### Core Components

1. **FastAPI Application** (`fastapi_pizza_agent.py`)
   - Main application with all endpoints
   - WebSocket support for real-time chat
   - Session management

2. **Services** (from `src/services/`)
   - `MenuService`: Menu data and fuzzy search
   - `OrderService`: Cart and order management
   - `UtilityService`: Helper functions

3. **Models** (`api_models.py`)
   - Pydantic models for request/response validation
   - Type-safe API contracts

4. **Session Management**
   - In-memory session storage
   - WebSocket connection tracking
   - Order state persistence

### Key Features

- **Fuzzy Search**: Intelligent menu item matching using similarity algorithms
- **Session-based**: Each user gets a unique session for order management
- **Real-time Updates**: WebSocket support for instant communication
- **Type Safety**: Full Pydantic validation for all API operations
- **Error Handling**: Comprehensive error handling with meaningful messages

## Development

### Running in Development Mode

```bash
uvicorn fastapi_pizza_agent:app --reload --log-level debug
```

### Testing

```bash
# Install test dependencies
pip install pytest pytest-asyncio httpx

# Run tests (when implemented)
pytest
```

### API Testing

Use the interactive documentation at http://localhost:8000/docs to test all endpoints.

## Production Deployment

### Using Gunicorn

```bash
pip install gunicorn
gunicorn fastapi_pizza_agent:app -w 4 -k uvicorn.workers.UvicornWorker
```

### Using Docker

```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY requirements_fastapi.txt .
RUN pip install -r requirements_fastapi.txt

COPY . .
EXPOSE 8000

CMD ["uvicorn", "fastapi_pizza_agent:app", "--host", "0.0.0.0", "--port", "8000"]
```

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `SUPABASE_URL` | Supabase function URL | Required |
| `SUPABASE_ANON_KEY` | Supabase anonymous key | Required |
| `RESTAURANT_ID` | Restaurant identifier | Required |
| `OPENAI_API_KEY` | OpenAI API key | Optional |

### CORS Configuration

The API is configured to allow all origins in development. For production, update the CORS settings in `fastapi_pizza_agent.py`:

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://yourdomain.com"],  # Production domains
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)
```

## Migration from LiveKit

This FastAPI version provides the same functionality as the original LiveKit agent but with:

- **REST API**: Standard HTTP endpoints instead of WebRTC
- **WebSocket Chat**: Real-time communication without LiveKit dependency
- **Session Management**: In-memory sessions instead of LiveKit rooms
- **Simplified Deployment**: No need for LiveKit infrastructure

## Support

For issues and questions:
1. Check the API documentation at `/docs`
2. Review the logs for error details
3. Ensure all environment variables are properly set
4. Verify Supabase connectivity

## License

This project maintains the same license as the original LiveKit pizza ordering agent.

# Environment Variables Setup

To configure your pizza ordering agent with API keys, create a `.env` file in the root directory with the following variables:

## Required API Keys

```bash
# LiveKit Configuration
LIVEKIT_URL=wss://call-2ap7soq1.livekit.cloud
LIVEKIT_API_KEY=your_livekit_api_key_here
LIVEKIT_API_SECRET=your_livekit_api_secret_here

# OpenAI Configuration
OPENAI_API_KEY=your_openai_api_key_here

# Deepgram Configuration
DEEPGRAM_API_KEY=your_deepgram_api_key_here

# ElevenLabs Configuration
ELEVEN_API_KEY=your_elevenlabs_api_key_here

# Supabase Configuration
SUPABASE_URL=https://obfjfvxwqmhrzsntxkfy.supabase.co/functions/v1/fetch_menu
SUPABASE_ORDER_URL=https://obfjfvxwqmhrzsntxkfy.supabase.co/functions/v1/post_order
SUPABASE_ANON_KEY=sb_publishable_HNp8ZNUXDBMUtBKkHBkOQA_JwjTYZNB
RESTAURANT_ID=8f025919

# Agent Configuration
AGENT_NAME=simplified_pizza_agent
LOG_LEVEL=INFO
```

## How to Get API Keys

1. **OpenAI API Key**: Get from https://platform.openai.com/api-keys
2. **Deepgram API Key**: Get from https://console.deepgram.com/
3. **ElevenLabs API Key**: Get from https://elevenlabs.io/app/settings/api-keys
4. **LiveKit API Keys**: Get from your LiveKit Cloud dashboard
5. **Supabase Keys**: Already configured with working keys

## Setup Instructions

1. Create a `.env` file in the root directory
2. Copy the template above and replace the placeholder values with your actual API keys
3. Run the agent: `python modular_pizza_agent.py dev`

The agent will automatically load these environment variables and use them for authentication.

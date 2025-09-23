"""
Configuration settings for the pizza ordering agent
"""
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# ElevenLabs API Key
ELEVENLABS_API_KEY = os.getenv("ELEVEN_API_KEY", "sk_06adde87eed40d0c21a06d7468e9f0171e80d6408f5afd09")

# OpenAI API Key
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "your-openai-api-key-here")

# Deepgram API Key
DEEPGRAM_API_KEY = os.getenv("DEEPGRAM_API_KEY", "your-deepgram-api-key-here")

# Supabase configuration
SUPABASE_URL = os.getenv("SUPABASE_URL", "https://obfjfvxwqmhrzsntxkfy.supabase.co/functions/v1/fetch_menu")
SUPABASE_ORDER_URL = os.getenv("SUPABASE_ORDER_URL", "https://obfjfvxwqmhrzsntxkfy.supabase.co/functions/v1/post_order")
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY", "sb_publishable_HNp8ZNUXDBMUtBKkHBkOQA_JwjTYZNB")
SUPABASE_HEADERS = {
    "Authorization": f"Bearer {SUPABASE_ANON_KEY}",
    "apikey": SUPABASE_ANON_KEY,
    "Content-Type": "application/json"
}
RESTAURANT_ID = os.getenv("RESTAURANT_ID", "8f025919")

# LiveKit configuration with validation
LIVEKIT_URL = os.getenv("LIVEKIT_URL", "wss://call-2ap7soq1.livekit.cloud")
LIVEKIT_API_KEY = os.getenv("LIVEKIT_API_KEY", "APIKcGU3ubnTxRZ")
LIVEKIT_API_SECRET = os.getenv("LIVEKIT_API_SECRET", "wHcfPWfvW6CSPxp3rYnb8c1dHPefAGXKNihlu4GuM6iC")

# Validate LiveKit configuration to prevent WebRTC string indexing errors
def validate_livekit_config():
    """Validate LiveKit configuration to prevent WebRTC string indexing errors"""
    if not LIVEKIT_API_KEY or len(LIVEKIT_API_KEY) < 8:
        raise ValueError(f"LiveKit API key is too short or empty: '{LIVEKIT_API_KEY}' (length: {len(LIVEKIT_API_KEY) if LIVEKIT_API_KEY else 0})")
    
    if not LIVEKIT_API_SECRET or len(LIVEKIT_API_SECRET) < 8:
        raise ValueError(f"LiveKit API secret is too short or empty: '{LIVEKIT_API_SECRET}' (length: {len(LIVEKIT_API_SECRET) if LIVEKIT_API_SECRET else 0})")
    
    if not LIVEKIT_URL or len(LIVEKIT_URL) < 8:
        raise ValueError(f"LiveKit URL is too short or empty: '{LIVEKIT_URL}' (length: {len(LIVEKIT_URL) if LIVEKIT_URL else 0})")
    
    print(f"✅ LiveKit configuration validated:")
    print(f"   URL: {LIVEKIT_URL}")
    print(f"   API Key: {LIVEKIT_API_KEY[:8]}... (length: {len(LIVEKIT_API_KEY)})")
    print(f"   API Secret: {LIVEKIT_API_SECRET[:8]}... (length: {len(LIVEKIT_API_SECRET)})")

# Validate configuration on import
try:
    validate_livekit_config()
except ValueError as e:
    print(f"❌ LiveKit configuration error: {e}")
    print("Please check your .env file and ensure all LiveKit credentials are properly set.")
    raise

# Agent configuration
AGENT_NAME = os.getenv("AGENT_NAME", "telephony_agent")
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

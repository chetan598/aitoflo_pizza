"""
Main pizza ordering agent with modular architecture
"""
import asyncio
import logging
from livekit.agents import Agent, AgentSession, JobContext, WorkerOptions, cli, AutoSubscribe
try:
    from livekit.plugins import deepgram, openai, silero, elevenlabs
except ImportError as e:
    print(f"Warning: Some plugins failed to import: {e}")
    # Create dummy classes for missing plugins
    class DummyPlugin:
        def __call__(self, *args, **kwargs):
            return None
    
    deepgram = DummyPlugin()
    openai = DummyPlugin()
    silero = DummyPlugin()
    elevenlabs = DummyPlugin()

from config.settings import AGENT_NAME, LOG_LEVEL, OPENAI_API_KEY, DEEPGRAM_API_KEY, ELEVENLABS_API_KEY
from models.order_models import OrderSession
from services.menu_service import MenuService
from services.order_service import OrderService
from tools.menu_tools import MenuTools
from tools.order_tools import OrderTools
from tools.customization_tools import CustomizationTools
from tools.customer_tools import CustomerTools
from tools.order_completion_tools import OrderCompletionTools

logger = logging.getLogger(AGENT_NAME)

class PizzaOrderingAgent:
    def __init__(self):
        self.session = OrderSession()
        self.menu_service = MenuService()
        self.order_service = OrderService()
        
        # Initialize tools
        self.menu_tools = MenuTools(self.menu_service)
        self.order_tools = OrderTools(self.order_service, self.menu_service)
        self.customization_tools = CustomizationTools(self.order_service)
        self.customer_tools = CustomerTools(self.session)
        self.completion_tools = OrderCompletionTools(self.order_service, self.session)
    
    def create_vad_with_fallback(self):
        """Create VAD with fallback options"""
        try:
            if hasattr(silero, 'VAD'):
                return silero.VAD()
            else:
                logger.warning("Silero VAD not available")
                return None
        except Exception as e:
            logger.warning(f"Failed to create Silero VAD: {e}")
            return None
    
    def create_stt_with_fallback(self):
        """Create STT with fallback options"""
        try:
            if hasattr(deepgram, 'STT'):
                return deepgram.STT(api_key=DEEPGRAM_API_KEY)
            else:
                logger.warning("Deepgram STT not available")
                return None
        except Exception as e:
            logger.warning(f"Failed to create Deepgram STT: {e}")
            return None
    
    def create_tts_with_fallback(self):
        """Create TTS with fallback options"""
        try:
            if hasattr(elevenlabs, 'TTS'):
                return elevenlabs.TTS(api_key=ELEVENLABS_API_KEY)
            else:
                logger.warning("ElevenLabs TTS not available")
                return None
        except Exception as e:
            logger.warning(f"Failed to create ElevenLabs TTS: {e}")
            try:
                if hasattr(openai, 'TTS'):
                    return openai.TTS(api_key=OPENAI_API_KEY)
                else:
                    logger.warning("OpenAI TTS not available")
                    return None
            except Exception as e2:
                logger.warning(f"Failed to create OpenAI TTS: {e2}")
                return None
    
    def create_llm_with_fallback(self):
        """Create LLM with fallback options"""
        try:
            if hasattr(openai, 'LLM'):
                return openai.LLM(api_key=OPENAI_API_KEY)
            else:
                logger.warning("OpenAI LLM not available")
                return None
        except Exception as e:
            logger.warning(f"Failed to create OpenAI LLM: {e}")
            return None
    
    async def entrypoint(self, ctx: JobContext):
        """Entry point for the pizza ordering agent"""
        try:
            # Add debugging for WebRTC connection
            from config.settings import LIVEKIT_URL, LIVEKIT_API_KEY
            print(f"🔗 Connecting to LiveKit URL: {LIVEKIT_URL}")
            print(f"🔑 Using API Key: {LIVEKIT_API_KEY[:8]}...")
            logger.info(f"Connecting to LiveKit URL: {LIVEKIT_URL}")
            
            await ctx.connect()
            participant = await ctx.wait_for_participant()
            logger.info(f"Call connected: {participant.identity}")
        except Exception as e:
            print(f"❌ WebRTC connection error: {e}")
            logger.error(f"WebRTC connection error: {e}")
            # Re-raise to let LiveKit handle the error
            raise
        
        # Load menu data
        menu_data = await self.menu_service.fetch_menu_from_api()
        if menu_data:
            self.menu_service.menu_data = menu_data
            self.session.menu_data = menu_data
        
        # Store session reference
        self.session.session_id = f"session_{ctx.room.name}"
        
        # Create agent with tools
        agent = Agent(
            instructions="You are a helpful pizza ordering assistant. Help customers with menu items, take orders, manage customizations, and complete their pizza orders.",
            tools=[
                self.menu_tools.manage_menu_and_items,
                self.order_tools.manage_order_items,
                self.customization_tools.manage_customizations,
                self.customer_tools.manage_customer_info,
                self.completion_tools.complete_order
            ]
        )
        
        # Create and start the session
        session = AgentSession(
            vad=self.create_vad_with_fallback(),
            stt=self.create_stt_with_fallback(),
            tts=self.create_tts_with_fallback(),
            llm=self.create_llm_with_fallback()
        )
        
        await session.start(agent=agent, room=ctx.room)
        logger.info("Pizza ordering agent ready")
        
        # Initial greeting
        await session.generate_reply(
            instructions="Hello! Welcome to our pizza restaurant. I can help you with our menu, take your order, and manage customizations. How can I help you today?"
        )

def main():
    """Main function to run the agent"""
    print("Initializing Modular Pizza Ordering Agent...")
    logging.basicConfig(level=getattr(logging, LOG_LEVEL))
    print("Agent ready with modular architecture!")
    
    agent = PizzaOrderingAgent()
    cli.run_app(WorkerOptions(
        entrypoint_fnc=agent.entrypoint,
        agent_name=AGENT_NAME
    ))

if __name__ == "__main__":
    main()

# Initialize utils package
from functools import lru_cache
from app.config import settings

@lru_cache()
def get_stt_service():
    """Get or create a singleton instance of the STT service."""
    from app.services.stt import DeepgramSTTService
    return DeepgramSTTService(settings.deepgram_api_key)

@lru_cache()
def get_translation_service():
    """Get or create a singleton instance of the translation service."""
    from app.services.translation import OpenAITranslationService
    return OpenAITranslationService(settings.openai_api_key, settings.openai_model)

@lru_cache()
def get_broadcast_service():
    """Get or create a singleton instance of the broadcast service."""
    from app.services.broadcast import BroadcastService
    return BroadcastService()

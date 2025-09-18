import os
from pydantic_settings import BaseSettings
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class Settings(BaseSettings):
    """Application settings."""
    
    # API Keys
    deepgram_api_key: str = os.getenv("DEEPGRAM_API_KEY", "")
    openai_api_key: str = os.getenv("OPENAI_API_KEY", "")
    
    # Redis Configuration
    redis_url: str = os.getenv("REDIS_URL", "redis://localhost:6379")
    
    # Application Settings
    debug: bool = os.getenv("DEBUG", "True").lower() == "true"
    host: str = os.getenv("HOST", "0.0.0.0")
    # Cloud Run sets PORT automatically, so we need to use it
    port: int = int(os.getenv("PORT", "8000"))
    
    # Translation Settings
    source_language: str = "ko"  # Default source language (Korean)
    target_language: str = "en"  # Default target language (English)
    
    # WebSocket Settings
    ws_heartbeat_interval: int = 30  # seconds
    
    # STT Settings
    sample_rate: int = 16000
    channels: int = 1
    encoding: str = "linear16"
    
    # Model Settings
    openai_model: str = "gpt-4o"
    
    class Config:
        env_file = ".env"
        case_sensitive = False

# Create settings instance
settings = Settings()

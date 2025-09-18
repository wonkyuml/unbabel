from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
import time

class AudioMetadata(BaseModel):
    """Metadata for audio chunks."""
    seq: int = Field(..., description="Sequence number of the audio chunk")
    room: str = Field(..., description="Room ID")
    is_final: bool = Field(False, description="Whether this is the final chunk in a sequence")
    format: str = Field("pcm_s16le", description="Audio format")
    sample_rate: int = Field(16000, description="Sample rate in Hz")

class CaptionMessage(BaseModel):
    """Caption message for broadcasting."""
    type: str = Field("caption", description="Message type")
    ts: float = Field(default_factory=time.time, description="Timestamp")
    original: str = Field(..., description="Original text in source language")
    translation: str = Field(..., description="Translated text in target language")

class ConnectionMessage(BaseModel):
    """Connection status message."""
    type: str = Field(..., description="Message type (connection_established, error)")
    room_id: str = Field(..., description="Room ID")
    message: str = Field(..., description="Status message")

class LanguageCommand(BaseModel):
    """Command to change language settings."""
    type: str = Field("set_language", description="Command type")
    language: str = Field(..., description="Target language code")

class TranscriptData(BaseModel):
    """Data from speech-to-text service."""
    text: str = Field(..., description="Transcribed text")
    is_final: bool = Field(..., description="Whether this is a final transcript")
    confidence: float = Field(default=0.0, description="Confidence score")

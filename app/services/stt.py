import logging
import asyncio
import uuid
from typing import Dict, Any, Callable, Optional, List

from deepgram import (
    DeepgramClient,
    LiveTranscriptionEvents,
    LiveOptions,
    DeepgramClientOptions
)

class DeepgramSTTService:
    """Service for handling speech-to-text using Deepgram SDK."""

    def __init__(self, api_key: str):
        """Initialize the STT service.
        
        Args:
            api_key: Deepgram API key
        """
        if not api_key:
            raise ValueError("Deepgram API key is required")
            
        # Log partial API key for debugging
        masked_key = api_key[:4] + "*" * (len(api_key) - 4) if len(api_key) > 4 else "****"
        logging.info(f"Initializing Deepgram with API key: {masked_key}")
        
        # Create client with keepalive option
        config = DeepgramClientOptions(options={"keepalive": "true"})
        self.deepgram = DeepgramClient(api_key, config)
        
        # Store active connections and callbacks
        self.active_sessions: Dict[str, Dict] = {}
        
    async def create_connection(self, on_transcript: Callable[[Dict[str, Any]], None]) -> str:
        """Create a new connection to the STT service.
        
        Args:
            on_transcript: Callback function to handle transcripts
            
        Returns:
            Session ID for the connection
        """
        # Generate a unique session ID
        session_id = str(uuid.uuid4())
        
        # Initialize Deepgram connection
        dg_connection = self.deepgram.listen.live.v("1")
        
        # Define event handlers
        def on_open(client, open_event, **kwargs):
            print(f"Deepgram connection opened: {open_event}")
        
        def on_message(client, result, **kwargs):
            try:
                transcript = result.channel.alternatives[0].transcript
                if len(transcript) > 0:
                    print(f"Transcript received: {transcript}")
                    transcript_data = {
                        "text": transcript,
                        "is_final": True,
                        "confidence": result.channel.alternatives[0].confidence
                    }
                    # Store the callback and transcript data in the session
                    # The main application loop will check for new transcripts
                    if session_id in self.active_sessions:
                        if "pending_transcripts" not in self.active_sessions[session_id]:
                            self.active_sessions[session_id]["pending_transcripts"] = []
                        
                        # Add to pending transcripts
                        self.active_sessions[session_id]["pending_transcripts"].append(transcript_data)
                        print(f"Added transcript to pending queue for session {session_id}")
                    else:
                        print(f"Session {session_id} not found, transcript will be lost")
                else:
                    print("Empty transcript received, ignoring")
            except Exception as e:
                print(f"Error processing transcript: {e}")
                import traceback
                traceback.print_exc()
        
        def on_close(client, close_event, **kwargs):
            print(f"Deepgram connection closed: {close_event}")
        
        def on_error(client, error_event, **kwargs):
            print(f"Deepgram error: {error_event}")
        
        # Register event handlers
        dg_connection.on(LiveTranscriptionEvents.Open, on_open)
        dg_connection.on(LiveTranscriptionEvents.Transcript, on_message)
        dg_connection.on(LiveTranscriptionEvents.Close, on_close)
        dg_connection.on(LiveTranscriptionEvents.Error, on_error)
        
        # Define transcription options
        options = LiveOptions(
            model="nova-2",
            language="ko-KR",
            punctuate=True,
            # No need to specify encoding for WebM - Deepgram auto-detects it
            channels=1,
            sample_rate=16000
        )
        
        # Start the connection
        try:
            connection_started = dg_connection.start(options)
            if connection_started is False:
                logging.error("Failed to start Deepgram connection - returned False")
                raise Exception("Failed to start Deepgram connection")
            logging.info(f"Successfully started Deepgram connection for session {session_id}")
        except Exception as e:
            logging.error(f"Error starting Deepgram connection: {str(e)}")
            raise Exception(f"Failed to start Deepgram connection: {str(e)}")
        
        # Store connection and callback
        self.active_sessions[session_id] = {
            "connection": dg_connection,
            "callback": on_transcript
        }
        
        print(f"Created new STT session: {session_id}")
        return session_id
    
    async def send_audio(self, session_id: str, audio_data: bytes) -> None:
        """Send audio data to Deepgram.
        
        Args:
            session_id: Session ID returned from create_connection
            audio_data: Raw audio bytes
        """
        print(f"Received audio chunk: {len(audio_data)} bytes for session {session_id}")
        
        if session_id not in self.active_sessions:
            print(f"Session {session_id} not found")
            return
        
        # Skip very small chunks (likely metadata or empty frames)
        if len(audio_data) < 100:
            print(f"Skipping small audio chunk: {len(audio_data)} bytes")
            return
        
        try:
            # Get the Deepgram connection
            dg_connection = self.active_sessions[session_id]["connection"]
            
            # Send audio data to Deepgram
            dg_connection.send(audio_data)
            print(f"Sent {len(audio_data)} bytes to Deepgram")
        except Exception as e:
            logging.error(f"Error sending audio data: {str(e)}")
            raise
    
    async def close_connection(self, session_id: str) -> None:
        """Close a connection to the STT service.
        
        Args:
            session_id: Session ID returned from create_connection
        """
        print(f"Closing STT session: {session_id}")
        
        if session_id in self.active_sessions:
            try:
                # Get the Deepgram connection
                dg_connection = self.active_sessions[session_id]["connection"]
                
                # Close the connection
                dg_connection.finish()
                print(f"Closed Deepgram connection for session {session_id}")
            except Exception as e:
                print(f"Error closing Deepgram connection: {e}")
                import traceback
                traceback.print_exc()
            
            # Clean up
            del self.active_sessions[session_id]

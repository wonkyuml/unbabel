from fastapi import APIRouter, WebSocket, WebSocketDisconnect, HTTPException, Depends
from starlette.websockets import WebSocketState
import json
import asyncio
import uuid
from typing import Dict, List, Any

from app.config import settings
from app.services.stt import DeepgramSTTService
from app.services.translation import OpenAITranslationService
from app.services.broadcast import BroadcastService
from app.utils import get_stt_service, get_translation_service, get_broadcast_service
from app.utils.state import active_rooms

router = APIRouter(tags=["broadcast"])

@router.get("/debug/rooms")
async def debug_rooms():
    """Debug endpoint to view active rooms."""
    room_info = {}
    
    for room_id, room_data in active_rooms.items():
        room_info[room_id] = {
            "has_broadcaster": "broadcaster" in room_data,
            "viewer_count": len(room_data.get("viewers", set())),
            "language": room_data.get("language", "unknown")
        }
    
    return {
        "active_rooms": room_info,
        "total_rooms": len(active_rooms)
    }

@router.websocket("/ws/stream/{room_id}")
async def websocket_stream(
    websocket: WebSocket,
    room_id: str,
    stt_service: DeepgramSTTService = Depends(get_stt_service),
    translation_service: OpenAITranslationService = Depends(get_translation_service),
    broadcast_service: BroadcastService = Depends(get_broadcast_service),
):
    await websocket.accept()
    print("INFO:     connection open")
    
    # Initialize room if it doesn't exist
    if room_id not in active_rooms:
        active_rooms[room_id] = {
            "broadcaster": websocket,
            "viewers": set(),
            "language": "ko-KR"  # Default language
        }
        print(f"Created new room: {room_id}")
    else:
        # Update broadcaster websocket
        active_rooms[room_id]["broadcaster"] = websocket
        print(f"Updated broadcaster for room: {room_id}")
    
    # Initialize STT session
    session_id = None
    
    # Create a simple event-based approach
    async def on_transcript(transcript: Dict[str, Any]):
        """Handle transcript from Deepgram."""
        try:
            print(f"Received transcript: {transcript}")
            # Process the transcript directly
            text = transcript.get('text', '')
            if not text.strip():
                print("Empty transcript, ignoring")
                return
                
            print(f"Processing transcript text: '{text}'")
            
            # Translate the text
            print(f"Translating text from {settings.source_language} to {settings.target_language}")
            translated = await translation_service.translate(
                text, 
                settings.source_language, 
                settings.target_language
            )
            print(f"Translation result: '{translated}'")
            
            # Debug room state
            print(f"Room state before broadcast: {active_rooms.get(room_id, {})}")
            print(f"Number of viewers: {len(active_rooms.get(room_id, {}).get('viewers', set()))}")
            
            # Prepare message
            message = {
                "type": "caption",
                "ts": asyncio.get_event_loop().time(),
                "original": text,
                "translation": translated
            }
            print(f"Broadcasting message: {message}")
            
            # Broadcast the original and translated text
            await broadcast_service.broadcast_to_room(
                room_id=room_id,
                message=message
            )
            print(f"Broadcast complete for room: {room_id}")
            
            # Debug check if message was sent
            if room_id in active_rooms and "viewers" in active_rooms[room_id]:
                print(f"Message should have been sent to {len(active_rooms[room_id]['viewers'])} viewers")
            else:
                print("No viewers to receive the message")
                
        except Exception as e:
            print(f"Error handling transcript: {e}")
            import traceback
            traceback.print_exc()
    
    try:
        # Create STT session with Deepgram
        session_id = await stt_service.create_connection(on_transcript)
        print(f"Created STT session: {session_id}")
        
        # Process incoming audio data
        while True:
            try:
                # Check for pending transcripts
                session_data = stt_service.active_sessions.get(session_id, {})
                pending_transcripts = session_data.get("pending_transcripts", [])
                
                if pending_transcripts:
                    # Get the first transcript
                    transcript = pending_transcripts.pop(0)
                    print(f"Processing pending transcript: {transcript}")
                    
                    # Process the transcript
                    await on_transcript(transcript)
                
                # Try to receive audio data with a short timeout
                try:
                    audio_data = await asyncio.wait_for(
                        websocket.receive_bytes(), 
                        timeout=0.1  # Short timeout to check for transcripts frequently
                    )
                    print(f"Received audio data: {len(audio_data)} bytes")
                    
                    # Send to STT service
                    await stt_service.send_audio(session_id, audio_data)
                except asyncio.TimeoutError:
                    # No audio data received, continue to check for transcripts
                    continue
                    
            except WebSocketDisconnect:
                print("WebSocket disconnected")
                break
            except Exception as e:
                print(f"Error processing audio data: {e}")
                import traceback
                traceback.print_exc()
                # Don't break on errors, try to continue
                await asyncio.sleep(0.1)  # Avoid tight loop on errors
    except Exception as e:
        print(f"Error in websocket connection: {e}")
        import traceback
        traceback.print_exc()
    finally:
        # Clean up STT session
        if session_id:
            try:
                await stt_service.close_connection(session_id)
                print(f"Closed STT session: {session_id}")
            except Exception as e:
                print(f"Error closing STT session: {e}")
        
        # Clean up any pending transcripts
        if session_id in stt_service.active_sessions and "pending_transcripts" in stt_service.active_sessions[session_id]:
            stt_service.active_sessions[session_id]["pending_transcripts"] = []
            print("Cleared pending transcripts")
                
        print("WebSocket connection closed")

# End of file

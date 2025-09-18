from fastapi import APIRouter, WebSocket, WebSocketDisconnect, HTTPException
from starlette.websockets import WebSocketState
import json
import asyncio
from typing import Dict, Set, Any

from app.utils.state import active_rooms

router = APIRouter(tags=["viewer"])

@router.websocket("/ws/view/{room_id}")
async def websocket_view(websocket: WebSocket, room_id: str):
    """WebSocket endpoint for viewers to receive translated captions."""
    await websocket.accept()
    
    # Set up ping/pong heartbeat
    ping_task = None
    last_ping_time = asyncio.get_event_loop().time()
    ping_interval = 30  # Send ping every 30 seconds
    pong_timeout = 15   # Wait 15 seconds for pong response
    
    async def send_periodic_pings():
        nonlocal last_ping_time
        try:
            while True:
                # Send ping message
                if websocket.client_state == WebSocketState.CONNECTED:
                    await websocket.send_text("ping")
                    last_ping_time = asyncio.get_event_loop().time()
                
                # Wait for next ping interval
                await asyncio.sleep(ping_interval)
        except asyncio.CancelledError:
            # Task was cancelled, clean up
            return
        except Exception as e:
            print(f"Error in ping task: {e}")
    
    try:
        # Check if room exists
        if room_id not in active_rooms:
            await websocket.send_json({
                "type": "error",
                "message": "Room not found"
            })
            await websocket.close()
            return
        
        # Add viewer to room
        if "viewers" not in active_rooms[room_id]:
            active_rooms[room_id]["viewers"] = set()
        
        active_rooms[room_id]["viewers"].add(websocket)
        
        # Send welcome message
        await websocket.send_json({
            "type": "connection_established",
            "room_id": room_id,
            "message": "Connected to viewing room"
        })
        
        # Start ping task
        ping_task = asyncio.create_task(send_periodic_pings())
        
        # Keep connection alive until disconnect
        while True:
            # Periodically check if room still exists
            if room_id not in active_rooms:
                await websocket.send_json({
                    "type": "error",
                    "message": "Room closed"
                })
                break
            
            # Wait for a message with timeout
            try:
                # Use wait_for with a timeout to detect stale connections
                data = await asyncio.wait_for(
                    websocket.receive_text(),
                    timeout=ping_interval + pong_timeout
                )
                
                # Check for ping/pong messages
                if data == "ping":
                    # Respond to client ping with pong
                    await websocket.send_text("pong")
                    continue
                elif data == "pong":
                    # Client responded to our ping
                    last_ping_time = asyncio.get_event_loop().time()
                    continue
                
                # Handle other viewer commands
                try:
                    command = json.loads(data)
                    
                    # Example: Change target language
                    if command.get("type") == "set_language" and "language" in command:
                        # This would be implemented in a more robust way in production
                        pass
                        
                except json.JSONDecodeError:
                    # Not JSON, ignore
                    pass
                    
            except asyncio.TimeoutError:
                # Check if we've exceeded pong timeout
                current_time = asyncio.get_event_loop().time()
                if current_time - last_ping_time > pong_timeout:
                    print(f"Viewer connection timed out for room {room_id}")
                    break
                
    except WebSocketDisconnect:
        # Remove viewer from room
        if room_id in active_rooms and "viewers" in active_rooms[room_id]:
            active_rooms[room_id]["viewers"].discard(websocket)
    
    except Exception as e:
        # Log error
        print(f"Error in websocket_view: {e}")
        
        # Try to send error message
        if websocket.client_state != WebSocketState.DISCONNECTED:
            try:
                await websocket.send_json({
                    "type": "error",
                    "message": str(e)
                })
            except Exception:
                pass
        
        # Remove viewer from room
        if room_id in active_rooms and "viewers" in active_rooms[room_id]:
            active_rooms[room_id]["viewers"].discard(websocket)
    
    finally:
        # Clean up ping task
        if ping_task and not ping_task.done():
            ping_task.cancel()
            try:
                await ping_task
            except asyncio.CancelledError:
                pass
        
        # Ensure websocket is closed
        if websocket.client_state != WebSocketState.DISCONNECTED:
            await websocket.close()

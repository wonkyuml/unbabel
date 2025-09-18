from fastapi import WebSocket
from starlette.websockets import WebSocketState
from typing import Dict, Set, Any, List
import json
import asyncio

class ConnectionManager:
    """Manager for WebSocket connections."""
    
    def __init__(self):
        """Initialize the connection manager."""
        self.active_connections: Dict[str, Set[WebSocket]] = {}
    
    async def connect(self, websocket: WebSocket, room_id: str) -> None:
        """Connect a WebSocket to a room.
        
        Args:
            websocket: WebSocket connection
            room_id: Room ID
        """
        await websocket.accept()
        
        if room_id not in self.active_connections:
            self.active_connections[room_id] = set()
            
        self.active_connections[room_id].add(websocket)
    
    def disconnect(self, websocket: WebSocket, room_id: str) -> None:
        """Disconnect a WebSocket from a room.
        
        Args:
            websocket: WebSocket connection
            room_id: Room ID
        """
        if room_id in self.active_connections:
            self.active_connections[room_id].discard(websocket)
            
            # Remove room if empty
            if not self.active_connections[room_id]:
                del self.active_connections[room_id]
    
    async def send_personal_message(self, message: Dict[str, Any], websocket: WebSocket) -> None:
        """Send a message to a specific WebSocket.
        
        Args:
            message: Message to send
            websocket: WebSocket connection
        """
        if websocket.client_state != WebSocketState.DISCONNECTED:
            await websocket.send_json(message)
    
    async def broadcast(self, message: Dict[str, Any], room_id: str) -> None:
        """Broadcast a message to all WebSockets in a room.
        
        Args:
            message: Message to broadcast
            room_id: Room ID
        """
        if room_id not in self.active_connections:
            return
            
        disconnected_websockets = set()
        for websocket in self.active_connections[room_id]:
            try:
                if websocket.client_state != WebSocketState.DISCONNECTED:
                    await websocket.send_json(message)
            except Exception:
                disconnected_websockets.add(websocket)
        
        # Remove disconnected websockets
        for websocket in disconnected_websockets:
            self.active_connections[room_id].discard(websocket)
            
        # Remove room if empty
        if room_id in self.active_connections and not self.active_connections[room_id]:
            del self.active_connections[room_id]

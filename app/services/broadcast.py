from typing import Dict, Any, Set
import asyncio
from starlette.websockets import WebSocket, WebSocketState
from app.utils.state import active_rooms

class BroadcastService:
    """Service for broadcasting messages to viewers."""
    
    async def broadcast_to_room(self, room_id: str, message: Dict[str, Any]) -> None:
        """Broadcast a message to all viewers in a room.
        
        Args:
            room_id: Room ID
            message: Message to broadcast
        """
        print(f"Broadcasting to room {room_id}: {message}")
        
        if room_id not in active_rooms:
            print(f"Room {room_id} not found in active_rooms")
            return
        
        if "viewers" not in active_rooms[room_id]:
            print(f"No viewers key in room {room_id}")
            return
        
        # Get viewers
        viewers = active_rooms[room_id]["viewers"]
        print(f"Found {len(viewers)} viewers in room {room_id}")
        
        # Send message to all viewers
        disconnected_viewers = set()
        sent_count = 0
        for viewer in viewers:
            try:
                if viewer.client_state != WebSocketState.DISCONNECTED:
                    await viewer.send_json(message)
                    sent_count += 1
                else:
                    print(f"Viewer already disconnected, marking for removal")
                    disconnected_viewers.add(viewer)
            except Exception as e:
                print(f"Error sending message to viewer: {e}")
                # Mark viewer for removal
                disconnected_viewers.add(viewer)
        
        print(f"Successfully sent message to {sent_count} viewers")
        
        # Remove disconnected viewers
        for viewer in disconnected_viewers:
            active_rooms[room_id]["viewers"].discard(viewer)
            print(f"Removed disconnected viewer from room {room_id}")
        
        print(f"Room {room_id} now has {len(active_rooms[room_id]['viewers'])} viewers")

        # Also send the message to the broadcaster if they exist
        broadcaster = active_rooms[room_id].get("broadcaster")
        if broadcaster:
            try:
                if broadcaster.client_state != WebSocketState.DISCONNECTED:
                    await broadcaster.send_json(message)
                    print(f"Sent message back to broadcaster in room {room_id}")
                else:
                    print(f"Broadcaster in room {room_id} is disconnected.")
            except Exception as e:
                print(f"Error sending message to broadcaster in room {room_id}: {e}")
    
    async def broadcast_to_all_rooms(self, message: Dict[str, Any]) -> None:
        """Broadcast a message to all viewers in all rooms.
        
        Args:
            message: Message to broadcast
        """
        for room_id in active_rooms:
            await self.broadcast_to_room(room_id, message)

from typing import Dict, Any

# In-memory store of active rooms (for MVP)
# In production, use Redis or another distributed store
active_rooms: Dict[str, Dict[str, Any]] = {}

from fastapi import APIRouter, Request, Depends, HTTPException
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
import uuid
from pathlib import Path

router = APIRouter(tags=["pages"])

# Set up templates
templates = Jinja2Templates(directory=Path(__file__).parent.parent.parent / "templates")

@router.get("/", response_class=HTMLResponse)
async def index(request: Request):
    """Landing page with 'Start Broadcast' button."""
    return templates.TemplateResponse(
        "index.html", 
        {"request": request}
    )

@router.get("/broadcast/{room_id}", response_class=HTMLResponse)
async def broadcast_page(request: Request, room_id: str):
    """Broadcaster control panel page."""
    return templates.TemplateResponse(
        "broadcast.html", 
        {
            "request": request, 
            "room_id": room_id
        }
    )

@router.get("/broadcast", response_class=HTMLResponse)
async def create_broadcast(request: Request):
    """Create a new broadcast room and redirect to it."""
    # Generate a unique room ID
    room_id = str(uuid.uuid4())
    
    # Redirect to the broadcast page with the new room ID
    return templates.TemplateResponse(
        "broadcast.html", 
        {
            "request": request, 
            "room_id": room_id
        }
    )

@router.get("/view/{room_id}", response_class=HTMLResponse)
async def view_page(request: Request, room_id: str):
    """Viewer page with live captions."""
    return templates.TemplateResponse(
        "view.html", 
        {
            "request": request, 
            "room_id": room_id
        }
    )

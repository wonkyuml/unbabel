from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import os
from pathlib import Path
from app.middleware import add_https_middleware

from app.config import settings
from app.routes import broadcast, viewer, pages

# Create FastAPI app
app = FastAPI(
    title="Unbabel",
    description="Continuous Automatic Translation Broadcasting App",
    version="0.1.0",
    docs_url="/docs" if settings.debug else None,
    redoc_url="/redoc" if settings.debug else None,
)

# Mount static files
app.mount("/static", StaticFiles(directory=Path(__file__).parent.parent / "static"), name="static")

# Set up templates
templates = Jinja2Templates(directory=Path(__file__).parent.parent / "templates")

# Import the HTTPS middleware
from app.middleware import add_https_middleware

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    # For production, specify exact origins including the Cloud Run URL
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(pages.router)
app.include_router(broadcast.router)
app.include_router(viewer.router)

# Add HTTPS middleware to ensure all URLs use HTTPS
add_https_middleware(app)

# Startup event
@app.on_event("startup")
async def startup_event():
    # Initialize services if needed
    pass

# Shutdown event
@app.on_event("shutdown")
async def shutdown_event():
    # Clean up resources if needed
    pass

if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
    )

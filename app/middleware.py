from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response, HTMLResponse
from fastapi import FastAPI
import os
import re

# Check if we're running in Cloud Run
def is_cloud_run():
    return os.environ.get("K_SERVICE") is not None

class HTTPSRedirectMiddleware(BaseHTTPMiddleware):
    """Middleware to ensure all URLs are using HTTPS in Cloud Run"""
    
    async def dispatch(self, request: Request, call_next):
        # Set the scheme to HTTPS if we're in Cloud Run
        if is_cloud_run() and request.url.scheme == "http":
            request.scope["scheme"] = "https"
        
        response = await call_next(request)
        
        # Only process HTML responses in Cloud Run
        if is_cloud_run() and isinstance(response, HTMLResponse):
            # Get the response body
            body = b""
            async for chunk in response.body_iterator:
                body += chunk
            
            # Decode the body
            body_str = body.decode("utf-8")
            
            # Replace http:// URLs with https:// for static resources
            # This regex looks for http:// URLs that are part of src or href attributes
            body_str = re.sub(r'(src|href)=(["\'])http://', r'\1=\2https://', body_str)
            
            # Create a new response with the modified body
            response = Response(
                content=body_str,
                status_code=response.status_code,
                headers=dict(response.headers),
                media_type=response.media_type
            )
        
        return response

def add_https_middleware(app: FastAPI):
    """Add the HTTPS redirect middleware to the FastAPI app"""
    app.add_middleware(HTTPSRedirectMiddleware)

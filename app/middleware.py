from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response
import json

class FlashMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # Get flash messages from session
        flash_messages = request.session.get('flash_messages', [])
        
        # Clear flash messages after reading
        if 'flash_messages' in request.session:
            del request.session['flash_messages']
        
        # Add flash messages to request state
        request.state.flash_messages = flash_messages
        
        response = await call_next(request)
        return response

def flash(request: Request, message: str, category: str = "info"):
    """Add a flash message to the session"""
    if not hasattr(request.state, 'session'):
        return
    
    flash_messages = request.state.session.get('flash_messages', [])
    flash_messages.append((category, message))
    request.state.session['flash_messages'] = flash_messages
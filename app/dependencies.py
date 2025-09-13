from fastapi import Depends, Request
from app.database import get_db
from app.middleware import flash

def get_flash(request: Request):
    """Dependency to get flash messages"""
    return lambda: flash(request)

def get_template_context(request: Request, db=Depends(get_db)):
    """Dependency to provide template context"""
    return {
        "request": request,
        "db": db,
        "flash": flash(request)
    }
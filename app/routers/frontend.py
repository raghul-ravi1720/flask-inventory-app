from fastapi import APIRouter, Request, Depends
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from app.database import get_db

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")



@router.get("/boms")
async def list_boms(request: Request, db: Session = Depends(get_db)):
    return templates.TemplateResponse("list_bom.html", {"request": request})

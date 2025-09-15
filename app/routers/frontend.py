from fastapi import APIRouter, Request, Depends
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from app.database import get_db

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


@router.get("/boms")
async def list_boms(request: Request, db: Session = Depends(get_db)):
    return templates.TemplateResponse("list_bom.html", {"request": request})

@router.get("/purchase_orders")
async def list_purchase_orders(request: Request, db: Session = Depends(get_db)):
    return templates.TemplateResponse("purchase_orders.html", {"request": request})

@router.get("/company_branches")
async def list_company_branches(request: Request, db: Session = Depends(get_db)):
    return templates.TemplateResponse("company_branches.html", {"request": request})

@router.get("/consignees")
async def list_consignees(request: Request, db: Session = Depends(get_db)):
    return templates.TemplateResponse("consignees.html", {"request": request})
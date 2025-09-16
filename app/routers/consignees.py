from fastapi import APIRouter, Depends, HTTPException, Request, Form, status
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from sqlalchemy.orm import Session
from typing import List

from app.database import get_db
from app import models, schemas
from app.shared import templates

router = APIRouter()

# API Endpoints (for potential future use)
@router.get("/api", response_model=List[schemas.Consignee])
async def get_consignees_api(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    consignees = db.query(models.Consignee).offset(skip).limit(limit).all()
    return consignees

@router.get("/api/{consignee_id}", response_model=schemas.Consignee)
async def get_consignee_api(consignee_id: int, db: Session = Depends(get_db)):
    consignee = db.query(models.Consignee).filter(models.Consignee.id == consignee_id).first()
    if consignee is None:
        raise HTTPException(status_code=404, detail="Consignee not found")
    return consignee

@router.post("/api", response_model=schemas.Consignee)
async def create_consignee_api(consignee: schemas.ConsigneeCreate, db: Session = Depends(get_db)):
    db_consignee = models.Consignee(**consignee.dict())
    db.add(db_consignee)
    db.commit()
    db.refresh(db_consignee)
    return db_consignee

# Frontend Routes
@router.get("", response_class=HTMLResponse)
async def list_consignees(request: Request, db: Session = Depends(get_db)):
    try:
        consignees = db.query(models.Consignee).all()
        print(f"Found {len(consignees)} consignees")
        for consignee in consignees:
            print(f"Consignee: {consignee.id} - {consignee.branch_name}")
            
        return templates.TemplateResponse("consignees.html", {
            "request": request, 
            "consignees": consignees
        })
    except Exception as e:
        print(f"Error fetching consignees: {e}")
        return templates.TemplateResponse("consignees.html", {
            "request": request, 
            "consignees": [],
            "error": f"Error loading consignees: {str(e)}"
        })

@router.get("/add", response_class=HTMLResponse)
async def add_consignee_form(request: Request):
    return templates.TemplateResponse("add_consignee.html", {"request": request})

@router.post("/add")
async def add_consignee(
    request: Request,
    company_name: str = Form(...),
    branch_name: str = Form(...),
    address: str = Form(...),
    city: str = Form(...),
    state: str = Form(...),
    pincode: str = Form(...),
    gst_no: str = Form(...),
    state_code: str = Form(...),
    email: str = Form(...),
    branch_indicator: str = Form(...),
    db: Session = Depends(get_db)
):
    try:
        consignee = models.Consignee(
            company_name=company_name,
            branch_name=branch_name,
            address=address,
            city=city,
            state=state,
            pincode=pincode,
            gst_no=gst_no,
            state_code=state_code,
            email=email,
            branch_indicator=branch_indicator
        )
        db.add(consignee)
        db.commit()
        db.refresh(consignee)
        print(f"Created consignee with ID: {consignee.id}")
        return RedirectResponse(url="/consignees", status_code=status.HTTP_303_SEE_OTHER)
    except Exception as e:
        db.rollback()
        print(f"Error adding consignee: {e}")
        return templates.TemplateResponse("add_consignee.html", {
            "request": request,
            "error": f"Error adding consignee: {str(e)}"
        })

@router.get("/edit/{consignee_id}", response_class=HTMLResponse)
async def edit_consignee_form(request: Request, consignee_id: int, db: Session = Depends(get_db)):
    consignee = db.query(models.Consignee).filter(models.Consignee.id == consignee_id).first()
    if not consignee:
        return RedirectResponse(url="/consignees", status_code=status.HTTP_303_SEE_OTHER)
    
    return templates.TemplateResponse("edit_consignee.html", {
        "request": request, 
        "consignee": consignee
    })

@router.post("/edit/{consignee_id}")
async def update_consignee(
    request: Request,
    consignee_id: int,
    company_name: str = Form(...),
    branch_name: str = Form(...),
    address: str = Form(...),
    city: str = Form(...),
    state: str = Form(...),
    pincode: str = Form(...),
    gst_no: str = Form(...),
    state_code: str = Form(...),
    email: str = Form(...),
    branch_indicator: str = Form(...),
    db: Session = Depends(get_db)
):
    try:
        consignee = db.query(models.Consignee).filter(models.Consignee.id == consignee_id).first()
        if not consignee:
            return RedirectResponse(url="/consignees", status_code=status.HTTP_303_SEE_OTHER)
        
        consignee.company_name = company_name
        consignee.branch_name = branch_name
        consignee.address = address
        consignee.city = city
        consignee.state = state
        consignee.pincode = pincode
        consignee.gst_no = gst_no
        consignee.state_code = state_code
        consignee.email = email
        consignee.branch_indicator = branch_indicator
        
        db.commit()
        return RedirectResponse(url="/consignees", status_code=status.HTTP_303_SEE_OTHER)
    except Exception as e:
        db.rollback()
        consignee = db.query(models.Consignee).filter(models.Consignee.id == consignee_id).first()
        return templates.TemplateResponse("edit_consignee.html", {
            "request": request, 
            "consignee": consignee,
            "error": f"Error updating consignee: {str(e)}"
        })

@router.post("/delete/{consignee_id}")
async def delete_consignee(consignee_id: int, db: Session = Depends(get_db)):
    try:
        consignee = db.query(models.Consignee).filter(models.Consignee.id == consignee_id).first()
        if consignee:
            db.delete(consignee)
            db.commit()
        
        return RedirectResponse(url="/consignees", status_code=status.HTTP_303_SEE_OTHER)
    except Exception as e:
        db.rollback()
        return RedirectResponse(url="/consignees", status_code=status.HTTP_303_SEE_OTHER)
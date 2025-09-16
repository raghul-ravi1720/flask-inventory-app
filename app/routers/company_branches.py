from fastapi import APIRouter, Depends, HTTPException, Request, Form, status
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from sqlalchemy.orm import Session
from typing import List

from app.database import get_db
from app import models, schemas
from app.shared import templates

router = APIRouter()

# API Endpoints (for potential future use)
@router.get("/api", response_model=List[schemas.CompanyBranch])
async def get_company_branches_api(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    company_branches = db.query(models.CompanyBranch).offset(skip).limit(limit).all()
    return company_branches

@router.get("/api/{branch_id}", response_model=schemas.CompanyBranch)
async def get_company_branch_api(branch_id: int, db: Session = Depends(get_db)):
    branch = db.query(models.CompanyBranch).filter(models.CompanyBranch.id == branch_id).first()
    if branch is None:
        raise HTTPException(status_code=404, detail="Company branch not found")
    return branch

@router.post("/api", response_model=schemas.CompanyBranch)
async def create_company_branch_api(branch: schemas.CompanyBranchCreate, db: Session = Depends(get_db)):
    db_branch = models.CompanyBranch(**branch.dict())
    db.add(db_branch)
    db.commit()
    db.refresh(db_branch)
    return db_branch

# Frontend Routes
@router.get("", response_class=HTMLResponse)
async def list_company_branches(request: Request, db: Session = Depends(get_db)):
    try:
        company_branches = db.query(models.CompanyBranch).all()
        print(f"Found {len(company_branches)} company branches")
        for branch in company_branches:
            print(f"Branch: {branch.id} - {branch.branch_name}")
            
        return templates.TemplateResponse("company_branches.html", {
            "request": request, 
            "company_branches": company_branches
        })
    except Exception as e:
        print(f"Error fetching company branches: {e}")
        return templates.TemplateResponse("company_branches.html", {
            "request": request, 
            "company_branches": [],
            "error": f"Error loading company branches: {str(e)}"
        })

@router.get("/add", response_class=HTMLResponse)
async def add_company_branch_form(request: Request):
    return templates.TemplateResponse("add_company_branch.html", {"request": request})

@router.post("/add")
async def add_company_branch(
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
        branch = models.CompanyBranch(
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
        db.add(branch)
        db.commit()
        db.refresh(branch)
        return RedirectResponse(url="/company_branches", status_code=status.HTTP_303_SEE_OTHER)
    except Exception as e:
        db.rollback()
        return templates.TemplateResponse("add_company_branch.html", {
            "request": request,
            "error": f"Error adding company branch: {str(e)}"
        })

@router.get("/edit/{branch_id}", response_class=HTMLResponse)
async def edit_company_branch_form(request: Request, branch_id: int, db: Session = Depends(get_db)):
    branch = db.query(models.CompanyBranch).filter(models.CompanyBranch.id == branch_id).first()
    if not branch:
        return RedirectResponse(url="/company_branches", status_code=status.HTTP_303_SEE_OTHER)
    
    return templates.TemplateResponse("edit_company_branch.html", {
        "request": request, 
        "company_branch": branch
    })

@router.post("/edit/{branch_id}")
async def update_company_branch(
    request: Request,
    branch_id: int,
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
        branch = db.query(models.CompanyBranch).filter(models.CompanyBranch.id == branch_id).first()
        if not branch:
            return RedirectResponse(url="/company_branches", status_code=status.HTTP_303_SEE_OTHER)
        
        branch.company_name = company_name
        branch.branch_name = branch_name
        branch.address = address
        branch.city = city
        branch.state = state
        branch.pincode = pincode
        branch.gst_no = gst_no
        branch.state_code = state_code
        branch.email = email
        branch.branch_indicator = branch_indicator
        
        db.commit()
        return RedirectResponse(url="/company_branches", status_code=status.HTTP_303_SEE_OTHER)
    except Exception as e:
        db.rollback()
        branch = db.query(models.CompanyBranch).filter(models.CompanyBranch.id == branch_id).first()
        return templates.TemplateResponse("edit_company_branch.html", {
            "request": request, 
            "company_branch": branch,
            "error": f"Error updating company branch: {str(e)}"
        })

@router.post("/delete/{branch_id}")
async def delete_company_branch(branch_id: int, db: Session = Depends(get_db)):
    try:
        branch = db.query(models.CompanyBranch).filter(models.CompanyBranch.id == branch_id).first()
        if branch:
            db.delete(branch)
            db.commit()
        
        return RedirectResponse(url="/company_branches", status_code=status.HTTP_303_SEE_OTHER)
    except Exception as e:
        db.rollback()
        return RedirectResponse(url="/company_branches", status_code=status.HTTP_303_SEE_OTHER)
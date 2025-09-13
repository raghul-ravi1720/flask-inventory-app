from fastapi import APIRouter, Depends, HTTPException, Request, Form, status
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session
from typing import List
from app.database import get_db
from app import models
from app.shared import templates
from app.schemas import Dealer, DealerCreate, DealerUpdate
from requests import request
from datetime import datetime

from app.pdf_utils import generate_pdf, create_pdf_response, render_pdf_template
from fastapi import Query
from typing import List, Optional
from fastapi import Form
from typing import List

router = APIRouter()

# API Endpoints
@router.get("/api", response_model=List[Dealer])
async def get_dealers_api(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    dealers = db.query(models.Dealer).offset(skip).limit(limit).all()
    return dealers

@router.get("/api/{dealer_id}", response_model=Dealer)
async def get_dealer_api(dealer_id: int, db: Session = Depends(get_db)):
    dealer = db.query(models.Dealer).filter(models.Dealer.id == dealer_id).first()
    if dealer is None:
        raise HTTPException(status_code=404, detail="Dealer not found")
    return dealer

# Frontend Routes - ORDER IS CRITICAL: More specific routes first
@router.get("/add", response_class=HTMLResponse)
async def add_dealer_form(request: Request):
    return templates.TemplateResponse("add_dealer.html", {"request": request})

@router.get("/edit/{dealer_id}", response_class=HTMLResponse)
async def edit_dealer_form(request: Request, dealer_id: int, db: Session = Depends(get_db)):
    try:
        dealer = db.query(models.Dealer).filter(models.Dealer.id == dealer_id).first()
        if dealer is None:
            return RedirectResponse(url="/dealers", status_code=status.HTTP_303_SEE_OTHER)
        
        return templates.TemplateResponse("edit_dealer.html", {"request": request, "dealer": dealer})
    except Exception as e:
        print(f"Error loading edit form: {e}")
        return RedirectResponse(url="/dealers", status_code=status.HTTP_303_SEE_OTHER)

# Dealer details route - This should render the dealer details page
@router.get("/details/{dealer_id}", response_class=HTMLResponse)
async def dealer_details(request: Request, dealer_id: int, db: Session = Depends(get_db)):
    try:
        dealer = db.query(models.Dealer).filter(models.Dealer.id == dealer_id).first()
        if dealer is None:
            return templates.TemplateResponse("error.html", {
                "request": request, 
                "status_code": 404, 
                "detail": f"Dealer with ID {dealer_id} not found"
            })
        
        # Fetch materials associated with this dealer
        materials = db.query(models.Storage).filter(models.Storage.dealer_id == dealer_id).all()
        
        # Calculate total inventory value
        total_value = sum(
            material.price * material.current_stock 
            for material in materials 
            if material.price and material.current_stock
        )
        
        return templates.TemplateResponse("dealer_details.html", {
            "request": request, 
            "dealer": dealer,
            "materials": materials,
            "total_value": total_value,
            "materials_count": len(materials)
        })
    except Exception as e:
        print(f"Error loading dealer details: {e}")
        return templates.TemplateResponse("error.html", {
            "request": request, 
            "status_code": 500, 
            "detail": f"Error loading dealer details: {str(e)}"
        })
    
# List dealers route
@router.get("", response_class=HTMLResponse)
async def list_dealers(request: Request, db: Session = Depends(get_db)):
    try:
        search_query = request.query_params.get('q', '').strip()
        if search_query:
            dealers = db.query(models.Dealer).filter(models.Dealer.name.ilike(f'%{search_query}%')).all()
        else:
            dealers = db.query(models.Dealer).all()
        
        return templates.TemplateResponse("dealers.html", {
            "request": request, 
            "dealers": dealers,
            "search_query": search_query
        })
    except Exception as e:
        print(f"Error in list_dealers: {e}")
        return templates.TemplateResponse("error.html", {
            "request": request, 
            "status_code": 500, 
            "detail": f"Error loading dealers: {str(e)}"
        })

@router.post("/add")
async def add_dealer(
    request: Request,
    name: str = Form(...),
    address: str = Form(None),
    city: str = Form(None),
    state: str = Form(None),
    country: str = Form(None),
    pincode: str = Form(None),
    telephone: str = Form(None),
    mobile: str = Form(None),
    email: str = Form(None),
    gst_no: str = Form(None),
    bank_name: str = Form(None),
    account_no: str = Form(None),
    ifsc_code: str = Form(None),
    db: Session = Depends(get_db)
):
    try:
        dealer = models.Dealer(
            name=name,
            address=address,
            city=city,
            state=state,
            country=country,
            pincode=pincode,
            telephone=telephone,
            mobile=mobile,
            email=email,
            gst_no=gst_no,
            bank_name=bank_name,
            account_no=account_no,
            ifsc_code=ifsc_code
        )
        
        db.add(dealer)
        db.commit()
        
        return RedirectResponse(url="/dealers", status_code=status.HTTP_303_SEE_OTHER)
    except Exception as e:
        print(f"Error adding dealer: {e}")
        return templates.TemplateResponse("error.html", {
            "request": request, 
            "status_code": 500, 
            "detail": f"Error adding dealer: {str(e)}"
        })

@router.post("/edit/{dealer_id}")
async def update_dealer(
    request: Request,
    dealer_id: int,
    name: str = Form(...),
    address: str = Form(None),
    city: str = Form(None),
    state: str = Form(None),
    country: str = Form(None),
    pincode: str = Form(None),
    telephone: str = Form(None),
    mobile: str = Form(None),
    email: str = Form(None),
    gst_no: str = Form(None),
    bank_name: str = Form(None),
    account_no: str = Form(None),
    ifsc_code: str = Form(None),
    db: Session = Depends(get_db)
):
    try:
        dealer = db.query(models.Dealer).filter(models.Dealer.id == dealer_id).first()
        if dealer is None:
            return templates.TemplateResponse("error.html", {
                "request": request, 
                "status_code": 404, 
                "detail": f"Dealer with ID {dealer_id} not found"
            })
        
        dealer.name = name
        dealer.address = address
        dealer.city = city
        dealer.state = state
        dealer.country = country
        dealer.pincode = pincode
        dealer.telephone = telephone
        dealer.mobile = mobile
        dealer.email = email
        dealer.gst_no = gst_no
        dealer.bank_name = bank_name
        dealer.account_no = account_no
        dealer.ifsc_code = ifsc_code
        
        db.commit()
        
        return RedirectResponse(url="/dealers", status_code=status.HTTP_303_SEE_OTHER)
    except Exception as e:
        print(f"Error updating dealer: {e}")
        return templates.TemplateResponse("error.html", {
            "request": request, 
            "status_code": 500, 
            "detail": f"Error updating dealer: {str(e)}"
        })

@router.post("/delete/{dealer_id}")
async def delete_dealer(dealer_id: int, db: Session = Depends(get_db)):
    try:
        dealer = db.query(models.Dealer).filter(models.Dealer.id == dealer_id).first()
        if dealer is None:
            return templates.TemplateResponse("error.html", {
                "request": request, 
                "status_code": 404, 
                "detail": f"Dealer with ID {dealer_id} not found"
            })
        
        db.delete(dealer)
        db.commit()
        
        return RedirectResponse(url="/dealers", status_code=status.HTTP_303_SEE_OTHER)
    except Exception as e:
        print(f"Error deleting dealer: {e}")
        return templates.TemplateResponse("error.html", {
            "request": request, 
            "status_code": 500, 
            "detail": f"Error deleting dealer: {str(e)}"
        })
    

# Add these routes to your dealers router
@router.get("/export", response_class=HTMLResponse)
async def export_dealers_form(request: Request, db: Session = Depends(get_db)):
    dealers = db.query(models.Dealer).all()
    return templates.TemplateResponse("export_dealers.html", {
        "request": request,
        "dealers": dealers
    })

# Update the export PDF endpoint
@router.post("/export/pdf")
async def export_dealers_pdf(
    request: Request,
    dealer_ids: List[int] = Form([]),
    export_all: bool = Form(False),
    db: Session = Depends(get_db)
):
    try:
        if export_all:
            dealers = db.query(models.Dealer).all()
        elif dealer_ids:
            dealers = db.query(models.Dealer).filter(models.Dealer.id.in_(dealer_ids)).all()
        else:
            return templates.TemplateResponse("error.html", {
                "request": request,
                "status_code": 400,
                "detail": "Please select at least one dealer to export"
            })
        
        # Render HTML template using PDF-specific renderer
        html_content = render_pdf_template("export_dealers_list.html", {
            "dealers": dealers,
            "export_date": datetime.now(),
            "total_count": len(dealers)
        })
        
        # Generate PDF
        pdf_buffer = generate_pdf(html_content)
        if not pdf_buffer:
            return templates.TemplateResponse("error.html", {
                "request": request,
                "status_code": 500,
                "detail": "Failed to generate PDF"
            })
        
        # Create response
        filename = f"dealers_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        return create_pdf_response(pdf_buffer, filename)
        
    except Exception as e:
        print(f"Error generating dealers PDF: {e}")
        return templates.TemplateResponse("error.html", {
            "request": request,
            "status_code": 500,
            "detail": f"Error generating PDF: {str(e)}"
        })
from fastapi import APIRouter, Depends, HTTPException, Request, Form, status
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session
from typing import List
from app.database import get_db
from app import models
from app.shared import templates
from app.schemas import Storage, StorageCreate, StorageUpdate, StorageWithDealer

from app.pdf_utils import generate_pdf, create_pdf_response, render_pdf_template
from fastapi import Query
from typing import Optional
from datetime import datetime
from fastapi import Form


router = APIRouter()

# API Endpoints
@router.get("/api", response_model=List[StorageWithDealer])
async def get_storage_api(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    storages = db.query(models.Storage).offset(skip).limit(limit).all()
    
    # Add dealer information to each storage item
    result = []
    for storage in storages:
        storage_dict = storage.__dict__
        if storage.dealer:
            storage_dict["dealer_name"] = storage.dealer.name
            storage_dict["dealer"] = {"id": storage.dealer.id, "name": storage.dealer.name}
        result.append(storage_dict)
    
    return result

@router.get("/api/{storage_id}", response_model=StorageWithDealer)
async def get_storage_api(storage_id: int, db: Session = Depends(get_db)):
    storage = db.query(models.Storage).filter(models.Storage.id == storage_id).first()
    if storage is None:
        raise HTTPException(status_code=404, detail="Storage item not found")
    
    storage_dict = storage.__dict__
    if storage.dealer:
        storage_dict["dealer_name"] = storage.dealer.name
        storage_dict["dealer"] = {"id": storage.dealer.id, "name": storage.dealer.name}
    
    return storage_dict

@router.post("/api", response_model=Storage)
async def create_storage_api(storage: StorageCreate, db: Session = Depends(get_db)):
    db_storage = models.Storage(**storage.dict())
    db.add(db_storage)
    db.commit()
    db.refresh(db_storage)
    return db_storage

@router.put("/api/{storage_id}", response_model=Storage)
async def update_storage_api(storage_id: int, storage: StorageUpdate, db: Session = Depends(get_db)):
    db_storage = db.query(models.Storage).filter(models.Storage.id == storage_id).first()
    if db_storage is None:
        raise HTTPException(status_code=404, detail="Storage item not found")
    
    for key, value in storage.dict(exclude_unset=True).items():
        setattr(db_storage, key, value)
    
    db.commit()
    db.refresh(db_storage)
    return db_storage

@router.delete("/api/{storage_id}")
async def delete_storage_api(storage_id: int, db: Session = Depends(get_db)):
    storage = db.query(models.Storage).filter(models.Storage.id == storage_id).first()
    if storage is None:
        raise HTTPException(status_code=404, detail="Storage item not found")
    
    db.delete(storage)
    db.commit()
    return {"message": "Storage item deleted successfully"}

# Frontend Routes
@router.get("", response_class=HTMLResponse)
async def list_storage(request: Request, db: Session = Depends(get_db)):
    try:
        search_query = request.query_params.get('q', '').strip()
        if search_query:
            storages = db.query(models.Storage).filter(
                models.Storage.base_name.ilike(f'%{search_query}%') |
                models.Storage.defined_name_with_spec.ilike(f'%{search_query}%') |
                models.Storage.brand.ilike(f'%{search_query}%')
            ).all()
        else:
            storages = db.query(models.Storage).all()
        
        return templates.TemplateResponse("list_storage.html", {
            "request": request, 
            "storages": storages,
            "search_query": search_query
        })
    except Exception as e:
        print(f"Error in list_storage: {e}")
        return templates.TemplateResponse("error.html", {
            "request": request, 
            "status_code": 500, 
            "detail": f"Error loading storage items: {str(e)}"
        })

@router.get("/add", response_class=HTMLResponse)
async def add_storage_form(request: Request, db: Session = Depends(get_db)):
    try:
        dealers = db.query(models.Dealer).all()
        units_list = ["Nos", "Kgs", "mm", "cm", "liters", "meters", "pieces", "packs"]
        
        return templates.TemplateResponse("add_storage.html", {
            "request": request,
            "dealers": dealers,
            "units_list": units_list
        })
    except Exception as e:
        print(f"Error loading add storage form: {e}")
        return RedirectResponse(url="/storage", status_code=status.HTTP_303_SEE_OTHER)

@router.post("/add")
async def add_storage(
    request: Request,
    base_name: str = Form(...),
    defined_name_with_spec: str = Form(None),
    brand: str = Form(None),
    hsn_code: str = Form(None),
    dealer_id: str = Form(None),
    tax: float = Form(0),
    price: float = Form(0),
    current_stock: float = Form(0),
    units: str = Form(None),
    db: Session = Depends(get_db)
):
    try:
        # Convert dealer_id to integer if provided
        dealer_id_int = int(dealer_id) if dealer_id and dealer_id != "None" else None
        
        storage = models.Storage(
            base_name=base_name,
            defined_name_with_spec=defined_name_with_spec,
            brand=brand,
            hsn_code=hsn_code,
            dealer_id=dealer_id_int,
            tax=tax,
            price=price,
            current_stock=current_stock,
            units=units
        )
        
        db.add(storage)
        db.commit()
        
        return RedirectResponse(url="/storage", status_code=status.HTTP_303_SEE_OTHER)
    except Exception as e:
        print(f"Error adding storage: {e}")
        return RedirectResponse(url="/storage", status_code=status.HTTP_303_SEE_OTHER)

@router.get("/edit/{storage_id}", response_class=HTMLResponse)
async def edit_storage_form(request: Request, storage_id: int, db: Session = Depends(get_db)):
    try:
        storage = db.query(models.Storage).filter(models.Storage.id == storage_id).first()
        if storage is None:
            return RedirectResponse(url="/storage", status_code=status.HTTP_303_SEE_OTHER)
        
        dealers = db.query(models.Dealer).all()
        units_list = ["Nos", "Kgs", "mm", "cm", "liters", "meters", "pieces", "packs"]
        
        return templates.TemplateResponse("edit_storage.html", {
            "request": request, 
            "storage": storage,
            "dealers": dealers,
            "units_list": units_list
        })
    except Exception as e:
        print(f"Error loading edit form: {e}")
        return RedirectResponse(url="/storage", status_code=status.HTTP_303_SEE_OTHER)

@router.post("/edit/{storage_id}")
async def update_storage(
    request: Request,
    storage_id: int,
    base_name: str = Form(...),
    defined_name_with_spec: str = Form(None),
    brand: str = Form(None),
    hsn_code: str = Form(None),
    dealer_id: str = Form(None),
    tax: float = Form(0),
    price: float = Form(0),
    current_stock: float = Form(0),
    units: str = Form(None),
    db: Session = Depends(get_db)
):
    try:
        storage = db.query(models.Storage).filter(models.Storage.id == storage_id).first()
        if storage is None:
            return RedirectResponse(url="/storage", status_code=status.HTTP_303_SEE_OTHER)
        
        # Convert dealer_id to integer if provided
        dealer_id_int = int(dealer_id) if dealer_id and dealer_id != "None" else None
        
        storage.base_name = base_name
        storage.defined_name_with_spec = defined_name_with_spec
        storage.brand = brand
        storage.hsn_code = hsn_code
        storage.dealer_id = dealer_id_int
        storage.tax = tax
        storage.price = price
        storage.current_stock = current_stock
        storage.units = units
        
        db.commit()
        
        return RedirectResponse(url="/storage", status_code=status.HTTP_303_SEE_OTHER)
    except Exception as e:
        print(f"Error updating storage: {e}")
        return RedirectResponse(url="/storage", status_code=status.HTTP_303_SEE_OTHER)

@router.post("/delete/{storage_id}")
async def delete_storage(storage_id: int, db: Session = Depends(get_db)):
    try:
        storage = db.query(models.Storage).filter(models.Storage.id == storage_id).first()
        if storage is None:
            return RedirectResponse(url="/storage", status_code=status.HTTP_303_SEE_OTHER)
        
        db.delete(storage)
        db.commit()
        
        return RedirectResponse(url="/storage", status_code=status.HTTP_303_SEE_OTHER)
    except Exception as e:
        print(f"Error deleting storage: {e}")
        return RedirectResponse(url="/storage", status_code=status.HTTP_303_SEE_OTHER)

@router.get("/details/{storage_id}", response_class=HTMLResponse)
async def storage_details(request: Request, storage_id: int, db: Session = Depends(get_db)):
    try:
        storage = db.query(models.Storage).filter(models.Storage.id == storage_id).first()
        if storage is None:
            return templates.TemplateResponse("error.html", {
                "request": request, 
                "status_code": 404, 
                "detail": f"Storage item with ID {storage_id} not found"
            })
        
        return templates.TemplateResponse("storage_details.html", {
            "request": request, 
            "storage": storage
        })
    except Exception as e:
        print(f"Error loading storage details: {e}")
        return templates.TemplateResponse("error.html", {
            "request": request, 
            "status_code": 500, 
            "detail": f"Error loading storage details: {str(e)}"
        })
    
# Add these routes to your storage router
@router.get("/export", response_class=HTMLResponse)
async def export_storage_form(request: Request, db: Session = Depends(get_db)):
    dealers = db.query(models.Dealer).all()
    return templates.TemplateResponse("export_storage.html", {
        "request": request,
        "dealers": dealers
    })

# Update the export PDF endpoint
@router.post("/export/pdf")
async def export_storage_pdf(
    request: Request,
    export_option: str = Form(...),
    dealer_id: Optional[str] = Form(None),  # Change to string to handle empty values
    db: Session = Depends(get_db)
):
    try:
        print(f"Export option: {export_option}, Dealer ID: {dealer_id}")
        
        # Handle dealer_id conversion safely
        dealer_id_int = None
        if dealer_id and dealer_id.strip() and dealer_id != "None":
            try:
                dealer_id_int = int(dealer_id)
            except ValueError:
                print(f"Invalid dealer ID: {dealer_id}")
                return templates.TemplateResponse("error.html", {
                    "request": request,
                    "status_code": 400,
                    "detail": "Invalid dealer ID format"
                })
        
        if export_option == "by_dealer" and dealer_id_int:
            storages = db.query(models.Storage).filter(models.Storage.dealer_id == dealer_id_int).all()
            dealer = db.query(models.Dealer).filter(models.Dealer.id == dealer_id_int).first()
            title = f"Storage Items - {dealer.name if dealer else 'Unknown Dealer'}"
            filename = f"storage_{dealer.name if dealer else 'unknown'}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        elif export_option == "all":
            storages = db.query(models.Storage).all()
            title = "All Storage Items"
            filename = f"storage_all_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        else:
            return templates.TemplateResponse("error.html", {
                "request": request,
                "status_code": 400,
                "detail": "Please select a valid export option"
            })
        
        # Calculate total value
        total_value = 0
        for storage in storages:
            if storage.price and storage.current_stock:
                total_value += storage.price * storage.current_stock
        
        # Render HTML template using PDF-specific renderer
        html_content = render_pdf_template("export_storage_list.html", {
            "storages": storages,
            "title": title,
            "export_date": datetime.now(),
            "total_count": len(storages),
            "total_value": total_value
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
        return create_pdf_response(pdf_buffer, filename)
        
    except Exception as e:
        print(f"Error generating storage PDF: {e}")
        import traceback
        traceback.print_exc()
        return templates.TemplateResponse("error.html", {
            "request": request,
            "status_code": 500,
            "detail": f"Error generating PDF: {str(e)}"
        })    
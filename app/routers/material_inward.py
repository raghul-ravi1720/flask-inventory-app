from fastapi import APIRouter, Depends, Request, Form, status, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from sqlalchemy.orm import Session, joinedload
from datetime import datetime, date
from typing import List

from app.database import get_db
from app import models
from app.shared import templates

router = APIRouter()

# List all material inwards
@router.get("", response_class=HTMLResponse)
async def list_material_inward(request: Request, db: Session = Depends(get_db)):
    inwards = db.query(models.MaterialInward).order_by(models.MaterialInward.id.desc()).all()
    return templates.TemplateResponse("material_inward.html", {
        "request": request,
        "inwards": inwards
    })

@router.get("/api/po/{po_no}")
def get_po_details(po_no: int, db: Session = Depends(get_db)):
    po = db.query(models.PurchaseOrder).filter(models.PurchaseOrder.po_no == po_no).first()
    if not po:
        raise HTTPException(status_code=404, detail="PO not found")
    
    # Get dealer name from the dealer relationship
    dealer_name = po.dealer.name if po.dealer else None

    total_cost = sum((item.quantity or 0) * (item.price or 0) for item in po.items)
    
    return JSONResponse({
        "po_no": po.po_no,
        "po_date": po.date.strftime('%Y-%m-%d') if po.date else None,
        "dealer_name": dealer_name,
        "total_cost": total_cost
    })

# Add material inward form
@router.get("/add", response_class=HTMLResponse)
async def add_material_inward_form(request: Request, db: Session = Depends(get_db)):
    purchase_orders = db.query(models.PurchaseOrder).all()
    return templates.TemplateResponse("add_material_inward.html", {
        "request": request,
        "purchase_orders": purchase_orders,
        "current_date": date.today()
    })

# Add material inward POST
@router.post("/add")
async def add_material_inward(
    request: Request,
    db: Session = Depends(get_db)
):
    form_data = await request.form()
    try:
        inward = models.MaterialInward(
            po_no=int(form_data.get("po_no")),
            dealer_name=form_data.get("dealer_name"),
            po_date=datetime.strptime(form_data.get("po_date"), "%Y-%m-%d").date() if form_data.get("po_date") else None,
            date_of_inward=datetime.strptime(form_data.get("date_of_inward"), "%Y-%m-%d").date() if form_data.get("date_of_inward") else date.today(),
            bill_no=form_data.get("bill_no"),
            bill_date=datetime.strptime(form_data.get("bill_date"), "%Y-%m-%d").date() if form_data.get("bill_date") else None,
            cost=float(form_data.get("cost") or 0),
            payment_method=form_data.get("payment_method"),
            pending_materials=form_data.get("pending_materials")
        )
        db.add(inward)
        db.commit()
        return RedirectResponse(url="/material_inward", status_code=status.HTTP_303_SEE_OTHER)
    except Exception as e:
        db.rollback()
        print(f"Error adding material inward: {e}")
        
        # Get purchase orders for re-rendering the form
        purchase_orders = db.query(models.PurchaseOrder).all()
        
        return templates.TemplateResponse("add_material_inward.html", {
            "request": request,
            "purchase_orders": purchase_orders,
            "current_date": date.today(),
            "error": f"Error adding material inward: {str(e)}",
            "form_data": dict(form_data)  # Pass form data back to repopulate the form
        })

# View single inward
@router.get("/{inward_id}", response_class=HTMLResponse)
async def view_material_inward(request: Request, inward_id: int, db: Session = Depends(get_db)):
    inward = db.query(models.MaterialInward).filter(models.MaterialInward.id == inward_id).first()
    if not inward:
        return templates.TemplateResponse("error.html", {
            "request": request, "status_code": 404, "detail": "Material inward not found"
        })
    return templates.TemplateResponse("view_material_inward.html", {
        "request": request, "inward": inward
    })

# Edit inward form
@router.get("/edit/{inward_id}", response_class=HTMLResponse)
async def edit_material_inward_form(request: Request, inward_id: int, db: Session = Depends(get_db)):
    inward = db.query(models.MaterialInward).filter(models.MaterialInward.id == inward_id).first()
    purchase_orders = db.query(models.PurchaseOrder).all()
    if not inward:
        return RedirectResponse(url="/material_inward", status_code=status.HTTP_303_SEE_OTHER)
    return templates.TemplateResponse("edit_material_inward.html", {
        "request": request, "inward": inward, "purchase_orders": purchase_orders
    })

# Edit inward POST
@router.post("/edit/{inward_id}")
async def update_material_inward(request: Request, inward_id: int, db: Session = Depends(get_db)):
    form_data = await request.form()
    inward = db.query(models.MaterialInward).filter(models.MaterialInward.id == inward_id).first()
    if not inward:
        return RedirectResponse(url="/material_inward", status_code=status.HTTP_303_SEE_OTHER)

    inward.po_no = int(form_data.get("po_no")) if form_data.get("po_no") else inward.po_no
    inward.dealer_name = form_data.get("dealer_name")
    inward.po_date = datetime.strptime(form_data.get("po_date"), "%Y-%m-%d").date() if form_data.get("po_date") else inward.po_date
    inward.date_of_inward = datetime.strptime(form_data.get("date_of_inward"), "%Y-%m-%d").date() if form_data.get("date_of_inward") else inward.date_of_inward
    inward.bill_no = form_data.get("bill_no")
    inward.bill_date = datetime.strptime(form_data.get("bill_date"), "%Y-%m-%d").date() if form_data.get("bill_date") else inward.bill_date
    inward.cost = float(form_data.get("cost") or 0)
    inward.payment_method = form_data.get("payment_method")
    inward.pending_materials = form_data.get("pending_materials")

    db.commit()
    return RedirectResponse(url="/material_inward", status_code=status.HTTP_303_SEE_OTHER)

# Delete inward
@router.post("/delete/{inward_id}")
async def delete_material_inward(inward_id: int, db: Session = Depends(get_db)):
    inward = db.query(models.MaterialInward).filter(models.MaterialInward.id == inward_id).first()
    if inward:
        db.delete(inward)
        db.commit()
    return RedirectResponse(url="/material_inward", status_code=status.HTTP_303_SEE_OTHER)

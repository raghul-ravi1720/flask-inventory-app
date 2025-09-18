from fastapi import APIRouter, Depends, Request, Form, status, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from sqlalchemy.orm import Session, joinedload
from datetime import datetime, date
from typing import List

from app.database import get_db
from app import models
from app.shared import templates

router = APIRouter()

# List all pending materials
@router.get("", response_class=HTMLResponse)
async def list_pending_materials(request: Request, db: Session = Depends(get_db)):
    pending_materials = db.query(models.PendingMaterial).options(
        joinedload(models.PendingMaterial.purchase_order),
        joinedload(models.PendingMaterial.po_item)
    ).filter(models.PendingMaterial.status.in_(['pending', 'partially_resolved'])).all()
    
    return templates.TemplateResponse("pending_list.html", {
        "request": request,
        "pending_materials": pending_materials
    })

# Add pending materials from a material inward
@router.get("/add/{inward_id}", response_class=HTMLResponse)
async def add_pending_materials_form(request: Request, inward_id: int, db: Session = Depends(get_db)):
    inward = db.query(models.MaterialInward).options(
        joinedload(models.MaterialInward.items)
    ).filter(models.MaterialInward.id == inward_id).first()
    
    if not inward:
        return templates.TemplateResponse("error.html", {
            "request": request, "status_code": 404, "detail": "Material inward not found"
        })
    
    # Get items that are not fully received
    pending_items = []
    for item in inward.items:
        if item.status != 'completed':
            pending_items.append({
                'po_item_id': item.po_item_id,
                'material_name': item.material_name,
                'spec': item.spec,
                'brand': item.brand,
                'ordered_quantity': item.ordered_quantity,
                'received_quantity': item.quantity_received,
                'pending_quantity': item.ordered_quantity - item.quantity_received,
                'unit': item.unit
            })
    
    return templates.TemplateResponse("add_pending_list.html", {
        "request": request,
        "inward": inward,
        "pending_items": pending_items
    })

# Add pending materials POST
@router.post("/add/{inward_id}")
async def add_pending_materials(
    request: Request,
    inward_id: int,
    db: Session = Depends(get_db)
):
    form_data = await request.form()
    inward = db.query(models.MaterialInward).filter(models.MaterialInward.id == inward_id).first()
    
    if not inward:
        return templates.TemplateResponse("error.html", {
            "request": request, "status_code": 404, "detail": "Material inward not found"
        })
    
    try:
        # Process pending items
        index = 0
        while True:
            po_item_id = form_data.get(f"items[{index}][po_item_id]")
            if not po_item_id:
                break
                
            is_pending = form_data.get(f"items[{index}][is_pending]") == "on"
            
            if is_pending:
                pending_material = models.PendingMaterial(
                    po_no=inward.po_no,
                    po_item_id=int(po_item_id),
                    material_name=form_data.get(f"items[{index}][material_name]"),
                    spec=form_data.get(f"items[{index}][spec]"),
                    brand=form_data.get(f"items[{index}][brand]"),
                    ordered_quantity=int(form_data.get(f"items[{index}][ordered_quantity]")),
                    received_quantity=int(form_data.get(f"items[{index}][received_quantity]") or 0),
                    pending_quantity=int(form_data.get(f"items[{index}][pending_quantity]")),
                    unit=form_data.get(f"items[{index}][unit]"),
                    status="pending",
                    original_inward_id=inward_id
                )
                db.add(pending_material)
            
            index += 1
        
        db.commit()
        return RedirectResponse(url="/pending_materials", status_code=status.HTTP_303_SEE_OTHER)
    except Exception as e:
        db.rollback()
        print(f"Error adding pending materials: {e}")
        
        # Re-render the form
        inward = db.query(models.MaterialInward).options(
            joinedload(models.MaterialInward.items)
        ).filter(models.MaterialInward.id == inward_id).first()
        
        pending_items = []
        for item in inward.items:
            if item.status != 'completed':
                pending_items.append({
                    'po_item_id': item.po_item_id,
                    'material_name': item.material_name,
                    'spec': item.spec,
                    'brand': item.brand,
                    'ordered_quantity': item.ordered_quantity,
                    'received_quantity': item.quantity_received,
                    'pending_quantity': item.ordered_quantity - item.quantity_received,
                    'unit': item.unit
                })
        
        return templates.TemplateResponse("add_pending_list.html", {
            "request": request,
            "inward": inward,
            "pending_items": pending_items,
            "error": f"Error adding pending materials: {str(e)}"
        })

# Update pending materials form
@router.get("/update/{po_no}", response_class=HTMLResponse)
async def update_pending_materials_form(request: Request, po_no: int, db: Session = Depends(get_db)):
    # Get the purchase order details
    po = db.query(models.PurchaseOrder).options(
        joinedload(models.PurchaseOrder.dealer)
    ).filter(models.PurchaseOrder.po_no == po_no).first()
    
    if not po:
        return templates.TemplateResponse("error.html", {
            "request": request, "status_code": 404, "detail": "Purchase order not found"
        })
    
    # Get pending materials for this PO
    pending_materials = db.query(models.PendingMaterial).options(
        joinedload(models.PendingMaterial.purchase_order),
        joinedload(models.PendingMaterial.po_item)
    ).filter(
        models.PendingMaterial.po_no == po_no,
        models.PendingMaterial.status.in_(['pending', 'partially_resolved'])
    ).all()
    
    if not pending_materials:
        return templates.TemplateResponse("error.html", {
            "request": request, "status_code": 404, "detail": "No pending materials found for this PO"
        })
    
    return templates.TemplateResponse("update_pending_list.html", {
        "request": request,
        "pending_materials": pending_materials,
        "po_no": po_no,
        "po": po,  # Pass the PO object to the template
        "current_date": date.today()
    })

# Update pending materials POST
@router.post("/update/{po_no}")
async def update_pending_materials(
    request: Request,
    po_no: int,
    db: Session = Depends(get_db)
):
    form_data = await request.form()
    
    try:
        # Create a new material inward for the pending materials
        inward = models.MaterialInward(
            po_no=po_no,
            dealer_name=form_data.get("dealer_name"),
            po_date=datetime.strptime(form_data.get("po_date"), "%Y-%m-%d").date() if form_data.get("po_date") else None,
            date_of_inward=datetime.strptime(form_data.get("date_of_inward"), "%Y-%m-%d").date() if form_data.get("date_of_inward") else date.today(),
            bill_no=form_data.get("bill_no"),
            bill_date=datetime.strptime(form_data.get("bill_date"), "%Y-%m-%d").date() if form_data.get("bill_date") else None,
            cost=float(form_data.get("cost") or 0),
            payment_method=form_data.get("payment_method"),
            status="partial",
            is_pending_inward=True
        )
        
        db.add(inward)
        db.flush()  # Get the ID without committing
        
        # Process pending items
        index = 0
        all_items_resolved = True
        
        while True:
            pending_id = form_data.get(f"items[{index}][id]")
            if not pending_id:
                break
                
            pending_material = db.query(models.PendingMaterial).filter(models.PendingMaterial.id == int(pending_id)).first()
            if pending_material:
                quantity_received = int(form_data.get(f"items[{index}][quantity_received]", 0))
                
                if quantity_received > 0:
                    # Create material inward item
                    inward_item = models.MaterialInwardItem(
                        material_inward_id=inward.id,
                        po_item_id=pending_material.po_item_id,
                        material_name=pending_material.material_name,
                        spec=pending_material.spec,
                        brand=pending_material.brand,
                        ordered_quantity=pending_material.ordered_quantity,
                        quantity_received=quantity_received,
                        unit=pending_material.unit,
                        status="completed" if quantity_received >= pending_material.pending_quantity else "partial"
                    )
                    db.add(inward_item)
                    
                    # Update pending material
                    new_received = pending_material.received_quantity + quantity_received
                    new_pending = pending_material.ordered_quantity - new_received
                    
                    pending_material.received_quantity = new_received
                    pending_material.pending_quantity = new_pending
                    
                    if new_pending == 0:
                        pending_material.status = "resolved"
                    elif new_pending < pending_material.ordered_quantity:
                        pending_material.status = "partially_resolved"
                    else:
                        all_items_resolved = False
                else:
                    all_items_resolved = False
            
            index += 1
        
        # Check if all pending materials for this PO are resolved
        if all_items_resolved:
            # Update PO status if all items received
            po = db.query(models.PurchaseOrder).filter(models.PurchaseOrder.po_no == po_no).first()
            if po:
                po.status = "received"
        
        db.commit()
        return RedirectResponse(url="/pending_materials", status_code=status.HTTP_303_SEE_OTHER)
    except Exception as e:
        db.rollback()
        print(f"Error updating pending materials: {e}")
        
        # Re-render the form
        pending_materials = db.query(models.PendingMaterial).options(
            joinedload(models.PendingMaterial.purchase_order),
            joinedload(models.PendingMaterial.po_item)
        ).filter(
            models.PendingMaterial.po_no == po_no,
            models.PendingMaterial.status.in_(['pending', 'partially_resolved'])
        ).all()
        
        # Get the purchase order details
        po = db.query(models.PurchaseOrder).options(
            joinedload(models.PurchaseOrder.dealer)
        ).filter(models.PurchaseOrder.po_no == po_no).first()
        
        return templates.TemplateResponse("update_pending_list.html", {
            "request": request,
            "pending_materials": pending_materials,
            "po_no": po_no,
            "po": po,
            "current_date": date.today(),
            "error": f"Error updating pending materials: {str(e)}"
        })
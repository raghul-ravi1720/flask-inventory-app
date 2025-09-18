from fastapi import APIRouter, Depends, Request, Form, status, HTTPException, UploadFile, File
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from sqlalchemy.orm import Session, joinedload
from datetime import datetime, date
from typing import List, Optional
import os
import uuid

from app.database import get_db
from app import models
from app.shared import templates

router = APIRouter()

# List all material inwards
@router.get("", response_class=HTMLResponse)
async def list_material_inward(request: Request, db: Session = Depends(get_db)):
    inwards = db.query(models.MaterialInward).options(
        joinedload(models.MaterialInward.items).joinedload(models.MaterialInwardItem.po_item),
        joinedload(models.MaterialInward.pending_materials_list),  # Changed from pending_materials to pending_materials_list
        joinedload(models.MaterialInward.resolution_history)
    ).order_by(models.MaterialInward.id.desc()).all()
    
    return templates.TemplateResponse("material_inward.html", {
        "request": request,
        "inwards": inwards
    })

# Update the API endpoint to return PO details
@router.get("/api/po/{po_no}")
def get_po_details(po_no: int, db: Session = Depends(get_db)):
    po = db.query(models.PurchaseOrder).options(
        joinedload(models.PurchaseOrder.items)
    ).filter(models.PurchaseOrder.po_no == po_no).first()
    
    if not po:
        raise HTTPException(status_code=404, detail="PO not found")
    
    # Get dealer name from the dealer relationship
    dealer_name = po.dealer.name if po.dealer else None
    total_cost = sum((item.quantity or 0) * (item.price or 0) for item in po.items)
    
    # Check if there are any pending materials for this PO
    pending_materials = db.query(models.PendingMaterial).filter(
        models.PendingMaterial.po_item_id.in_([item.id for item in po.items]),
        models.PendingMaterial.status.in_(['pending', 'partially_resolved'])
    ).all()
    
    # Prepare items data
    items = []
    for item in po.items:
        # Check if this item has pending quantities
        pending_for_item = [p for p in pending_materials if p.po_item_id == item.id]
        pending_qty = sum(p.pending_quantity for p in pending_for_item) if pending_for_item else 0
        received_qty = item.quantity - pending_qty if pending_for_item else 0
        
        items.append({
            "id": item.id,
            "material_name": item.material_name,
            "spec": item.spec,
            "brand": item.brand,
            "ordered_quantity": item.quantity,
            "pending_quantity": pending_qty,
            "received_quantity": received_qty,
            "price": item.price,
            "unit": item.unit,
            "dealer_name": item.dealer_name,
            "has_pending": pending_qty > 0
        })
    
    return JSONResponse({
        "po_no": po.po_no,
        "po_date": po.date.strftime('%Y-%m-%d') if po.date else None,
        "dealer_name": dealer_name,
        "total_cost": total_cost,
        "items": items,
        "has_pending_materials": len(pending_materials) > 0
    })

# API endpoint to get pending materials for a PO
@router.get("/api/po/{po_no}/pending")
def get_po_pending_materials(po_no: int, db: Session = Depends(get_db)):
    po = db.query(models.PurchaseOrder).options(
        joinedload(models.PurchaseOrder.items)
    ).filter(models.PurchaseOrder.po_no == po_no).first()
    
    if not po:
        raise HTTPException(status_code=404, detail="PO not found")
    
    # Get pending materials for this PO
    pending_materials = db.query(models.PendingMaterial).filter(
        models.PendingMaterial.po_item_id.in_([item.id for item in po.items]),
        models.PendingMaterial.status.in_(['pending', 'partially_resolved'])
    ).all()
    
    pending_list = []
    for pending in pending_materials:
        pending_list.append({
            "id": pending.id,
            "material_name": pending.material_name,
            "spec": pending.spec,
            "brand": pending.brand,
            "ordered_quantity": pending.ordered_quantity,
            "received_quantity": pending.received_quantity,
            "pending_quantity": pending.pending_quantity,
            "unit": pending.unit,
            "status": pending.status,
            "inward_id": pending.material_inward_id
        })
    
    return JSONResponse({"pending_materials": pending_list})

# Add material inward form
@router.get("/add", response_class=HTMLResponse)
async def add_material_inward_form(request: Request, db: Session = Depends(get_db)):
    purchase_orders = db.query(models.PurchaseOrder).all()
    return templates.TemplateResponse("add_material_inward_enhanced.html", {
        "request": request,
        "purchase_orders": purchase_orders,
        "current_date": date.today()
    })

# In material_inward.py

@router.post("/add")
async def add_material_inward(
    request: Request,
    db: Session = Depends(get_db)
):
    form_data = await request.form()
    try:
        # Create the material inward record
        inward = models.MaterialInward(
            po_no=int(form_data.get("po_no")),
            dealer_name=form_data.get("dealer_name"),
            po_date=datetime.strptime(form_data.get("po_date"), "%Y-%m-%d").date() if form_data.get("po_date") else None,
            date_of_inward=datetime.strptime(form_data.get("date_of_inward"), "%Y-%m-%d").date() if form_data.get("date_of_inward") else date.today(),
            bill_no=form_data.get("bill_no"),
            bill_date=datetime.strptime(form_data.get("bill_date"), "%Y-%m-%d").date() if form_data.get("bill_date") else None,
            cost=float(form_data.get("cost") or 0),
            payment_method=form_data.get("payment_method"),
            status="partial"
        )
        
        db.add(inward)
        db.flush()  # Get the ID without committing
        
        # Get the PO to reference its items
        po = db.query(models.PurchaseOrder).options(
            joinedload(models.PurchaseOrder.items)
        ).filter(models.PurchaseOrder.po_no == inward.po_no).first()
        
        # Process received items
        index = 0
        all_items_completed = True
        
        while True:
            item_id = form_data.get(f"items[{index}][id]")
            if not item_id:
                break
                
            # Find the PO item
            po_item = next((item for item in po.items if item.id == int(item_id)), None)
            if not po_item:
                index += 1
                continue
                
            material_received = form_data.get(f"items[{index}][received]") == "on"
            quantity_received = int(form_data.get(f"items[{index}][quantity_received]", 0))
            
            if material_received and quantity_received > 0:
                # Create material inward item
                inward_item = models.MaterialInwardItem(
                    material_inward_id=inward.id,
                    po_item_id=po_item.id,
                    material_name=po_item.material_name,
                    spec=po_item.spec,
                    brand=po_item.brand,
                    ordered_quantity=po_item.quantity,
                    quantity_received=quantity_received,
                    unit=po_item.unit,
                    status="completed" if quantity_received >= po_item.quantity else "partial"
                )
                db.add(inward_item)
                
                # Check if all items are completed
                if quantity_received < po_item.quantity:
                    all_items_completed = False
            else:
                # Material not received at all
                all_items_completed = False
            
            index += 1
        
        # Update inward status
        if all_items_completed:
            inward.status = "completed"
            
            # Update PO status if all items received
            po.status = "received"
        
        db.commit()
        return RedirectResponse(url=f"/material_inward/{inward.id}/add_pending", status_code=status.HTTP_303_SEE_OTHER)
    except Exception as e:
        db.rollback()
        print(f"Error adding material inward: {e}")
        
        # Get purchase orders for re-rendering the form
        purchase_orders = db.query(models.PurchaseOrder).all()
        
        return templates.TemplateResponse("add_material_inward_enhanced.html", {
            "request": request,
            "purchase_orders": purchase_orders,
            "current_date": date.today(),
            "error": f"Error adding material inward: {str(e)}"
        })
    
# Add this after the add material inward POST endpoint
@router.get("/{inward_id}/add_pending", response_class=HTMLResponse)
async def redirect_to_add_pending(request: Request, inward_id: int, db: Session = Depends(get_db)):
    return RedirectResponse(url=f"/pending_materials/add/{inward_id}", status_code=status.HTTP_303_SEE_OTHER)

# Update the view endpoint to show pending materials
@router.get("/{inward_id}", response_class=HTMLResponse)
async def view_material_inward(request: Request, inward_id: int, db: Session = Depends(get_db)):
    inward = db.query(models.MaterialInward).options(
        joinedload(models.MaterialInward.items),
        joinedload(models.MaterialInward.purchase_order)
    ).filter(models.MaterialInward.id == inward_id).first()
    
    if not inward:
        return templates.TemplateResponse("error.html", {
            "request": request, "status_code": 404, "detail": "Material inward not found"
        })
    
    # Get pending materials for this PO
    pending_materials = db.query(models.PendingMaterial).options(
        joinedload(models.PendingMaterial.po_item)
    ).filter(
        models.PendingMaterial.po_no == inward.po_no,
        models.PendingMaterial.status.in_(['pending', 'partially_resolved'])
    ).all()
    
    return templates.TemplateResponse("view_material_inward_enhanced.html", {
        "request": request,
        "inward": inward,
        "pending_materials": pending_materials
    })

# Update the edit form endpoint
@router.get("/edit/{inward_id}", response_class=HTMLResponse)
async def edit_material_inward_form(request: Request, inward_id: int, db: Session = Depends(get_db)):
    inward = db.query(models.MaterialInward).options(
        joinedload(models.MaterialInward.items),
        joinedload(models.MaterialInward.pending_materials_list),
        joinedload(models.MaterialInward.resolution_history)
    ).filter(models.MaterialInward.id == inward_id).first()
    
    # Get the PO to show all items
    po = db.query(models.PurchaseOrder).options(
        joinedload(models.PurchaseOrder.items)
    ).filter(models.PurchaseOrder.po_no == inward.po_no).first() if inward else None
    
    purchase_orders = db.query(models.PurchaseOrder).all()
    
    if not inward or not po:
        return RedirectResponse(url="/material_inward", status_code=status.HTTP_303_SEE_OTHER)
    
    return templates.TemplateResponse("edit_material_inward_enhanced.html", {
        "request": request, 
        "inward": inward, 
        "purchase_orders": purchase_orders,
        "po": po
    })

# Edit inward POST
@router.post("/edit/{inward_id}")
async def update_material_inward(request: Request, inward_id: int, db: Session = Depends(get_db)):
    form_data = await request.form()
    inward = db.query(models.MaterialInward).options(
        joinedload(models.MaterialInward.items),
        joinedload(models.MaterialInward.pending_materials_list)
    ).filter(models.MaterialInward.id == inward_id).first()
    
    if not inward:
        return RedirectResponse(url="/material_inward", status_code=status.HTTP_303_SEE_OTHER)

    try:
        # Update basic inward details
        inward.dealer_name = form_data.get("dealer_name")
        inward.po_date = datetime.strptime(form_data.get("po_date"), "%Y-%m-%d").date() if form_data.get("po_date") else inward.po_date
        inward.date_of_inward = datetime.strptime(form_data.get("date_of_inward"), "%Y-%m-%d").date() if form_data.get("date_of_inward") else inward.date_of_inward
        inward.bill_no = form_data.get("bill_no")
        inward.bill_date = datetime.strptime(form_data.get("bill_date"), "%Y-%m-%d").date() if form_data.get("bill_date") else inward.bill_date
        inward.cost = float(form_data.get("cost") or 0)
        inward.payment_method = form_data.get("payment_method")
        
        # Get the PO to reference its items
        po = db.query(models.PurchaseOrder).options(
            joinedload(models.PurchaseOrder.items)
        ).filter(models.PurchaseOrder.po_no == inward.po_no).first()
        
        # Process received items
        index = 0
        all_items_resolved = True
        
        while True:
            item_id = form_data.get(f"items[{index}][id]")
            if not item_id:
                break
                
            # Find the PO item
            po_item = next((item for item in po.items if item.id == int(item_id)), None)
            if not po_item:
                index += 1
                continue
                
            # Find existing inward item
            inward_item = next((item for item in inward.items if item.po_item_id == int(item_id)), None)
            
            material_received = form_data.get(f"items[{index}][received]") == "on"
            additional_received = int(form_data.get(f"items[{index}][additional_received]", 0))
            is_full_quantity = form_data.get(f"items[{index}][full_quantity]") == "on"
            
            if material_received:
                if inward_item:
                    # Update existing inward item
                    new_received = inward_item.quantity_received + additional_received
                    inward_item.quantity_received = new_received
                    inward_item.status = "completed" if new_received == po_item.quantity else "partial"
                    
                    # Update pending material if exists
                    pending_material = next((p for p in inward.pending_materials_list if p.po_item_id == int(item_id)), None)
                    if pending_material:
                        pending_material.received_quantity = new_received
                        pending_material.pending_quantity = po_item.quantity - new_received
                        
                        if pending_material.pending_quantity == 0:
                            pending_material.status = "resolved"
                        elif pending_material.pending_quantity < po_item.quantity:
                            pending_material.status = "partially_resolved"
                else:
                    # Create new inward item
                    new_received = additional_received
                    inward_item = models.MaterialInwardItem(
                        material_inward_id=inward.id,
                        po_item_id=po_item.id,
                        quantity_received=new_received,
                        status="completed" if new_received == po_item.quantity else "partial"
                    )
                    db.add(inward_item)
                    
                    # Create pending material if not full quantity
                    if new_received < po_item.quantity:
                        all_items_resolved = False
                        pending_material = models.PendingMaterial(
                            material_inward_id=inward.id,
                            po_item_id=po_item.id,
                            material_name=po_item.material_name,
                            spec=po_item.spec,
                            brand=po_item.brand,
                            ordered_quantity=po_item.quantity,
                            received_quantity=new_received,
                            pending_quantity=po_item.quantity - new_received,
                            unit=po_item.unit,
                            status="partially_resolved" if new_received > 0 else "pending"
                        )
                        db.add(pending_material)
            else:
                # Material not received at all
                all_items_resolved = False
                
                # Remove inward item if exists
                if inward_item:
                    db.delete(inward_item)
                
                # Create or update pending material
                pending_material = next((p for p in inward.pending_materials_list if p.po_item_id == int(item_id)), None)
                if not pending_material:
                    pending_material = models.PendingMaterial(
                        material_inward_id=inward.id,
                        po_item_id=po_item.id,
                        material_name=po_item.material_name,
                        spec=po_item.spec,
                        brand=po_item.brand,
                        ordered_quantity=po_item.quantity,
                        received_quantity=0,
                        pending_quantity=po_item.quantity,
                        unit=po_item.unit,
                        status="pending"
                    )
                    db.add(pending_material)
            
            index += 1
        
        # Process pending material resolutions
        resolve_pending = form_data.getlist("resolve_pending[]")
        for pending_id in resolve_pending:
            pending_material = next((p for p in inward.pending_materials_list if p.id == int(pending_id)), None)
            if pending_material:
                resolve_quantity = int(form_data.get(f"resolve_quantity[{pending_id}]", 0))
                
                if resolve_quantity > 0:
                    new_received = pending_material.received_quantity + resolve_quantity
                    pending_material.received_quantity = new_received
                    pending_material.pending_quantity = pending_material.ordered_quantity - new_received
                    
                    if pending_material.pending_quantity == 0:
                        pending_material.status = "resolved"
                    elif pending_material.pending_quantity < pending_material.ordered_quantity:
                        pending_material.status = "partially_resolved"
                    
                    # Create resolution record
                    resolution = models.PendingMaterialResolution(
                        material_inward_id=inward.id,
                        pending_material_id=pending_material.id,
                        resolved_quantity=resolve_quantity,
                        resolution_bill_no=form_data.get("bill_no"),
                        resolution_date=inward.date_of_inward
                    )
                    db.add(resolution)
        
        # Update inward status
        if all_items_resolved:
            inward.status = "completed"
            
            # Update PO status if all items received
            po.status = "received"
        else:
            inward.status = "partial"
        
        db.commit()
        return RedirectResponse(url="/material_inward", status_code=status.HTTP_303_SEE_OTHER)
    except Exception as e:
        db.rollback()
        print(f"Error updating material inward: {e}")
        
        # Get purchase orders for re-rendering the form
        purchase_orders = db.query(models.PurchaseOrder).all()
        
        return templates.TemplateResponse("edit_material_inward_enhanced.html", {
            "request": request,
            "inward": inward,
            "purchase_orders": purchase_orders,
            "error": f"Error updating material inward: {str(e)}"
        })

# Delete inward
@router.post("/delete/{inward_id}")
async def delete_material_inward(inward_id: int, db: Session = Depends(get_db)):
    inward = db.query(models.MaterialInward).filter(models.MaterialInward.id == inward_id).first()
    if inward:
        db.delete(inward)
        db.commit()
    return RedirectResponse(url="/material_inward", status_code=status.HTTP_303_SEE_OTHER)

# List pending materials
@router.get("/pending", response_class=HTMLResponse)
async def list_pending_materials(request: Request, db: Session = Depends(get_db)):
    pending_materials = db.query(models.PendingMaterial).options(
        joinedload(models.PendingMaterial.po_item),
        joinedload(models.PendingMaterial.material_inward)
    ).filter(models.PendingMaterial.status.in_(['pending', 'partially_resolved'])).all()
    
    return templates.TemplateResponse("pending_materials.html", {
        "request": request,
        "pending_materials": pending_materials
    })

# Resolve pending material
@router.post("/pending/resolve/{pending_id}")
async def resolve_pending_material(
    request: Request,
    pending_id: int,
    db: Session = Depends(get_db),
    proof_document: Optional[UploadFile] = File(None)
):
    form_data = await request.form()
    pending_material = db.query(models.PendingMaterial).filter(models.PendingMaterial.id == pending_id).first()
    
    if pending_material:
        pending_material.status = "resolved"
        pending_material.resolution_bill_no = form_data.get("resolution_bill_no")
        pending_material.resolution_date = datetime.strptime(form_data.get("resolution_date"), "%Y-%m-%d").date() if form_data.get("resolution_date") else None
        
        # Handle file upload for proof document
        if proof_document and proof_document.filename:
            # Create uploads directory if it doesn't exist
            upload_dir = "uploads/pending_materials"
            os.makedirs(upload_dir, exist_ok=True)
            
            # Generate unique filename
            file_extension = proof_document.filename.split(".")[-1]
            unique_filename = f"{uuid.uuid4()}.{file_extension}"
            file_path = os.path.join(upload_dir, unique_filename)
            
            # Save the file
            with open(file_path, "wb") as buffer:
                content = await proof_document.read()
                buffer.write(content)
            
            pending_material.proof_document_path = file_path
        
        # Create resolution record
        resolution = models.PendingMaterialResolution(
            material_inward_id=pending_material.material_inward_id,
            pending_material_id=pending_material.id,
            resolved_quantity=pending_material.pending_quantity,
            resolution_bill_no=form_data.get("resolution_bill_no"),
            resolution_date=datetime.strptime(form_data.get("resolution_date"), "%Y-%m-%d").date() if form_data.get("resolution_date") else None,
            notes=form_data.get("notes", "")
        )
        db.add(resolution)
        
        # Update the pending quantity to zero since it's resolved
        pending_material.pending_quantity = 0
        
        db.commit()
    
    return RedirectResponse(url="/material_inward/pending", status_code=status.HTTP_303_SEE_OTHER)
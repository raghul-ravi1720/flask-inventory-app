from fastapi import APIRouter, Depends, HTTPException, Request, Form, status
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from sqlalchemy.orm import Session, joinedload
from typing import List, Optional
from datetime import datetime, date
import math

from app.database import get_db
from app import models
from app.shared import templates
from app.pdf_utils import generate_pdf, create_pdf_response, render_pdf_template
from sqlalchemy import or_

router = APIRouter()

# API Endpoints
@router.get("/api", response_model=List[dict])
async def get_purchase_orders_api(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    purchase_orders = db.query(models.PurchaseOrder).offset(skip).limit(limit).all()
    return purchase_orders

@router.get("/api/{po_no}", response_model=dict)
async def get_purchase_order_api(po_no: int, db: Session = Depends(get_db)):
    purchase_order = db.query(models.PurchaseOrder).filter(models.PurchaseOrder.po_no == po_no).first()
    if purchase_order is None:
        raise HTTPException(status_code=404, detail="Purchase order not found")
    return purchase_order.__dict__

# Frontend Routes
@router.get("", response_class=HTMLResponse)
async def list_purchase_orders(request: Request, db: Session = Depends(get_db)):
    try:
        search_query = request.query_params.get('q', '').strip()
        status_filter = request.query_params.get('status', '')
        branch_filter = request.query_params.get('branch', '')
        
        query = db.query(models.PurchaseOrder).options(
            joinedload(models.PurchaseOrder.dealer),
            joinedload(models.PurchaseOrder.items),
            joinedload(models.PurchaseOrder.invoice_branch),
            joinedload(models.PurchaseOrder.consignee)
        )
        
        if search_query:
            query = query.filter(
                or_(
                    models.PurchaseOrderItem.material_name.ilike(f'%{search_query}%'),
                    models.PurchaseOrder.dealer.has(models.Dealer.name.ilike(f'%{search_query}%'))
                )
            )
        
        if status_filter:
            query = query.filter(models.PurchaseOrder.status == status_filter)
        
        if branch_filter:
            query = query.filter(models.PurchaseOrder.invoice_branch_id == branch_filter)
        
        purchase_orders = query.order_by(models.PurchaseOrder.po_no.asc()).all()
        company_branches = db.query(models.CompanyBranch).all()
        
        return templates.TemplateResponse("purchase_orders.html", {
            "request": request, 
            "purchase_orders": purchase_orders,
            "company_branches": company_branches,
            "search_query": search_query,
            "status_filter": status_filter,
            "branch_filter": branch_filter
        })
    except Exception as e:
        print(f"Error in list_purchase_orders: {e}")
        return templates.TemplateResponse("error.html", {
            "request": request, 
            "status_code": 500, 
            "detail": f"Error loading purchase orders: {str(e)}"
        })

@router.get("/add", response_class=HTMLResponse)
async def add_purchase_order_form(request: Request, db: Session = Depends(get_db)):
    try:
        dealers = db.query(models.Dealer).all()
        company_branches = db.query(models.CompanyBranch).all()
        consignees = db.query(models.Consignee).all()
        
        # Get the next PO number
        last_po = db.query(models.PurchaseOrder).order_by(models.PurchaseOrder.po_no.asc()).first()
        next_po_number = last_po.po_no + 1 if last_po else 1
        
        return templates.TemplateResponse("add_purchase_order.html", {
            "request": request,
            "dealers": dealers,
            "company_branches": company_branches,
            "consignees": consignees,
            "next_po_number": next_po_number,
            "current_date": date.today() # YYYY-MM-DD
        })
    except Exception as e:
        print(f"Error loading add purchase order form: {e}")
        return RedirectResponse(url="/purchase_orders", status_code=status.HTTP_303_SEE_OTHER)

@router.post("/add")
async def add_purchase_order(
    request: Request,
    db: Session = Depends(get_db)
):
    try:
        form_data = await request.form()
        
        # Create purchase order
        purchase_order = models.PurchaseOrder(
            dealer_id=int(form_data.get("dealer_id")) if form_data.get("dealer_id") else None,
            invoice_branch_id=int(form_data.get("invoice_branch_id")) if form_data.get("invoice_branch_id") else None,
            consignee_id=int(form_data.get("consignee_id")) if form_data.get("consignee_id") else None,
            date=datetime.strptime(form_data.get("date"), "%Y-%m-%d").date() if form_data.get("date") else date.today(),
            status=form_data.get("status", "unsent"),
            notes=form_data.get("notes", ""),
            discount=float(form_data.get("discount", 0))
        )
        
        db.add(purchase_order)
        db.flush()  # Get the PO number without committing
        
        # Process items
        index = 0
        while True:
            material_id = form_data.get(f"items[{index}][material_id]")
            if not material_id:
                break
                
            material_name = form_data.get(f"items[{index}][material_name]")
            spec = form_data.get(f"items[{index}][spec]")
            brand = form_data.get(f"items[{index}][brand]")
            dealer_name = form_data.get(f"items[{index}][dealer_name]")
            price = float(form_data.get(f"items[{index}][price]", 0))
            unit = form_data.get(f"items[{index}][unit]")
            quantity = int(form_data.get(f"items[{index}][quantity]", 0))

            # Create purchase order item
            item = models.PurchaseOrderItem(
                po_no=purchase_order.po_no,
                material_id=int(material_id) if material_id else None,
                material_name=material_name,
                spec=spec,
                brand=brand,
                dealer_name=dealer_name,
                quantity=quantity,
                price=price,
                unit=unit
            )
            db.add(item)
            index += 1

        db.commit()
        
        return RedirectResponse(url="/purchase_orders", status_code=status.HTTP_303_SEE_OTHER)
    except Exception as e:
        print(f"Error adding purchase order: {e}")
        db.rollback()
        
        # Re-render the form with error message
        dealers = db.query(models.Dealer).all()
        company_branches = db.query(models.CompanyBranch).all()
        consignees = db.query(models.Consignee).all()
        
        last_po = db.query(models.PurchaseOrder).order_by(models.PurchaseOrder.po_no.asc()).first()
        next_po_number = last_po.po_no + 1 if last_po else 1
        
        return templates.TemplateResponse("add_purchase_order.html", {
            "request": request,
            "dealers": dealers,
            "company_branches": company_branches,
            "consignees": consignees,
            "next_po_number": next_po_number,
            "error": f"Error adding purchase order: {str(e)}",
            "form_data": dict(form_data)
        })

@router.get("/edit/{po_no}", response_class=HTMLResponse)
async def edit_purchase_order_form(request: Request, po_no: int, db: Session = Depends(get_db)):
    try:
        purchase_order = db.query(models.PurchaseOrder).options(
            joinedload(models.PurchaseOrder.items),
            joinedload(models.PurchaseOrder.dealer),
            joinedload(models.PurchaseOrder.invoice_branch),
            joinedload(models.PurchaseOrder.consignee)
        ).filter(models.PurchaseOrder.po_no == po_no).first()
        
        if purchase_order is None:
            return RedirectResponse(url="/purchase_orders", status_code=status.HTTP_303_SEE_OTHER)
        
        dealers = db.query(models.Dealer).all()
        company_branches = db.query(models.CompanyBranch).all()
        consignees = db.query(models.Consignee).all()
        
        return templates.TemplateResponse("edit_purchase_order.html", {
            "request": request, 
            "purchase_order": purchase_order,
            "dealers": dealers,
            "company_branches": company_branches,
            "consignees": consignees
        })
    except Exception as e:
        print(f"Error loading edit form: {e}")
        return RedirectResponse(url="/purchase_orders", status_code=status.HTTP_303_SEE_OTHER)

@router.post("/edit/{po_no}")
async def update_purchase_order(
    request: Request,
    po_no: int,
    db: Session = Depends(get_db)
):
    try:
        form_data = await request.form()
        
        purchase_order = db.query(models.PurchaseOrder).filter(models.PurchaseOrder.po_no == po_no).first()
        if purchase_order is None:
            return RedirectResponse(url="/purchase_orders", status_code=status.HTTP_303_SEE_OTHER)
        
        # Update purchase order details
        purchase_order.dealer_id = int(form_data.get("dealer_id")) if form_data.get("dealer_id") else None
        purchase_order.invoice_branch_id = int(form_data.get("invoice_branch_id")) if form_data.get("invoice_branch_id") else None
        purchase_order.consignee_id = int(form_data.get("consignee_id")) if form_data.get("consignee_id") else None
        purchase_order.date = datetime.strptime(form_data.get("date"), "%Y-%m-%d").date() if form_data.get("date") else purchase_order.date
        purchase_order.status = form_data.get("status", "unsent")
        purchase_order.notes = form_data.get("notes", "")
        purchase_order.discount = float(form_data.get("discount", 0))
        
        # Remove existing items
        db.query(models.PurchaseOrderItem).filter(models.PurchaseOrderItem.po_no == po_no).delete()
        
        # Process new items
        index = 0
        while True:
            material_id = form_data.get(f"items[{index}][material_id]")
            if not material_id:
                break
                
            material_name = form_data.get(f"items[{index}][material_name]")
            spec = form_data.get(f"items[{index}][spec]")
            brand = form_data.get(f"items[{index}][brand]")
            dealer_name = form_data.get(f"items[{index}][dealer_name]")
            price = float(form_data.get(f"items[{index}][price]", 0))
            unit = form_data.get(f"items[{index}][unit]")
            quantity = int(form_data.get(f"items[{index}][quantity]", 0))

            # Create purchase order item
            item = models.PurchaseOrderItem(
                po_no=po_no,
                material_id=int(material_id) if material_id else None,
                material_name=material_name,
                spec=spec,
                brand=brand,
                dealer_name=dealer_name,
                quantity=quantity,
                price=price,
                unit=unit
            )
            db.add(item)
            index += 1

        db.commit()
        
        return RedirectResponse(url="/purchase_orders", status_code=status.HTTP_303_SEE_OTHER)
    except Exception as e:
        print(f"Error updating purchase order: {e}")
        db.rollback()
        
        # Re-render the form with error message
        purchase_order = db.query(models.PurchaseOrder).options(
            joinedload(models.PurchaseOrder.items),
            joinedload(models.PurchaseOrder.dealer),
            joinedload(models.PurchaseOrder.invoice_branch),
            joinedload(models.PurchaseOrder.consignee)
        ).filter(models.PurchaseOrder.po_no == po_no).first()
        
        dealers = db.query(models.Dealer).all()
        company_branches = db.query(models.CompanyBranch).all()
        consignees = db.query(models.Consignee).all()
        
        return templates.TemplateResponse("edit_purchase_order.html", {
            "request": request, 
            "purchase_order": purchase_order,
            "dealers": dealers,
            "company_branches": company_branches,
            "consignees": consignees,
            "error": f"Error updating purchase order: {str(e)}"
        })

@router.post("/delete/{po_no}")
async def delete_purchase_order(po_no: int, db: Session = Depends(get_db)):
    try:
        purchase_order = db.query(models.PurchaseOrder).filter(models.PurchaseOrder.po_no == po_no).first()
        if purchase_order is None:
            return RedirectResponse(url="/purchase_orders", status_code=status.HTTP_303_SEE_OTHER)
        
        db.delete(purchase_order)
        db.commit()
        
        return RedirectResponse(url="/purchase_orders", status_code=status.HTTP_303_SEE_OTHER)
    except Exception as e:
        print(f"Error deleting purchase order: {e}")
        db.rollback()
        return RedirectResponse(url="/purchase_orders", status_code=status.HTTP_303_SEE_OTHER)

@router.get("/{po_no}", response_class=HTMLResponse)
async def view_purchase_order(request: Request, po_no: int, db: Session = Depends(get_db)):
    try:
        purchase_order = db.query(models.PurchaseOrder).options(
            joinedload(models.PurchaseOrder.dealer),
            joinedload(models.PurchaseOrder.invoice_branch),
            joinedload(models.PurchaseOrder.consignee),
            joinedload(models.PurchaseOrder.items)
        ).filter(models.PurchaseOrder.po_no == po_no).first()
        
        if purchase_order is None:
            return templates.TemplateResponse("error.html", {
                "request": request, 
                "status_code": 404, 
                "detail": f"Purchase order with PO number {po_no} not found"
            })
        
        return templates.TemplateResponse("view_purchase_order.html", {
            "request": request, 
            "purchase_order": purchase_order
        })
    except Exception as e:
        print(f"Error viewing purchase order: {e}")
        return templates.TemplateResponse("error.html", {
            "request": request, 
            "status_code": 500, 
            "detail": f"Error viewing purchase order: {str(e)}"
        })

@router.get("/{po_no}/generate", response_class=HTMLResponse)
async def generate_po_form(request: Request, po_no: int, db: Session = Depends(get_db)):
    try:
        # Fetch the purchase order with all related data
        purchase_order = db.query(models.PurchaseOrder).options(
            joinedload(models.PurchaseOrder.dealer),
            joinedload(models.PurchaseOrder.invoice_branch),
            joinedload(models.PurchaseOrder.consignee),
            joinedload(models.PurchaseOrder.items).joinedload(models.PurchaseOrderItem.material)
        ).filter(models.PurchaseOrder.po_no == po_no).first()
        
        if purchase_order is None:
            return templates.TemplateResponse("error.html", {
                "request": request, 
                "status_code": 404, 
                "detail": f"Purchase order with PO number {po_no} not found"
            })
        
        # Convert amount to words for display
        def number_to_words(number):
            # Implementation from your previous code
            units = ["", "One", "Two", "Three", "Four", "Five", "Six", "Seven", "Eight", "Nine"]
            teens = ["Ten", "Eleven", "Twelve", "Thirteen", "Fourteen", "Fifteen", "Sixteen", "Seventeen", "Eighteen", "Nineteen"]
            tens = ["", "Ten", "Twenty", "Thirty", "Forty", "Fifty", "Sixty", "Seventy", "Eighty", "Ninety"]
            
            if number == 0:
                return "Zero"
            
            words = ""
            
            # Crores
            if number >= 10000000:
                words += number_to_words(number // 10000000) + " Crore "
                number %= 10000000
            
            # Lakhs
            if number >= 100000:
                words += number_to_words(number // 100000) + " Lakh "
                number %= 100000
            
            # Thousands
            if number >= 1000:
                words += number_to_words(number // 1000) + " Thousand "
                number %= 1000
            
            # Hundreds
            if number >= 100:
                words += number_to_words(number // 100) + " Hundred "
                number %= 100
            
            # Tens and units
            if number > 0:
                if number < 10:
                    words += units[number]
                elif number < 20:
                    words += teens[number - 10]
                else:
                    words += tens[number // 10]
                    if number % 10 > 0:
                        words += " " + units[number % 10]
            
            return words.strip()
        
        amount_in_words = number_to_words(math.floor(purchase_order.grand_total)) + " Rupees"
        if purchase_order.grand_total % 1 > 0:
            paise = round((purchase_order.grand_total % 1) * 100)
            amount_in_words += f" and {paise} Paise"
        
        amount_in_words += " Only"
        
        # Render the purchase order generator template with the PO data
        return templates.TemplateResponse("purchase_order_generator.html", {
            "request": request,
            "purchase_order": purchase_order,
            "amount_in_words": amount_in_words
        })
        
    except Exception as e:
        print(f"Error loading PO generator form: {e}")
        return templates.TemplateResponse("error.html", {
            "request": request, 
            "status_code": 500, 
            "detail": f"Error loading purchase order generator: {str(e)}"
        })

@router.get("/search/materials")
async def search_materials_po(
    request: Request, 
    q: str = "", 
    dealer_id: str = "", 
    db: Session = Depends(get_db)
):
    try:
        query = db.query(models.Storage)
        
        if q:
            query = query.filter(
                or_(
                    models.Storage.defined_name_with_spec.ilike(f'%{q}%'),
                    models.Storage.base_name.ilike(f'%{q}%')
                )
            )
        
        if dealer_id:
            query = query.filter(models.Storage.dealer_id == int(dealer_id))
        
        materials = query.limit(20).all()
        
        return templates.TemplateResponse("_material_options_po.html", {
            "request": request,
            "materials": materials
        })
    except Exception as e:
        print(f"Error searching materials for PO: {e}")
        return JSONResponse(content={"error": str(e)}, status_code=500)
from fastapi import APIRouter, Depends, HTTPException, Request, Form, status
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime

from app.database import get_db
from app import models
from app.shared import templates
from app.schemas import Product, ProductCreate, ProductUpdate, ProductWithMaterials, ProductMaterialCreate
from app.pdf_utils import generate_pdf, create_pdf_response, render_pdf_template
from sqlalchemy.orm import joinedload

router = APIRouter()

# API Endpoints
@router.get("/api", response_model=List[ProductWithMaterials])
async def get_products_api(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    products = db.query(models.Product).offset(skip).limit(limit).all()
    return products

@router.get("/api/{product_id}", response_model=ProductWithMaterials)
async def get_product_api(product_id: int, db: Session = Depends(get_db)):
    product = db.query(models.Product).filter(models.Product.id == product_id).first()
    if product is None:
        raise HTTPException(status_code=404, detail="Product not found")
    return product

@router.post("/api", response_model=Product)
async def create_product_api(product: ProductCreate, db: Session = Depends(get_db)):
    db_product = models.Product(**product.dict())
    db.add(db_product)
    db.commit()
    db.refresh(db_product)
    return db_product

@router.put("/api/{product_id}", response_model=Product)
async def update_product_api(product_id: int, product: ProductUpdate, db: Session = Depends(get_db)):
    db_product = db.query(models.Product).filter(models.Product.id == product_id).first()
    if db_product is None:
        raise HTTPException(status_code=404, detail="Product not found")
    
    for key, value in product.dict(exclude_unset=True).items():
        setattr(db_product, key, value)
    
    db.commit()
    db.refresh(db_product)
    return db_product

@router.delete("/api/{product_id}")
async def delete_product_api(product_id: int, db: Session = Depends(get_db)):
    product = db.query(models.Product).filter(models.Product.id == product_id).first()
    if product is None:
        raise HTTPException(status_code=404, detail="Product not found")
    
    db.delete(product)
    db.commit()
    return {"message": "Product deleted successfully"}

# Frontend Routes
@router.get("", response_class=HTMLResponse)
async def list_products(request: Request, db: Session = Depends(get_db)):
    try:
        search_query = request.query_params.get('q', '').strip()
        
        if search_query:
            products = db.query(models.Product).filter(
                models.Product.product_name.ilike(f'%{search_query}%') |
                models.Product.product_description.ilike(f'%{search_query}%') |
                models.Product.section_name.ilike(f'%{search_query}%')
            ).all()
        else:
            products = db.query(models.Product).all()
        
        # Build storage map for efficiency
        storages = db.query(models.Storage).all()
        storage_map = {s.id: s for s in storages}
        
        return templates.TemplateResponse("list_product.html", {
            "request": request, 
            "products": products,
            "storage_map": storage_map,
            "search_query": search_query
        })
    except Exception as e:
        print(f"Error in list_products: {e}")
        return templates.TemplateResponse("error.html", {
            "request": request, 
            "status_code": 500, 
            "detail": f"Error loading products: {str(e)}"
        })

@router.get("/add", response_class=HTMLResponse)
async def add_product_form(request: Request, db: Session = Depends(get_db)):
    try:
        storages = db.query(models.Storage).all()
        return templates.TemplateResponse("add_product.html", {
            "request": request,
            "storages": storages
        })
    except Exception as e:
        print(f"Error loading add product form: {e}")
        return RedirectResponse(url="/products", status_code=status.HTTP_303_SEE_OTHER)

@router.post("/add")
async def add_product(
    request: Request,
    db: Session = Depends(get_db)
):
    try:
        form_data = await request.form()
        
        # Create the product
        product = models.Product(
            product_name=form_data.get("product_name"),
            product_description=form_data.get("product_description"),
            section_name=form_data.get("section_name")
        )
        
        db.add(product)
        db.flush()  # Get the ID without committing
        
        # Process materials
        material_ids = form_data.getlist("material_ids")
        quantities = form_data.getlist("quantities")
        
        for i, material_id in enumerate(material_ids):
            if material_id and quantities[i]:
                product_material = models.ProductMaterial(
                    product_id=product.id,
                    storage_id=int(material_id),
                    quantity_needed=int(quantities[i])
                )
                db.add(product_material)
        
        db.commit()
        
        return RedirectResponse(url="/products", status_code=status.HTTP_303_SEE_OTHER)
    except Exception as e:
        print(f"Error adding product: {e}")
        db.rollback()
        
        # Re-render the form with error message
        storages = db.query(models.Storage).all()
        return templates.TemplateResponse("add_product.html", {
            "request": request,
            "storages": storages,
            "error": f"Error adding product: {str(e)}",
            "form_data": dict(form_data)
        })

@router.get("/edit/{product_id}", response_class=HTMLResponse)
async def edit_product_form(request: Request, product_id: int, db: Session = Depends(get_db)):
    try:
        product = db.query(models.Product).filter(models.Product.id == product_id).first()
        if product is None:
            return RedirectResponse(url="/products", status_code=status.HTTP_303_SEE_OTHER)
        
        storages = db.query(models.Storage).all()

        # ✅ Safe storage map
        storage_map = {
            s.id: {
                "id": s.id,
                "base_name": getattr(s, "base_name", "") or "",
                "defined_name_with_spec": getattr(s, "defined_name_with_spec", "") or "",
                "brand": getattr(s, "brand", "") or "",
                "dealer": {
                    "id": getattr(s.dealer, "id", None) if s.dealer else None,
                    "name": getattr(s.dealer, "name", "") if s.dealer else ""
                } if s.dealer else None
            }
            for s in storages
        }

        # ✅ Serialize product materials for JS
        product_materials = [
            {
                "storage_id": pm.storage_id,
                "quantity_needed": pm.quantity_needed
            }
            for pm in product.product_materials
        ]

        # ✅ Selected quantities for form prefilling
        selected_quantities = {
            pm.storage_id: pm.quantity_needed
            for pm in product.product_materials if pm.storage_id
        }

        return templates.TemplateResponse("edit_product.html", {
            "request": request, 
            "product": product,
            "storages": storages,
            "storage_map": storage_map,
            "product_materials": product_materials,   # ✅ Now included
            "selected_quantities": selected_quantities
        })
    except Exception as e:
        print(f"Error loading edit form: {str(e)}")
        import traceback
        traceback.print_exc()
        return RedirectResponse(url="/products", status_code=status.HTTP_303_SEE_OTHER)

@router.post("/edit/{product_id}")
async def update_product_form(
    request: Request,
    product_id: int,
    db: Session = Depends(get_db)
):
    try:
        form_data = await request.form()

        product = db.query(models.Product).filter(models.Product.id == product_id).first()
        if product is None:
            return RedirectResponse(url="/products", status_code=status.HTTP_303_SEE_OTHER)

        # ✅ Update product info
        product.product_name = form_data.get("product_name")
        product.section_name = form_data.get("section_name")
        product.product_description = form_data.get("product_description")

        # ✅ Clear old materials
        db.query(models.ProductMaterial).filter(
            models.ProductMaterial.product_id == product.id
        ).delete()

        # ✅ Add updated materials
        material_ids = form_data.getlist("material_ids")
        quantities = form_data.getlist("quantities")

        for i, material_id in enumerate(material_ids):
            if material_id and quantities[i]:
                db.add(models.ProductMaterial(
                    product_id=product.id,
                    storage_id=int(material_id),
                    quantity_needed=int(quantities[i])
                ))

        db.commit()

        return RedirectResponse(url="/products", status_code=status.HTTP_303_SEE_OTHER)
    
    except Exception as e:
        print(f"Error updating product: {e}")
        db.rollback()

        storages = db.query(models.Storage).all()
        return templates.TemplateResponse("edit_product.html", {
            "request": request,
            "product": product,
            "storages": storages,
            "error": f"Error updating product: {str(e)}"
        })

@router.get("/details/{product_id}", response_class=HTMLResponse)
async def product_details(request: Request, product_id: int, db: Session = Depends(get_db)):
    product = db.query(models.Product).filter(models.Product.id == product_id).first()
    if not product:
        return RedirectResponse(url="/products", status_code=status.HTTP_303_SEE_OTHER)

    storages = db.query(models.Storage).all()
    storage_map = {s.id: s for s in storages}

    return templates.TemplateResponse("product_details.html", {
        "request": request,
        "product": product,
        "storage_map": storage_map
    })


@router.post("/delete/{product_id}")
async def delete_product(product_id: int, db: Session = Depends(get_db)):
    try:
        product = db.query(models.Product).filter(models.Product.id == product_id).first()
        if product is None:
            return RedirectResponse(url="/products", status_code=status.HTTP_303_SEE_OTHER)
        
        db.delete(product)
        db.commit()
        
        return RedirectResponse(url="/products", status_code=status.HTTP_303_SEE_OTHER)
    except Exception as e:
        print(f"Error deleting product: {e}")
        db.rollback()
        return RedirectResponse(url="/products", status_code=status.HTTP_303_SEE_OTHER)

@router.get("/search_materials")
async def search_materials(request: Request, q: str = "", db: Session = Depends(get_db)):
    try:
        if q:
            materials = db.query(models.Storage).filter(
                models.Storage.base_name.ilike(f'%{q}%') |
                models.Storage.defined_name_with_spec.ilike(f'%{q}%') |
                models.Storage.brand.ilike(f'%{q}%')
            ).limit(10).all()
        else:
            materials = db.query(models.Storage).limit(10).all()
        
        return templates.TemplateResponse("_material_options.html", {
            "request": request,
            "materials": materials
        })
    except Exception as e:
        print(f"Error searching materials: {e}")
        return JSONResponse(content={"error": str(e)}, status_code=500)
    
# Export functionality
@router.get("/export",  response_class=HTMLResponse)
async def export_products_form(request: Request, db: Session = Depends(get_db)):
    products = db.query(models.Product).all()  # ✅ use SQLAlchemy model, not schema
    return templates.TemplateResponse("export_products.html", {
        "request": request,
        "products": products
    })
    
@router.post("/export/pdf")
async def export_products_pdf(request: Request, db: Session = Depends(get_db)):
    form = await request.form()
    product_id = form.get("product_ids")  # single product selected

    if not product_id:
        return templates.TemplateResponse("error.html", {
            "request": request,
            "status_code": 400,
            "detail": "No product selected for export"
        })

    # Fetch the product with its materials
    product = db.query(models.Product).options(
        joinedload(models.Product.product_materials)
        .joinedload(models.ProductMaterial.storage)
    ).filter(models.Product.id == int(product_id)).first()

    if not product:
        return templates.TemplateResponse("error.html", {
            "request": request,
            "status_code": 404,
            "detail": "Product not found"
        })

    html_content = render_pdf_template("_export_product_details.html", {
        "product": product,  # ✅ pass as single product
        "export_date": datetime.now()
    })

    pdf_buffer = generate_pdf(html_content)
    if not pdf_buffer:
        return templates.TemplateResponse("error.html", {
            "request": request,
            "status_code": 500,
            "detail": "Failed to generate PDF"
        })

    filename = f"product_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
    return create_pdf_response(pdf_buffer, filename)

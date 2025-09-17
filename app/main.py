from fastapi import FastAPI, Request, Depends
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse, PlainTextResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
import os
from datetime import datetime
import traceback

app = FastAPI(
    title="Inventory Management System",
    description="A comprehensive inventory management system built with FastAPI",
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc"
)

# Configure templates
templates = Jinja2Templates(directory="app/templates")

# Mount static files
app.mount("/static", StaticFiles(directory="app/static"), name="static")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Template filters
def format_currency(value):
    if value is None:
        return "₹0.00"
    try:
        return f"₹{float(value):,.2f}"
    except (ValueError, TypeError):
        return "₹0.00"

def format_date(value, format='%Y-%m-%d'):
    if value is None:
        return ""
    try:
        if isinstance(value, str):
            value = datetime.strptime(value, '%Y-%m-%d')
        return value.strftime(format)
    except (ValueError, TypeError):
        return ""

# Add filters to main application templates
templates.env.filters["currency"] = format_currency
templates.env.filters["dateformat"] = format_date

# Custom exception handlers
@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    if request.url.path.startswith('/api/'):
        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": exc.detail},
        )
    return templates.TemplateResponse(
        "error.html",
        {"request": request, "status_code": exc.status_code, "detail": exc.detail},
        status_code=exc.status_code
    )

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    if request.url.path.startswith('/api/'):
        return JSONResponse(
            status_code=422,
            content={"detail": exc.errors(), "body": exc.body},
        )
    # For non-API routes, redirect to appropriate page or show error
    return templates.TemplateResponse(
        "error.html",
        {"request": request, "status_code": 422, "detail": "Validation error"},
        status_code=422
    )

# Global exception handler to catch all errors
@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    # Print the full traceback to console for debugging
    traceback.print_exc()

    # Return a detailed error response
    error_detail = f"Error: {str(exc)}\n\n{traceback.format_exc()}"
    
    if request.url.path.startswith('/api/'):
        return JSONResponse(
            status_code=500,
            content={"deatil": "Internal Server Error", "error": str(exc)},
        )
    # Return a simple error message
    return PlainTextResponse(
        f"Internal Server Error: {str(exc)}",
        status_code=500
    )

# Update the template context function
def template_context(request: Request):
    return {
        "current_date": datetime.now().date(),
        "current_datetime": datetime.now(),
        "request": request
    }

# Update the root endpoint
@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    context = template_context(request)
    return templates.TemplateResponse("index.html", context)

# Health check endpoint
@app.get("/health")
async def health_check():
    return {
        "status": "healthy", 
        "timestamp": datetime.now(),
    }

# API info endpoint
@app.get("/api/info")
async def api_info():
    return {
        "name": "Inventory Management System",
        "version": "1.0.0",
        "description": "A comprehensive inventory management system"
    }

@app.get("/api/test")
async def test_endpoint():
    return {"message": "API is working", "status": "success"}

# Import and include routers after all basic routes are defined
try:
    from app.routers import frontend
    app.include_router(frontend.router)
    print("Frontend router imported successfully")
except ImportError as e:
    print(f"Failed to import frontend router: {e}")
    import traceback
    traceback.print_exc()

try:
    from app.routers import dealers
    app.include_router(dealers.router, prefix="/dealers")
    print("Dealers router imported successfully")
except ImportError as e:
    print(f"Failed to import dealers router: {e}")
    import traceback
    traceback.print_exc()

try:
    from app.routers import storage
    app.include_router(storage.router, prefix="/storage")
    print("Storages router imported successfully")
except ImportError as e:
    print(f"Failed to import storage router: {e}")
    import traceback
    traceback.print_exc()    

# Add Products router
try:
    from app.routers import products
    app.include_router(products.router, prefix="/products")
    print("Products router imported successfully")
except ImportError as e:
    print(f"Failed to import products router: {e}")
    import traceback
    traceback.print_exc()    

# Add Purchase Orders router
try:
    from app.routers import purchase_orders
    app.include_router(purchase_orders.router, prefix="/purchase_orders")
    print("Purchase orders router imported successfully")
except ImportError as e:
    print(f"Failed to import purchase orders router: {e}")
    import traceback
    traceback.print_exc()

# Add Company Branches router
try:
    from app.routers import company_branches
    app.include_router(company_branches.router, prefix="/company_branches")
    print("Company branches router imported successfully")
except ImportError as e:
    print(f"Failed to import company branches router: {e}")
    import traceback
    traceback.print_exc()

# Add Consignees router
try:
    from app.routers import consignees
    app.include_router(consignees.router, prefix="/consignees")
    print("Consignees router imported successfully")
except ImportError as e:
    print(f"Failed to import consignees router: {e}")
    import traceback
    traceback.print_exc()

# Add Material Inward router
try:
    from app.routers import material_inward
    app.include_router(material_inward.router, prefix="/material_inward")
    print("Material Inward router imported successfully")
except ImportError as e:
    print(f"Failed to import material inward router: {e}")
    import traceback
    traceback.print_exc()

# Add this after the other router imports
try:
    from app.routers import test
    app.include_router(test.router, prefix="/test")
    print("Test router imported successfully")
except ImportError as e:
    print(f"Failed to import test router: {e}")
    import traceback
    traceback.print_exc()    

# Import database and models after the app is created
try:
    from app.database import engine, get_db
    from app import models
    
    # Create all tables
    models.Base.metadata.create_all(bind=engine)
    print("Database tables created successfully")
except ImportError as e:
    print(f"Failed to import database modules: {e}")
except Exception as e:
    print(f"Failed to create database tables: {e}")

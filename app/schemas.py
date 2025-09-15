from pydantic import BaseModel, EmailStr
from typing import List, Optional
from datetime import datetime

# Dealer Schemas
class DealerBase(BaseModel):
    name: str
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    country: Optional[str] = None
    pincode: Optional[str] = None
    telephone: Optional[str] = None
    mobile: Optional[str] = None
    email: Optional[EmailStr] = None
    gst_no: Optional[str] = None
    bank_name: Optional[str] = None
    account_no: Optional[str] = None
    ifsc_code: Optional[str] = None

class DealerDetails(DealerBase):
    pass

class DealerCreate(DealerBase):
    pass

class DealerUpdate(DealerBase):
    pass

class Dealer(DealerBase):
    id: int
    created_at: datetime
    updated_at: datetime
    
    class Config:
        orm_mode = True

# Storage Schemas
class StorageBase(BaseModel):
    base_name: str
    defined_name_with_spec: Optional[str] = None
    brand: Optional[str] = None
    hsn_code: Optional[str] = None
    dealer_id: Optional[int] = None
    tax: Optional[float] = 0
    price: Optional[float] = 0
    current_stock: Optional[float] = 0
    units: Optional[str] = None

class StorageCreate(StorageBase):
    pass

class StorageUpdate(StorageBase):
    pass

class Storage(StorageBase):
    id: int
    created_at: datetime
    updated_at: datetime
    
    class Config:
        orm_mode = True

# For API responses that include dealer information
class StorageWithDealer(Storage):
    dealer_name: Optional[str] = None
    dealer: Optional[dict] = None
    
    class Config:
        orm_mode = True

# Product Schemas
class ProductBase(BaseModel):
    product_name: str
    product_description: Optional[str] = None
    section_name: Optional[str] = None

class ProductCreate(ProductBase):
    pass

class Product(ProductBase):
    id: int
    
    class Config:
        orm_mode = True

# Add similar schemas for other models as needed

# Add to your existing schemas
class ProductMaterialBase(BaseModel):
    storage_id: int
    quantity_needed: int

class ProductMaterialCreate(ProductMaterialBase):
    pass

class ProductMaterial(ProductMaterialBase):
    class Config:
        orm_mode = True

class ProductBase(BaseModel):
    product_name: str
    product_description: Optional[str] = None
    section_name: Optional[str] = None

class ProductCreate(ProductBase):
    pass

class ProductUpdate(ProductBase):
    pass

class Product(ProductBase):
    id: int
    created_at: datetime
    updated_at: datetime
    
    class Config:
        orm_mode = True

class ProductWithMaterials(Product):
    product_materials: List[ProductMaterial] = []
    
    class Config:
        orm_mode = True
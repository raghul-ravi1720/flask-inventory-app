from pydantic import BaseModel, EmailStr, Field
from typing import List, Optional
from datetime import datetime, date

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

# Consignee Schemas
class ConsigneeBase(BaseModel):
    company_name: str = Field(..., max_length=120)
    branch_name: str = Field(..., max_length=120)
    address: str = Field(..., max_length=250)
    city: str = Field(..., max_length=100)
    state: str = Field(..., max_length=100)
    pincode: str = Field(..., max_length=20)
    gst_no: str = Field(..., max_length=50)
    state_code: str = Field(..., max_length=10)
    email: str = Field(..., max_length=120)
    branch_indicator: str = Field(..., max_length=1)

class ConsigneeCreate(ConsigneeBase):
    pass

class ConsigneeUpdate(ConsigneeBase):
    pass

class Consignee(ConsigneeBase):
    id: int
    
    class Config:
        orm_mode = True
        from_attributes = True

# CompanyBranch Schemas
class CompanyBranchBase(BaseModel):
    company_name: str = Field(..., max_length=120)
    branch_name: str = Field(..., max_length=120)
    address: str = Field(..., max_length=250)
    city: str = Field(..., max_length=100)
    state: str = Field(..., max_length=100)
    pincode: str = Field(..., max_length=20)
    gst_no: str = Field(..., max_length=50)
    state_code: str = Field(..., max_length=10)
    email: str = Field(..., max_length=120)
    branch_indicator: str = Field(..., max_length=1)

class CompanyBranchCreate(CompanyBranchBase):
    pass

class CompanyBranchUpdate(CompanyBranchBase):
    pass

class CompanyBranch(CompanyBranchBase):
    id: int
    
    class Config:
        orm_mode = True
        from_attributes = True

# Purchase Order Schemas (for reference, since you mentioned PO needs these)
class PurchaseOrderBase(BaseModel):
    dealer_id: Optional[int] = None
    date: Optional[datetime] = None
    status: Optional[str] = None
    notes: Optional[str] = None
    discount: Optional[float] = None
    invoice_branch_id: Optional[int] = None
    consignee_id: Optional[int] = None

class PurchaseOrderCreate(PurchaseOrderBase):
    pass

class PurchaseOrderUpdate(PurchaseOrderBase):
    pass

class PurchaseOrder(PurchaseOrderBase):
    po_no: int
    dealer: Optional[dict] = None
    invoice_branch: Optional[dict] = None
    consignee: Optional[dict] = None
    items: Optional[list] = None
    
    class Config:
        orm_mode = True
        from_attributes = True        

class MaterialInwardBase(BaseModel):
    po_no: int
    dealer_name: Optional[str]
    po_date: Optional[date]
    date_of_inward: Optional[date]
    bill_no: Optional[str]
    bill_date: Optional[date]
    cost: Optional[float]
    payment_method: Optional[str]
    pending_materials: Optional[str]

class MaterialInwardCreate(MaterialInwardBase):
    pass

class MaterialInwardUpdate(MaterialInwardBase):
    pass

class MaterialInward(MaterialInwardBase):
    id: int

    class Config:
        orm_mode = True        
from sqlalchemy import Column, Integer, String, Float, Text, Boolean, Date, DateTime, ForeignKey, Table
from sqlalchemy.orm import relationship, backref
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime, date
import random

Base = declarative_base()

# Association table for Product and Storage many-to-many relationship
product_material = Table(
    'product_material',
    Base.metadata,
    Column('product_id', Integer, ForeignKey('product.id'), primary_key=True),
    Column('storage_id', Integer, ForeignKey('storage.id'), primary_key=True),
    Column('quantity_needed', Integer, nullable=False, default=1)
)

class Dealer(Base):
    __tablename__ = 'dealer'
    
    id = Column(Integer, primary_key=True)
    name = Column(String(120), nullable=False)
    address = Column(String(250))
    city = Column(String(100))
    state = Column(String(100))
    country = Column(String(100))
    pincode = Column(String(20))
    telephone = Column(String(50))
    mobile = Column(String(50))
    email = Column(String(120))
    gst_no = Column(String(50))
    bank_name = Column(String(100))
    account_no = Column(String(100))
    ifsc_code = Column(String(50))
    
    materials = relationship('Storage', back_populates='dealer', lazy='dynamic')

class Product(Base):
    __tablename__ = 'product'
    
    id = Column(Integer, primary_key=True)
    product_name = Column(String(128), nullable=False)
    product_description = Column(Text)
    section_name = Column(String(128))
    
    # Many-to-many relationship with Storage through product_material table
    materials = relationship(
        'Storage', 
        secondary=product_material,
        back_populates='products'
    )
    
    boms = relationship('BOM', back_populates='product')

class Storage(Base):
    __tablename__ = 'storage'
    
    id = Column(Integer, primary_key=True)
    base_name = Column(String(128))
    defined_name_with_spec = Column(String(256))
    brand = Column(String(128))
    hsn_code = Column(String(32))
    dealer_id = Column(Integer, ForeignKey('dealer.id'))
    tax = Column(Float)
    price = Column(Float)
    current_stock = Column(Float)
    units = Column(String(32))
    
    dealer = relationship('Dealer', back_populates='materials')
    
    # Many-to-many relationship with Product
    products = relationship(
        'Product', 
        secondary=product_material,
        back_populates='materials'
    )
    
    bom_materials = relationship('BOMMaterial', back_populates='storage')
    supply_items = relationship('BOMSupplyItem', back_populates='storage')
    po_items = relationship('PurchaseOrderItem', back_populates='material')

class BOM(Base):
    __tablename__ = 'bom'
    
    id = Column(Integer, primary_key=True)
    product_id = Column(Integer, ForeignKey('product.id'))
    product_quantity = Column(Integer)
    consignee = Column(String(128))
    date = Column(Date, default=date.today)
    status = Column(String(20), default='pending')
    completion_date = Column(Date, nullable=True)
    notes = Column(Text)
    bom_identifier = Column(String(50), unique=True, nullable=False)
    
    product = relationship('Product', back_populates='boms')
    materials = relationship('BOMMaterial', back_populates='bom', cascade='all, delete-orphan')
    supply_transactions = relationship('BOMSupplyTransaction', back_populates='bom', cascade='all, delete-orphan')
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        if not self.bom_identifier:
            self.bom_identifier = f"BOM-{datetime.now().strftime('%Y%m%d-%H%M%S')}-{random.randint(1000, 9999)}"
    
    @property
    def total_required_materials(self):
        return sum(m.quantity_required for m in self.materials)
    
    @property
    def total_provided_materials(self):
        provided = 0
        for transaction in self.supply_transactions:
            for item in transaction.supply_items:
                provided += item.quantity_provided
        return provided
    
    @property
    def progress_percentage(self):
        if self.total_required_materials == 0:
            return 0
        return (self.total_provided_materials / self.total_required_materials) * 100

class BOMMaterial(Base):
    __tablename__ = 'bom_material'
    
    id = Column(Integer, primary_key=True)
    bom_id = Column(Integer, ForeignKey('bom.id'))
    storage_id = Column(Integer, ForeignKey('storage.id'))
    quantity_required = Column(Float)
    quantity_provided = Column(Float, default=0)
    is_fully_provided = Column(Boolean, default=False)
    
    bom = relationship('BOM', back_populates='materials')
    storage = relationship('Storage', back_populates='bom_materials')

class BOMSupplyTransaction(Base):
    __tablename__ = 'bom_supply_transaction'
    
    id = Column(Integer, primary_key=True)
    bom_id = Column(Integer, ForeignKey('bom.id'))
    supply_date = Column(Date, default=date.today)
    supply_type = Column(String(20))
    notes = Column(Text)
    
    bom = relationship('BOM', back_populates='supply_transactions')
    supply_items = relationship('BOMSupplyItem', back_populates='transaction', cascade='all, delete-orphan')

class BOMSupplyItem(Base):
    __tablename__ = 'bom_supply_item'
    
    id = Column(Integer, primary_key=True)
    transaction_id = Column(Integer, ForeignKey('bom_supply_transaction.id'))
    bom_id = Column(Integer, ForeignKey('bom.id'))
    storage_id = Column(Integer, ForeignKey('storage.id'))
    quantity_provided = Column(Float)
    
    transaction = relationship('BOMSupplyTransaction', back_populates='supply_items')
    storage = relationship('Storage', back_populates='supply_items')
    bom = relationship('BOM')

class CompanyBranch(Base):
    __tablename__ = 'company_branches'
    
    id = Column(Integer, primary_key=True)
    company_name = Column(String(120), nullable=False)
    branch_name = Column(String(120), nullable=False)
    address = Column(String(250), nullable=False)
    city = Column(String(100), nullable=False)
    state = Column(String(100), nullable=False)
    pincode = Column(String(20), nullable=False)
    gst_no = Column(String(50), nullable=False)
    state_code = Column(String(10), nullable=False)
    email = Column(String(120), nullable=False)
    branch_indicator = Column(String(1), nullable=False)
    
    def __repr__(self):
        return f'<CompanyBranch {self.branch_name}>'

class Consignee(Base):
    __tablename__ = 'consignees'
    
    id = Column(Integer, primary_key=True)
    company_name = Column(String(120), nullable=False)
    branch_name = Column(String(120), nullable=False)
    address = Column(String(250), nullable=False)
    city = Column(String(100), nullable=False)
    state = Column(String(100), nullable=False)
    pincode = Column(String(20), nullable=False)
    gst_no = Column(String(50), nullable=False)
    state_code = Column(String(10), nullable=False)
    email = Column(String(120), nullable=False)
    branch_indicator = Column(String(1), nullable=False)
    
    def __repr__(self):
        return f'<Consignee {self.branch_name}>'

class PurchaseOrder(Base):
    __tablename__ = 'purchase_order'
    
    po_no = Column(Integer, primary_key=True)
    dealer_id = Column(Integer, ForeignKey('dealer.id'))
    date = Column(Date, default=date.today)
    status = Column(String(20))
    notes = Column(Text)
    discount = Column(Float, default=0.0)
    invoice_branch_id = Column(Integer, ForeignKey('company_branches.id'))
    consignee_id = Column(Integer, ForeignKey('consignees.id'))
    
    dealer = relationship('Dealer', backref='purchase_orders')
    invoice_branch = relationship('CompanyBranch', foreign_keys=[invoice_branch_id])
    consignee = relationship('Consignee', foreign_keys=[consignee_id])
    items = relationship('PurchaseOrderItem', back_populates='purchase_order', cascade='all, delete-orphan')
    
    @property
    def total_quantity(self):
        return sum(item.quantity for item in self.items)
    
    @property
    def subtotal(self):
        return sum(item.price * item.quantity for item in self.items)
    
    @property
    def tax_amount(self):
        return self.subtotal * 0.1  # 10% tax
    
    @property
    def discount_amount(self):
        return self.subtotal * (self.discount / 100)
    
    @property
    def grand_total(self):
        return self.subtotal + self.tax_amount - self.discount_amount
    
    @property
    def total(self):
        return self.subtotal
    
    @property
    def voucher_number(self):
        current_year = self.date.year % 100
        next_year = current_year + 1
        return f"PO-{self.invoice_branch.branch_indicator if self.invoice_branch else 'N'}-{self.po_no}-{current_year}-{next_year}"

class PurchaseOrderItem(Base):
    __tablename__ = 'purchase_order_item'
    
    id = Column(Integer, primary_key=True)
    po_no = Column(Integer, ForeignKey('purchase_order.po_no'))
    material_id = Column(Integer, ForeignKey('storage.id'))
    material_name = Column(String(256))
    spec = Column(String(256))
    brand = Column(String(128))
    dealer_name = Column(String(120))
    quantity = Column(Integer)
    price = Column(Float)
    unit = Column(String(50))
    
    purchase_order = relationship('PurchaseOrder', back_populates='items')
    material = relationship('Storage', back_populates='po_items')

class MaterialInward(Base):
    __tablename__ = 'material_inward'
    
    id = Column(Integer, primary_key=True)
    po_no = Column(Integer, ForeignKey('purchase_order.po_no'))
    dealer_name = Column(String(128))
    po_date = Column(Date)
    date_of_inward = Column(Date, default=date.today)
    bill_no = Column(String(64))
    bill_date = Column(Date)
    cost = Column(Float)
    payment_method = Column(String(64))
    pending_materials = Column(Text)

class MaterialOutward(Base):
    __tablename__ = 'material_outward'
    
    id = Column(Integer, primary_key=True)
    material_details = Column(String(256))
    receiver_section = Column(String(128))
    qty = Column(Integer)
    date = Column(Date, default=date.today)
    reason = Column(String(256))

class Section(Base):
    __tablename__ = 'section'
    
    id = Column(Integer, primary_key=True)
    section_name = Column(String(128))
    products_they_create = Column(Text)
    inventory_details = Column(Text)
    product_development_status = Column(String(256))
from sqlalchemy import Column, String, Integer, Float, Boolean, ForeignKey, DateTime, JSON, Text
from sqlalchemy.orm import relationship, DeclarativeBase
from sqlalchemy.sql import func
import datetime

# LOCAL DECOUPLED MODELS
# Copied from backend/common/models.py to avoid 'backend' package dependency on Railway
# This ensures the service is self-contained.

class Base(DeclarativeBase):
    pass

class Project(Base):
    __tablename__ = 'bim_projects'
    
    id = Column(String, primary_key=True) # Custom ID or UUID
    name = Column(String, nullable=False)
    description = Column(Text, nullable=True) 
    status = Column(String, default="Active")
    created_at = Column(DateTime, server_default=func.now())
    organization_id = Column(String, nullable=False, index=True)
    
    # Real Schema uses 'settings' (JSON) for extra data
    settings = Column(JSON, default={}) 
    archived = Column(Boolean, default=False) # Exists in bim_projects? If not, move to settings. 
    # Checking common/models.py: archived was created in line 41 but as legacy? 
    # Actually line 356 in common/models.py had settings. 
    # Line 20 status exists. 
    # Line 41 archived exists? NO, it was commented out in common/models.py or not shown in BIM section.
    # Wait, line 348 in common/models.py showed BimProject but lines 13-65 showed Project.
    # The 'Project' at top of common/models.py mapped to 'bim_projects'.
    # REQUIRED FIELDS FOR STABILITY
    # archived = Column(Boolean, default=False) # DOES NOT EXIST IN DB

    # PROXY PROPERTIES for Finance Compatibility
    # These allow the app to treat 'client', 'amount' as attributes, but they store in 'settings'
    
    @property
    def archived(self): return self.settings.get('finance', {}).get('archived', False)
    @archived.setter
    def archived(self, value):
        s = dict(self.settings) if self.settings else {}
        if 'finance' not in s: s['finance'] = {}
        s['finance']['archived'] = value
        self.settings = s
    
    @property
    def client(self): return self.settings.get('finance', {}).get('client', "")
    @client.setter
    def client(self, value): 
        s = dict(self.settings) if self.settings else {}
        if 'finance' not in s: s['finance'] = {}
        s['finance']['client'] = value
        self.settings = s

    @property
    def amount(self): return self.settings.get('finance', {}).get('amount', 0.0)
    @amount.setter
    def amount(self, value):
        s = dict(self.settings) if self.settings else {}
        if 'finance' not in s: s['finance'] = {}
        s['finance']['amount'] = value
        self.settings = s
        
    @property
    def square_meters(self): return self.settings.get('finance', {}).get('square_meters', 0.0)
    @square_meters.setter
    def square_meters(self, value):
        s = dict(self.settings) if self.settings else {}
        if 'finance' not in s: s['finance'] = {}
        s['finance']['square_meters'] = value
        self.settings = s

    @property
    def start_date(self): return self.settings.get('finance', {}).get('start_date', "")
    @start_date.setter
    def start_date(self, value):
        s = dict(self.settings) if self.settings else {}
        if 'finance' not in s: s['finance'] = {}
        s['finance']['start_date'] = value
        self.settings = s
        
    @property
    def duration_months(self): return self.settings.get('finance', {}).get('duration_months', 0.0)
    @duration_months.setter
    def duration_months(self, value):
        s = dict(self.settings) if self.settings else {}
        if 'finance' not in s: s['finance'] = {}
        s['finance']['duration_months'] = value
        self.settings = s
        
    @property
    def additional_time_months(self): return self.settings.get('finance', {}).get('additional_time_months', 0.0)
    @additional_time_months.setter
    def additional_time_months(self, value):
        s = dict(self.settings) if self.settings else {}
        if 'finance' not in s: s['finance'] = {}
        s['finance']['additional_time_months'] = value
        self.settings = s

    @property
    def paid_amount(self): return self.settings.get('finance', {}).get('paid_amount', 0.0)
    @paid_amount.setter
    def paid_amount(self, value):
        s = dict(self.settings) if self.settings else {}
        if 'finance' not in s: s['finance'] = {}
        s['finance']['paid_amount'] = value
        self.settings = s
        
    @property
    def emoji(self): return self.settings.get('finance', {}).get('emoji', "📁")
    @emoji.setter
    def emoji(self, value):
        s = dict(self.settings) if self.settings else {}
        if 'finance' not in s: s['finance'] = {}
        s['finance']['emoji'] = value
        self.settings = s
        
    @property
    def category(self): return self.settings.get('finance', {}).get('category', "Residencial")
    @category.setter
    def category(self, value):
        s = dict(self.settings) if self.settings else {}
        if 'finance' not in s: s['finance'] = {}
        s['finance']['category'] = value
        self.settings = s

    @property
    def nit(self): return self.settings.get('finance', {}).get('nit', "")
    @nit.setter
    def nit(self, value):
        s = dict(self.settings) if self.settings else {}
        if 'finance' not in s: s['finance'] = {}
        s['finance']['nit'] = value
        self.settings = s
        
    @property
    def legal_name(self): return self.settings.get('finance', {}).get('legal_name', "")
    @legal_name.setter
    def legal_name(self, value):
        s = dict(self.settings) if self.settings else {}
        if 'finance' not in s: s['finance'] = {}
        s['finance']['legal_name'] = value
        self.settings = s
        
    @property
    def po_number(self): return self.settings.get('finance', {}).get('po_number', "")
    @po_number.setter
    def po_number(self, value):
        s = dict(self.settings) if self.settings else {}
        if 'finance' not in s: s['finance'] = {}
        s['finance']['po_number'] = value
        self.settings = s
        
    @property
    def estimation_data(self): return self.settings.get('finance', {}).get('estimation_data', {})
    @estimation_data.setter
    def estimation_data(self, value):
        s = dict(self.settings) if self.settings else {}
        if 'finance' not in s: s['finance'] = {}
        s['finance']['estimation_data'] = value
        self.settings = s


class Collaborator(Base):
    __tablename__ = 'resources_collaborators'
    
    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    email = Column(String)
    role = Column(String, default="Collaborator")
    base_salary = Column(Float, default=0.0)
    bonus_incentive = Column(Float, default=0.0)
    salary = Column(Float, default=0.0) # Total
    birthday = Column(String)
    start_date = Column(String)
    accumulated_liability = Column(Float, default=0.0)
    profile_picture = Column(String)
    status = Column(String, default="Activo")
    archived = Column(Boolean, default=False)
    
    adjustments = Column(JSON, default=[])

class ExpenseColumn(Base):
    __tablename__ = 'resources_expense_columns'
    
    id = Column(String, primary_key=True)
    title = Column(String)
    order_index = Column(Integer, default=0)
    
    cards = relationship("ExpenseCard", back_populates="column", cascade="all, delete-orphan")

class ExpenseCard(Base):
    __tablename__ = 'resources_expense_cards'
    
    id = Column(String, primary_key=True)
    column_id = Column(String, ForeignKey('resources_expense_columns.id'))
    title = Column(String)
    amount = Column(Float, default=0.0)
    date = Column(String)
    notes = Column(Text, default="")
    files = Column(JSON, default={}) # {filename: path}
    
    column = relationship("ExpenseColumn", back_populates="cards")

class Quotation(Base):
    __tablename__ = 'resources_quotations'
    
    id = Column(String, primary_key=True)
    title = Column(String)
    client_name = Column(String)
    project_type = Column(String, default="Residencial")
    status = Column(String, default="Borrador") # Borrador, Enviada, Aprobada
    
    # Block-based content: [{type: 'text', ...}, {type: 'timeline', ...}]
    content_json = Column(JSON, default=[]) 
    
    total_amount = Column(Float, default=0.0)
    
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

class QuotationTemplate(Base):
    __tablename__ = 'resources_quotation_templates'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, nullable=False)
    content_json = Column(JSON, default=[])
    created_at = Column(DateTime, default=func.now())

# LEGACY COMPAT: Stubs for shared database.py usage
class AppUser(Base):
    __tablename__ = 'resources_users'
    email = Column(String, primary_key=True)
    full_name = Column(String)
    hashed_password = Column(String)
    role = Column(String)
    is_active = Column(Boolean)
    permissions = Column(JSON)

class TimelineEvent(Base):
    __tablename__ = 'resources_timeline_events'
    id = Column(Integer, primary_key=True)

class ContactSubmission(Base):
    __tablename__ = 'web_contact_submissions'
    id = Column(Integer, primary_key=True)

class PluginSheetSession(Base):
    __tablename__ = 'plugin_sheet_sessions'
    id = Column(String, primary_key=True)

class SheetTemplate(Base):
    __tablename__ = 'plugin_sheet_templates'
    id = Column(Integer, primary_key=True)

# Backward-compat alias for legacy imports
AccountUser = AppUser

 

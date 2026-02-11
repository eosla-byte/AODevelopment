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
    
    # Core Project Profile Fields
    organization_id = Column(String, ForeignKey('accounts_organizations.id', ondelete="CASCADE"), nullable=False, index=True)

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

# Models used in finance but not critical locally can be omitted or added if needed
# ContactSubmission? AppUser? 

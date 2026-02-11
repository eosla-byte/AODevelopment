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
    # Core Project Profile Fields
    organization_id = Column(String, nullable=False, index=True) # ForeignKey removed for Railway service decoupling
    
    # REQUIRED FIELDS FOR STABILITY
    archived = Column(Boolean, default=False)
    status = Column(String, default="Active")


    # Relationships are optional in local definition if we don't eager load them or use them in this service
    # But keeping them prevents mapper errors if code tries to access them
    # Note: Target classes must be defined or handled loosely.
    # For now, we define Project. Organization will be defined if needed or we use string reference.
    # organization = relationship("Organization", back_populates="projects")
    
    
# We only define what Accounts service needs for now, or what is critical for startup.
# If Accounts database.py imports other models, we need them here or mocked.

# LEGACY COMPAT: Type Hint Stubs
# database.py type hints reference these, so they must exist as attributes of this module.
class Collaborator(Base):
    __tablename__ = 'resources_collaborators'
    id = Column(String, primary_key=True)
    name = Column(String)
    email = Column(String)
    created_at = Column(DateTime, default=func.now())
    # Minimal definition to satisfy "List[models.Collaborator]" type hint

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

class ExpenseColumn(Base):
    __tablename__ = 'resources_expense_columns'
    id = Column(String, primary_key=True)

class ExpenseCard(Base):
    __tablename__ = 'resources_expense_cards'
    id = Column(String, primary_key=True)

class PluginSheetSession(Base):
    __tablename__ = 'plugin_sheet_sessions'
    id = Column(String, primary_key=True)

class Quotation(Base):
    __tablename__ = 'resources_quotations'
    id = Column(String, primary_key=True)

class QuotationTemplate(Base):
    __tablename__ = 'resources_quotation_templates'
    id = Column(Integer, primary_key=True)

class SheetTemplate(Base):
    __tablename__ = 'plugin_sheet_templates'
    id = Column(Integer, primary_key=True)




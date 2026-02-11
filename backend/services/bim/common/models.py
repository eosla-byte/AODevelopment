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


class BimScheduleVersion(Base):
    __tablename__ = 'bim_schedule_versions'
    
    id = Column(String, primary_key=True)
    project_id = Column(String, ForeignKey('bim_projects.id'))
    version_name = Column(String) # e.g. "Baseline 1", "Update Nov"
    imported_at = Column(DateTime, default=func.now())
    imported_by = Column(String, ForeignKey('bim_users.id')) # Loose FK reference if BimUser not local
    source_filename = Column(String)
    source_type = Column(String) # P6, MSP
    
    activities = relationship("BimActivity", back_populates="version", cascade="all, delete-orphan")

class BimActivity(Base):
    __tablename__ = 'bim_activities'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    version_id = Column(String, ForeignKey('bim_schedule_versions.id'))
    
    activity_id = Column(String) # The P6 Activity ID (e.g. A1000)
    wbs_code = Column(String)
    name = Column(String, nullable=False)
    
    planned_start = Column(DateTime)
    planned_finish = Column(DateTime)
    actual_start = Column(DateTime)
    actual_finish = Column(DateTime)
    
    duration = Column(Float)
    pct_complete = Column(Float, default=0.0)
    
    # Advanced Gantt Fields
    contractor = Column(String) # Empresa Encargada
    predecessors = Column(String) # JSON or String "1,2,3"
    display_order = Column(Integer, default=0) # For manual row reordering
    style = Column(String) # JSON: {"font": "Calibri", "fontSize": 11, "bold": true, "fill": "#ffff00", "color": "#ff0000"}
    cell_styles = Column(JSON, default={}) # New: {"colId": {"backgroundColor": "red"}}
    comments = Column(JSON, default=[]) # Log of delays/notes
    
    # New Fields for Advanced Gantt
    extension_days = Column(Integer, default=0)
    history = Column(JSON, default=[]) # [{date, progress, user}]
    # Force Rebuild Check 2
    
    # Hierarchy
    parent_wbs = Column(String)
    
    # Relationships
    version = relationship("BimScheduleVersion", back_populates="activities")

    # Relationships
    version = relationship("BimScheduleVersion", back_populates="activities")

# BIM User/Org might be needed but they can be mocked or referred loosely

# LEGACY COMPAT: Type Hint Stubs
class Collaborator(Base):
    __tablename__ = 'resources_collaborators'
    id = Column(String, primary_key=True)
    name = Column(String)

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

# Backward-compat alias for legacy imports
AccountUser = AppUser




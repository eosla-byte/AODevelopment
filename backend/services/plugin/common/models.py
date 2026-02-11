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


# PLUGIN SPECIFIC MODELS
class PluginLicense(Base):
    __tablename__ = 'plugin_licenses'
    
    machine_id = Column(String, primary_key=True)
    user_email = Column(String, ForeignKey('resources_users.email'))
    status = Column(String) # APROBADO, PENDIENTE, BLOQUEADO
    last_check_in = Column(DateTime)
    
class PluginLog(Base):
    __tablename__ = 'plugin_logs'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_email = Column(String)
    machine_id = Column(String)
    command_name = Column(String)
    duration_ms = Column(Integer)
    timestamp = Column(DateTime, default=func.now())
    context_data = Column(JSON) # Project name, file name, etc.

class PluginSession(Base):
    __tablename__ = 'plugin_sessions'
    
    id = Column(String, primary_key=True) # UUID
    user_email = Column(String)
    machine_id = Column(String)
    revit_version = Column(String)
    plugin_version = Column(String, default="1.0.0")
    ip_address = Column(String)
    start_time = Column(DateTime, default=func.now())
    last_heartbeat = Column(DateTime, default=func.now())
    is_active = Column(Boolean, default=True)

class PluginActivity(Base):
    __tablename__ = 'plugin_activities'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String, ForeignKey('plugin_sessions.id'))
    filename = Column(String)
    active_minutes = Column(Float, default=0.0)
    idle_minutes = Column(Float, default=0.0)
    timestamp = Column(DateTime, default=func.now()) 
    revit_user = Column(String)
    acc_project = Column(String)
    
    session = relationship("PluginSession")

class PluginVersion(Base):
    __tablename__ = 'plugin_versions'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    version_number = Column(String, unique=True, nullable=False)
    changelog = Column(Text)
    download_url = Column(String)
    is_mandatory = Column(Boolean, default=False)
    released_at = Column(DateTime, default=func.now())

class PluginProjectFolder(Base):
    __tablename__ = 'plugin_project_folders'
    
    id = Column(String, primary_key=True) # UUID
    name = Column(String, nullable=False)
    created_at = Column(DateTime, default=func.now())
    
    sessions = relationship("PluginCloudSession", back_populates="folder")

class PluginCloudSession(Base):
    # NOT Inheriting from Base because we might want raw JSON handling or simple table?
    # Wait, using Base allows ORM.
    __tablename__ = 'plugin_cloud_sessions'
    
    id = Column(String, primary_key=True) # UUID
    user_email = Column(String)
    project_name = Column(String, default="Proyecto Sin Nombre")
    folder_id = Column(String, ForeignKey('plugin_project_folders.id'), nullable=True)
    folder = relationship("PluginProjectFolder", back_populates="sessions")
    data_json = Column(JSON, default={}) # Stores { cards: [], groups: [], sheets: [], revit_data: ... }
    timestamp = Column(DateTime, default=func.now(), onupdate=func.now())

class CloudCommand(Base):
    __tablename__ = 'plugin_cloud_commands'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String, index=True)
    action = Column(String)
    payload = Column(JSON)
    status = Column(String, default="pending") # pending, sent, success, error
    result_json = Column(JSON, nullable=True) 
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    is_consumed = Column(Boolean, default=False)

class PluginRoutine(Base):
    __tablename__ = 'plugin_routines'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String, nullable=False)
    description = Column(Text) # The 'Prompt' or Explanation
    category = Column(String, default="General") # Documentacion, Modelado
    actions_json = Column(JSON, default=[]) # The recorded steps
    is_global = Column(Boolean, default=False)
    user_email = Column(String)
    created_at = Column(DateTime, default=func.now())

class SheetTemplate(Base):
    __tablename__ = 'plugin_sheet_templates'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, nullable=False)
    config_json = Column(JSON, default={}) # { visible_columns: [], filters: {} }
    is_global = Column(Boolean, default=True)
    created_by = Column(String, default="Admin")
    created_at = Column(DateTime, default=func.now())

class PluginSheetSession(Base):
    __tablename__ = 'plugin_sheet_sessions'
    
    id = Column(String, primary_key=True) # UUID
    project = Column(String)
    plugin_session_id = Column(String)
    sheets_json = Column(JSON)
    param_definitions_json = Column(JSON, default=[])
    created_at = Column(DateTime, default=func.now())
    expires_at = Column(DateTime, nullable=True) # Optional expiration logic logic

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




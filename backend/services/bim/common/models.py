from sqlalchemy import Column, String, Integer, Float, Boolean, ForeignKey, DateTime, JSON, Text, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from sqlalchemy.sql import func
import datetime

Base = declarative_base()

# -----------------------------------------------------------------------------
# SCHEMA: RESOURCES (Gestion Interna) -> Prefix 'resources_'
# -----------------------------------------------------------------------------

class Project(Base):
    __tablename__ = 'resources_projects'
    # __table_args__ = {'schema': 'resources'} # Commented for SQLite compatibility

    id = Column(String, primary_key=True) # Custom ID or UUID
    name = Column(String, nullable=False)
    client = Column(String)
    status = Column(String, default="Activo")
    nit = Column(String)
    legal_name = Column(String)
    po_number = Column(String)
    amount = Column(Float, default=0.0)
    paid_amount = Column(Float, default=0.0)
    emoji = Column(String, default="📁")
    category = Column(String, default="Residencial")
    square_meters = Column(Float, default=0.0)
    start_date = Column(String) # ISO String
    duration_months = Column(Float, default=0.0)
    additional_time_months = Column(Float, default=0.0)
    archived = Column(Boolean, default=False)
    
    # Financial metrics
    projected_profit_margin = Column(Float, default=0.0)
    real_profit_margin = Column(Float, default=0.0)
    
    # JSON Fields for flexible data
    acc_config = Column(JSON, default={})
    partners_config = Column(JSON, default={})
    files_meta = Column(JSON, default={})
    reminders = Column(JSON, default=[])   
    assigned_collaborators = Column(JSON, default={}) # {collab_id: percentage}
    
    # Estimation Data (Resources, Financial Config)
    estimation_data = Column(JSON, default={})
    
    # Relationships
    timeline_events = relationship("TimelineEvent", back_populates="project")

class TimelineEvent(Base):
    __tablename__ = 'resources_timeline_events'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    project_id = Column(String, ForeignKey('resources_projects.id'))
    type = Column(String)
    date = Column(String)
    filename = Column(String)
    category = Column(String)
    
    project = relationship("Project", back_populates="timeline_events")

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
    
class AppUser(Base):
    __tablename__ = 'resources_users'
    
    email = Column(String, primary_key=True)
    hashed_password = Column(String, nullable=False)
    full_name = Column(String)
    role = Column(String) # Admin, Member, Reader, Collaborator
    is_active = Column(Boolean, default=True)
    permissions = Column(JSON, default={}) # { "CivilConnection": true, ... }
    assigned_projects = Column(JSON, default=[]) # List of Project IDs assigned to this user

# -----------------------------------------------------------------------------
# SCHEMA: WEB (Sitio Publico) -> Prefix 'web_'
# -----------------------------------------------------------------------------

class ContactSubmission(Base):
    __tablename__ = 'web_contact_submissions'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String)
    email = Column(String)
    phone = Column(String)
    message = Column(Text)
    created_at = Column(DateTime, default=func.now())
    ip_address = Column(String)

# -----------------------------------------------------------------------------
# SCHEMA: PLUGIN (AOdev) -> Prefix 'plugin_'
# -----------------------------------------------------------------------------

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

# -----------------------------------------------------------------------------
# SCHEMA: EXPENSES (Gastos)
# -----------------------------------------------------------------------------

class ExpenseColumn(Base):
    __tablename__ = 'resources_expense_columns'
    
    id = Column(String, primary_key=True)
    title = Column(String)
    order_index = Column(Integer, default=0)
    
    cards = relationship("ExpenseCard", back_populates="column", cascade="all, delete-orphan")

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

# -----------------------------------------------------------------------------
# SCHEMA: QUOTATIONS (Cotizaciones)
# -----------------------------------------------------------------------------

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

# -----------------------------------------------------------------------------
# SCHEMA: BIM PORTAL (External) -> Prefix 'bim_'
# -----------------------------------------------------------------------------

class BimOrganization(Base):
    __tablename__ = 'bim_organizations'
    
    id = Column(String, primary_key=True) # UUID
    name = Column(String, nullable=False)
    tax_id = Column(String) # NIT/RFC
    logo_url = Column(String)
    created_at = Column(DateTime, default=func.now())
    is_active = Column(Boolean, default=True)

    users = relationship("BimUser", back_populates="organization")
    projects = relationship("BimProject", back_populates="organization")

class BimUser(Base):
    __tablename__ = 'bim_users'
    
    id = Column(String, primary_key=True) # UUID
    organization_id = Column(String, ForeignKey('bim_organizations.id'))
    email = Column(String, unique=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    full_name = Column(String)
    role = Column(String, default="Member") # Owner, Admin, Member, Guest
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=func.now())
    
    organization = relationship("BimOrganization", back_populates="users")

class BimProject(Base):
    __tablename__ = 'bim_projects'
    
    id = Column(String, primary_key=True) # UUID
    organization_id = Column(String, ForeignKey('bim_organizations.id'))
    name = Column(String, nullable=False)
    description = Column(Text)
    status = Column(String, default="Active")
    created_at = Column(DateTime, default=func.now())
    
    organization = relationship("BimOrganization", back_populates="projects")

# -----------------------------------------------------------------------------
# SCHEMA: BIM SCHEDULE MODULE
# -----------------------------------------------------------------------------

class BimScheduleVersion(Base):
    __tablename__ = 'bim_schedule_versions'
    
    id = Column(String, primary_key=True)
    project_id = Column(String, ForeignKey('bim_projects.id'))
    version_name = Column(String) # e.g. "Baseline 1", "Update Nov"
    imported_at = Column(DateTime, default=func.now())
    imported_by = Column(String, ForeignKey('bim_users.id'))
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
    
    # Visuals & Meta
    style = Column(String) # JSON or String for simple style? Main.py treats as string.
    contractor = Column(String)
    predecessors = Column(String)
    
    # Social Comments: [{id, userId, text, timestamp, attachments:[]}]
    comments = Column(JSON, default=[])
    
    # Hierarchy
    parent_wbs = Column(String)
    
    # Relationships
    version = relationship("BimScheduleVersion", back_populates="activities")


# -----------------------------------------------------------------------------
# SCHEMA: ACCOUNTS (accounts.somosao.com) -> Prefix 'accounts_'
# -----------------------------------------------------------------------------

class AccountUser(Base):
    __tablename__ = 'accounts_users'
    
    id = Column(String, primary_key=True) # UUID
    email = Column(String, unique=True, nullable=False, index=True)
    hashed_password = Column(String, nullable=False)
    
    # Profile Info
    full_name = Column(String)
    phone = Column(String)
    
    # Global Role (Super Admin vs Standard User)
    # The diagram distinguishes "Administradores AO" from "Usuarios Administradores (de Empresa)"
    # This role handles "Administradores AO".
    role = Column(String, default="Standard") # 'SuperAdmin', 'Standard'
    status = Column(String, default="Active") # Active, Inactive
    
    # Legacy fields (Optional during migration)
    company = Column(String, nullable=True)
    services_access = Column(JSON, default={}) 
    docs_access = Column(Boolean, default=True)
    insight_access = Column(Boolean, default=True)
    
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    # V2 Relationships
    memberships = relationship("OrganizationUser", back_populates="user")

class Organization(Base):
    __tablename__ = 'accounts_organizations'
    
    id = Column(String, primary_key=True) # UUID
    name = Column(String, nullable=False)
    contact_email = Column(String)
    tax_id = Column(String) # NIT/RFC
    logo_url = Column(String)
    status = Column(String, default="Active")
    
    created_at = Column(DateTime, default=func.now())
    
    users = relationship("OrganizationUser", back_populates="organization", cascade="all, delete-orphan")
    service_permissions = relationship("ServicePermission", back_populates="organization", cascade="all, delete-orphan")

class OrganizationUser(Base):
    """
    Link between User and Organization. Defines strict role within the company.
    """
    __tablename__ = 'accounts_organization_users'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    organization_id = Column(String, ForeignKey('accounts_organizations.id'))
    user_id = Column(String, ForeignKey('accounts_users.id'))
    
    # Role within the organization: 'Admin' (Gestor de la empresa) or 'Member' (Empleado)
    role = Column(String, default="Member") 
    
    # Granular permissions for this user specifically (optional override)
    permissions = Column(JSON, default={}) 
    
    joined_at = Column(DateTime, default=func.now())
    
    organization = relationship("Organization", back_populates="users")
    user = relationship("AccountUser", back_populates="memberships")

class ServicePermission(Base):
    """
    Controls which services an Organization has access to.
    Administered by 'Administradores AO'.
    """
    __tablename__ = 'accounts_service_permissions'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    organization_id = Column(String, ForeignKey('accounts_organizations.id'))
    
    # Service Slug: 'daily', 'bim', 'plugin', 'build', 'clients'
    service_slug = Column(String, nullable=False)
    
    # Plan Level? (Free, Pro, Enterprise)
    plan_level = Column(String, default="Standard")
    
    is_active = Column(Boolean, default=True)
    valid_until = Column(DateTime, nullable=True)
    
    organization = relationship("Organization", back_populates="service_permissions")


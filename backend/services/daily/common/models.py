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

# DAILY SPECIFIC MODELS
class DailyTeam(Base):
    __tablename__ = 'daily_teams'
    
    id = Column(String, primary_key=True) # UUID
    name = Column(String, nullable=False)
    organization_id = Column(String, nullable=True) 
    owner_id = Column(String) 
    members = Column(JSON, default=[]) 
    created_at = Column(DateTime, default=func.now())
    
    projects = relationship("DailyProject", back_populates="team")

class DailyProject(Base):
    __tablename__ = 'daily_projects'
    
    id = Column(String, primary_key=True) # UUID
    organization_id = Column(String, nullable=True) 
    team_id = Column(String, ForeignKey('daily_teams.id'), nullable=True) 
    name = Column(String, nullable=False)
    description = Column(Text)
    
    resources_project_id = Column(String, nullable=True) 
    bim_project_id = Column(String, nullable=True) 
    
    settings = Column(JSON, default={}) 
    
    created_at = Column(DateTime, default=func.now())
    created_by = Column(String)
    
    team = relationship("DailyTeam", back_populates="projects")
    columns = relationship("DailyColumn", back_populates="project", cascade="all, delete-orphan", order_by="DailyColumn.order_index")
    tasks = relationship("DailyTask", back_populates="project", cascade="all, delete-orphan")
    messages = relationship("DailyMessage", back_populates="project", cascade="all, delete-orphan")

class DailyColumn(Base):
    __tablename__ = 'daily_columns'
    
    id = Column(String, primary_key=True) 
    project_id = Column(String, ForeignKey('daily_projects.id'))
    title = Column(String, nullable=False)
    order_index = Column(Integer, default=0)
    color = Column(String, default="#e2e8f0")
    
    project = relationship("DailyProject", back_populates="columns")
    tasks = relationship("DailyTask", back_populates="column")

class DailyTask(Base):
    __tablename__ = 'daily_tasks'
    
    id = Column(String, primary_key=True) 
    project_id = Column(String, ForeignKey('daily_projects.id'), nullable=True) 
    column_id = Column(String, ForeignKey('daily_columns.id'), nullable=True)
    
    title = Column(String, nullable=False)
    description = Column(Text)
    
    priority = Column(String, default="Medium") 
    status = Column(String, default="Pending") 
    due_date = Column(DateTime, nullable=True)
    
    assignees = Column(JSON, default=[]) 
    created_by = Column(String)
    
    tags = Column(JSON, default=[]) 
    checklist = Column(JSON, default=[]) 
    attachments = Column(JSON, default=[]) 
    
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    is_direct_assignment = Column(Boolean, default=False)
    
    project = relationship("DailyProject", back_populates="tasks")
    column = relationship("DailyColumn", back_populates="columns") # Wait, column back_populates tasks? Correct is tasks->column
    # Correction: DailyColumn has tasks = relationship("DailyTask", back_populates="column")
    # So DailyTask.column should back_populates="tasks" ? No.
    # DailyColumn.tasks <-> DailyTask.column
    column = relationship("DailyColumn", back_populates="tasks")

    comments = relationship("DailyComment", back_populates="task", cascade="all, delete-orphan")

class DailyComment(Base):
    __tablename__ = 'daily_comments'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    task_id = Column(String, ForeignKey('daily_tasks.id'))
    user_id = Column(String) 
    user_name = Column(String, nullable=True) 
    content = Column(Text)
    
    parent_id = Column(Integer, ForeignKey('daily_comments.id'), nullable=True)
    
    reactions = Column(JSON, default={}) 
    
    created_at = Column(DateTime, default=func.now())
    
    task = relationship("DailyTask", back_populates="comments")
    replies = relationship("DailyComment", remote_side=[id]) 

class DailyChannel(Base):
    __tablename__ = 'daily_channels'
    
    id = Column(String, primary_key=True) 
    project_id = Column(String, ForeignKey('daily_projects.id'))
    name = Column(String, nullable=False) 
    type = Column(String, default="text") 
    created_at = Column(DateTime, default=func.now())
    
    project = relationship("DailyProject", backref="channels")
    messages = relationship("DailyMessage", back_populates="channel", cascade="all, delete-orphan")

class DailyMessage(Base):
    __tablename__ = 'daily_messages'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    channel_id = Column(String, ForeignKey('daily_channels.id'), nullable=True)
    project_id = Column(String, ForeignKey('daily_projects.id'), nullable=True)
    dm_room_id = Column(String, nullable=True) 
    
    sender_id = Column(String)
    content = Column(Text)
    attachments = Column(JSON, default=[])
    mentions = Column(JSON, default=[])
    
    thread_root_id = Column(Integer, nullable=True) 
    
    created_at = Column(DateTime, default=func.now())
    
    project = relationship("DailyProject", back_populates="messages")
    channel = relationship("DailyChannel", back_populates="messages")

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



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

    # Relationships are optional in local definition if we don't eager load them or use them in this service
    # But keeping them prevents mapper errors if code tries to access them
    # Note: Target classes must be defined or handled loosely.
    # For now, we define Project. Organization will be defined if needed or we use string reference.
    # organization = relationship("Organization", back_populates="projects")
    
# We only define what Accounts service needs for now, or what is critical for startup.
# If Accounts database.py imports other models, we need them here or mocked.

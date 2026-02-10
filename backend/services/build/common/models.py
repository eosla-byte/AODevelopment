from sqlalchemy import Column, String, Integer, Float, Boolean, ForeignKey, DateTime, JSON, Text
from sqlalchemy.sql import func
from .database import Base

# SCHEMA: BUILD SERVICE -> Prefix 'build_'
# Namespaced tables to coexist in db-central during simple migration

class BuildProject(Base):
    __tablename__ = 'build_projects'
    
    id = Column(String, primary_key=True) # UUID
    name = Column(String, nullable=False)
    client_name = Column(String)
    
    # Build Specific Data
    location = Column(String)
    construction_status = Column(String, default="Pre-Construction") # Planning, In-Progress, Completed
    
    start_date = Column(DateTime)
    end_date = Column(DateTime)
    
    budget = Column(Float, default=0.0)
    spent = Column(Float, default=0.0)
    
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

class BuildReport(Base):
    __tablename__ = 'build_reports'
    
    id = Column(String, primary_key=True)
    project_id = Column(String, ForeignKey('build_projects.id'))
    
    report_date = Column(DateTime, default=func.now())
    content = Column(Text)
    weather_condition = Column(String)
    
    images = Column(JSON, default=[]) # List of URLs
    
    created_by = Column(String) # User Email/ID

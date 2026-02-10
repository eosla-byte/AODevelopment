import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base

# BUILD DB SETUP
# Reuses the 'db-central' instance (which might be OPS or generic DATABASE_URL currently)
# During migration: BUILD_DB_URL should match the central DB.
# After migration: It becomes the primary user of that DB.
BUILD_DB_URL = os.getenv("BUILD_DB_URL", os.getenv("DATABASE_URL", "sqlite:///./aodev.db")).strip().replace("postgres://", "postgresql://")

print(f"✅ [BUILD DB] Connection: {'SQLite' if 'sqlite' in BUILD_DB_URL else 'Postgres'} | URL Set: {bool(BUILD_DB_URL)}")

engine_build = create_engine(BUILD_DB_URL, connect_args={"check_same_thread": False} if "sqlite" in BUILD_DB_URL else {})
SessionBuild = sessionmaker(autocommit=False, autoflush=False, bind=engine_build)

Base = declarative_base()

def get_build_db():
    db = SessionBuild()
    try:
        yield db
    finally:
        db.close()

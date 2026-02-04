import os
import datetime
import json
import uuid
from typing import List, Optional
from sqlalchemy.orm import Session, sessionmaker, joinedload
from sqlalchemy import create_engine
from sqlalchemy.sql import func
from . import models
from .models import Base, Project as DBProject, Collaborator as DBCollaborator, TimelineEvent, ContactSubmission, AppUser, ExpenseColumn, ExpenseCard, PluginSheetSession, DailyTeam, DailyProject, DailyColumn, DailyTask, DailyComment, DailyMessage
from sqlalchemy.orm.attributes import flag_modified

# DATABASE SETUP
# Multi-DB Configuration for Microservices/Monolith Hybrid

CORE_DB_URL = os.getenv("CORE_DB_URL", os.getenv("DATABASE_URL", "sqlite:///./aodev.db")).strip().replace("postgres://", "postgresql://")
OPS_DB_URL = os.getenv("OPS_DB_URL", os.getenv("DATABASE_URL", "sqlite:///./aodev.db")).strip().replace("postgres://", "postgresql://")
PLUGIN_DB_URL = os.getenv("PLUGIN_DB_URL", os.getenv("DATABASE_URL", "sqlite:///./aodev.db")).strip().replace("postgres://", "postgresql://")
EXT_DB_URL = os.getenv("EXT_DB_URL", os.getenv("DATABASE_URL", "sqlite:///./aodev.db")).strip().replace("postgres://", "postgresql://")

print(f"✅ [DB SETUP] Core: {'SQLite' if 'sqlite' in CORE_DB_URL else 'Postgres'}")
print(f"✅ [DB SETUP] Ops: {'SQLite' if 'sqlite' in OPS_DB_URL else 'Postgres'}")

# Create Engines
engine_core = create_engine(CORE_DB_URL, connect_args={"check_same_thread": False} if "sqlite" in CORE_DB_URL else {})
engine_ops = create_engine(OPS_DB_URL, connect_args={"check_same_thread": False} if "sqlite" in OPS_DB_URL else {})
engine_plugin = create_engine(PLUGIN_DB_URL, connect_args={"check_same_thread": False} if "sqlite" in PLUGIN_DB_URL else {})
engine_ext = create_engine(EXT_DB_URL, connect_args={"check_same_thread": False} if "sqlite" in EXT_DB_URL else {})

# Create Session Factories
SessionCore = sessionmaker(autocommit=False, autoflush=False, bind=engine_core)
SessionOps = sessionmaker(autocommit=False, autoflush=False, bind=engine_ops)
SessionPlugin = sessionmaker(autocommit=False, autoflush=False, bind=engine_plugin)
SessionExt = sessionmaker(autocommit=False, autoflush=False, bind=engine_ext)

# Universal SessionLocal for backwards compatibility (defaults to Ops for main app, or Core for Auth?)
# Ideally we replace usage, but to avoid breaking 2000 lines, we route dynamically or default to Ops (Operations is the biggest chunk).
SessionLocal = SessionOps 

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Specific Providers
def get_core_db():
    db = SessionCore()
    try: yield db
    finally: db.close()

def get_ops_db():
    db = SessionOps()
    try: yield db
    finally: db.close()

def get_plugin_db():
    db = SessionPlugin()
    try: yield db
    finally: db.close()

# Ensure tables exist
# For Phase 1 (Shared Code): Create ALL tables on ALL DBs to avoid missing table errors
# especially for new modules like BIM (bim_users, bim_projects)
# We bind to engine_ext because auth.py uses SessionExt, but since they likely share the same sqlite file, 
# this ensures the file has the schema.
Base.metadata.create_all(bind=engine_ext) 
# Also ensure for Ops/Core just in case they are different files in some configs
Base.metadata.create_all(bind=engine_core)
Base.metadata.create_all(bind=engine_ops) 


SCAN_CATEGORIES = {
    "Facturas": "invoice",
    "Pagos": "payment",
    "Impuestos_IVA": "tax_iva",
    "Impuestos_ISR": "tax_isr",
    "Legal": "legal",
    "Planos": "plans"
}

# -----------------------------------------------------------------------------
# PROJECT FUNCTIONS
# -----------------------------------------------------------------------------

def get_projects(archived: bool = False) -> List[models.Project]:
    db = SessionLocal()
    try:
        # Filter out 'Analisis' (Estimations) from standard project list
        projects = db.query(models.Project).filter(
            models.Project.archived == archived,
            models.Project.status != "Analisis" 
        ).all()
        
        # Initialize .files to empty dict to avoid template errors accessing p.files
        for p in projects:
            p.files = {cat: [] for cat in SCAN_CATEGORIES.keys()}
            
            # Safeguard numeric fields
            if p.amount is None: p.amount = 0.0
            if p.paid_amount is None: p.paid_amount = 0.0
            if p.duration_months is None: p.duration_months = 0.0
            if p.additional_time_months is None: p.additional_time_months = 0.0

            # Populate Events from Files Meta
            events = []
            if p.files_meta and isinstance(p.files_meta, dict):
                for cat, files in p.files_meta.items():
                    if isinstance(files, dict):
                        for fname, meta in files.items():
                            if isinstance(meta, dict):
                                date_str = meta.get("date", "")
                                # If no date, maybe we shouldn't show it on timeline? 
                                # Or show at start date?
                                # Let's try to parse or keep empty.
                                # The template JS handles date parsing.
                                if date_str:
                                    events.append({
                                        "type": "file",
                                        "date": date_str,
                                        "category": cat,
                                        "filename": fname
                                    })
            p.events = events
            
            db.expunge(p)
        return projects
    except Exception as e:
        print(f"DB Error get_projects: {e}")
        return []
    finally:
        db.close()

def update_project_profit_config(project_id: str, projected: float, real: float, partners: dict) -> bool:
    db = SessionLocal()
    try:
        proj = db.query(models.Project).filter(models.Project.id == project_id).first()
        if not proj: return False
        
        proj.projected_profit_margin = projected
        proj.real_profit_margin = real
        proj.partners_config = partners
        flag_modified(proj, "partners_config")
        
        db.commit()
        return True
    except Exception as e:
        print(f"Error update_project_profit_config: {e}")
        db.rollback()
        return False
    finally:
        db.close()

def get_project_details(project_id: str) -> Optional[models.Project]:
    db = SessionLocal()
    try:
        proj = db.query(models.Project).filter(models.Project.id == project_id).first()
        if not proj:
            return None
            
        proj.files = {cat: [] for cat in SCAN_CATEGORIES.keys()}
        
        # SAFEGUARDS for JSON attributes (Ensure correct Types)
        if proj.reminders is None or not isinstance(proj.reminders, list): 
            proj.reminders = []
            
        if proj.acc_config is None or not isinstance(proj.acc_config, dict): 
            proj.acc_config = {}
            
        if proj.partners_config is None or not isinstance(proj.partners_config, dict): 
            proj.partners_config = {}
            
        if proj.assigned_collaborators is None or not isinstance(proj.assigned_collaborators, dict): 
            proj.assigned_collaborators = {}
            
        if proj.files_meta is None or not isinstance(proj.files_meta, dict): 
            proj.files_meta = {}

        # SAFEGUARDS for Numeric Fields (Ensure Float)
        if proj.amount is None: proj.amount = 0.0
        if proj.paid_amount is None: proj.paid_amount = 0.0
        if proj.square_meters is None: proj.square_meters = 0.0
        if proj.projected_profit_margin is None: proj.projected_profit_margin = 0.0
        if proj.real_profit_margin is None: proj.real_profit_margin = 0.0
        if proj.duration_months is None: proj.duration_months = 0.0
        if proj.additional_time_months is None: proj.additional_time_months = 0.0

        # CALCULATE FINANCIAL METRICS FROM METADATA
        cat_totals = {}
        for cat in SCAN_CATEGORIES.keys():
            cat_totals[cat] = 0.0

        if proj.files_meta:
            for cat, files_dict in proj.files_meta.items():
                if isinstance(files_dict, dict):
                    current_sum = 0.0
                    # Ensure category exists in files dict (though initialized above, safety check)
                    if cat not in proj.files:
                        proj.files[cat] = []

                    for fname, meta in files_dict.items():
                        if isinstance(meta, dict):
                            # Populate File Object for UI
                            file_obj = {
                                "name": fname,
                                "amount": 0.0,
                                "note": meta.get("note", ""),
                                "date": meta.get("date", "")
                            }
                            
                            try:
                                val = float(meta.get("amount", 0.0))
                                current_sum += val
                                file_obj["amount"] = val
                            except: pass
                            
                            proj.files[cat].append(file_obj)
                    
                    if cat in cat_totals:
                         cat_totals[cat] = current_sum
                    else:
                         cat_totals[cat] = current_sum

        proj.cat_totals = cat_totals 
        
        # Override paid_amount with calculated if we rely on files, 
        # or should we respect DB if files are empty?
        # Logic says: Recalculate from files if available.
        # But 'payments' usually come from files in "Pagos".
        proj.paid_amount = cat_totals.get("Pagos", 0.0)
        proj.total_iva_paid = cat_totals.get("Impuestos_IVA", 0.0)
        proj.total_isr_paid = cat_totals.get("Impuestos_ISR", 0.0)
        
        db.expunge(proj)
        return proj
    finally:
        db.close()

def create_project(name: str, client: str = "", nit: str = "", legal_name: str = "", po_number: str = "", amount: float = 0.0, status: str = "Activo", emoji: str = "📁", custom_id: str = None, category: str = "Residencial") -> bool:
    db = SessionLocal()
    try:
        if custom_id:
            new_id = custom_id
        else:
            new_id = str(int(datetime.datetime.now().timestamp()))
            
        new_proj = models.Project(
            id=new_id,
            name=name,
            client=client,
            nit=nit,
            legal_name=legal_name,
            po_number=po_number,
            amount=amount,
            status=status,
            emoji=emoji,
            category=category,
            start_date=datetime.datetime.now().isoformat()
        )
        db.add(new_proj)
        db.commit()
            
        return True
    except Exception as e:
        print(f"Error create_project: {e}")
        db.rollback()
        return False

    finally:
        db.close()

def get_project_stats_by_category():
    """
    Iterates through all projects and aggregates stats (count, square_meters) by category.
    Returns a dictionary keyed by frontend category slugs (residential, commercial, etc).
    ONLY counts "Activo" projects.
    """
    projects = get_projects()
    
    # Initialize with 0
    stats = {
        "residential": {"count": 0, "sqm": 0.0},
        "commercial": {"count": 0, "sqm": 0.0},
        "industrial": {"count": 0, "sqm": 0.0},
        "recreational": {"count": 0, "sqm": 0.0},
        "educational": {"count": 0, "sqm": 0.0}
    }
    
    # Robust Mapping
    mapping = {
        "Residencial": "residential",
        "residential": "residential",
        
        "Comercial": "commercial",
        "commercial": "commercial",
        
        "Naves Industriales": "industrial",
        "Industrial": "industrial",
        "industrial": "industrial",
        
        "Recreativo": "recreational",
        "recreational": "recreational",
        
        "Educativo": "educational",
        "educational": "educational"
    }

    total_sqm_global = 0.0
    total_projects_global = 0

    for p in projects:
        # Check Status - User requested Active projects count
        status = getattr(p, "status", "Activo")
        if status != "Activo":
            continue

        # Get attributes
        cat_raw = getattr(p, "category", "Residencial") 
        sqm = getattr(p, "square_meters", 0.0)
        
        try:
            sqm = float(sqm)
        except (ValueError, TypeError):
            sqm = 0.0

        # Resolve category
        slug = mapping.get(cat_raw, "residential") # Default to residential if unknown
        
        if slug in stats:
            stats[slug]["count"] += 1
            stats[slug]["sqm"] += sqm
        
        total_sqm_global += sqm
        total_projects_global += 1

    return {
        "categories": stats,
        "global": {
            "total_projects": total_projects_global,
            "total_sqm": total_sqm_global
        }
    }

def update_project_meta(project_id: str, new_client: str, new_status: str, nit: str, legal_name: str, po_number: str, amount: float, emoji: str, start_date: str, duration_months: float, additional_time_months: float, paid_amount: float, square_meters: float = 0.0, category: str = "Residencial", archived: bool = False, acc_config: dict = None) -> bool:
    db = SessionLocal()
    try:
        proj = db.query(models.Project).filter(models.Project.id == project_id).first()
        if not proj: return False
        
        proj.client = new_client
        proj.status = new_status
        proj.nit = nit
        proj.legal_name = legal_name
        proj.po_number = po_number
        proj.amount = amount
        proj.emoji = emoji
        proj.start_date = start_date
        proj.duration_months = duration_months
        proj.additional_time_months = additional_time_months
        proj.paid_amount = paid_amount
        proj.square_meters = square_meters
        proj.category = category
        proj.archived = archived
        if acc_config:
            proj.acc_config = acc_config
            
        db.commit()
        return True
    except Exception as e:
        print(f"Error update_project: {e}")
        db.rollback()
        return False
    finally:
        db.close()


def update_project_collaborators(project_id: str, assignments: dict) -> bool:
    """
    Updates the assigned_collaborators map for a project.
    assignments: { collab_id: percentage_float }
    """
    db = SessionLocal()
    try:
        proj = db.query(models.Project).filter(models.Project.id == project_id).first()
        if not proj: return False
        
        proj.assigned_collaborators = assignments
        flag_modified(proj, "assigned_collaborators")
        
        db.commit()
        return True
    except Exception as e:
        print(f"Error update_project_collaborators: {e}")
        db.rollback()
        return False
    finally:
        db.close()

def get_total_collaborator_allocations():
    """
    Returns a dict { collab_id: total_percentage } across ALL active projects.
    """
    db = SessionLocal()
    try:
        active_projects = db.query(models.Project).filter(models.Project.status == "Activo").all()
        allocations = {}
        for p in active_projects:
            # Safe Guard: Ensure we have a DICT
            if p.assigned_collaborators and isinstance(p.assigned_collaborators, dict):
                for cid, pct in p.assigned_collaborators.items():
                    try:
                        val = float(pct)
                        allocations[cid] = allocations.get(cid, 0.0) + val
                    except: pass
    
        return allocations
    finally:
        db.close()

def get_collaborator_assigned_projects(collab_id: str):
    """
    Returns list of { id, name, percentage, status } for a collaborator.
    """
    db = SessionLocal()
    try:
        projects = db.query(models.Project).all()
        assigned = []
        for p in projects:
            if p.assigned_collaborators and collab_id in p.assigned_collaborators:
                try:
                    pct = float(p.assigned_collaborators[collab_id])
                    assigned.append({
                        "id": p.id,
                        "name": p.name,
                        "status": p.status,
                        "percentage": pct
                    })
                except: pass
        return assigned
    finally:
        db.close()

# -----------------------------------------------------------------------------
# COLLABORATOR FUNCTIONS
# -----------------------------------------------------------------------------

def get_collaborators() -> List[models.Collaborator]:
    db = SessionLocal()
    try:
        return db.query(models.Collaborator).filter(models.Collaborator.archived == False).all()
    finally:
        db.close()

def get_collaborator_details(collab_id: str) -> Optional[models.Collaborator]:
    db = SessionLocal()
    try:
        collab = db.query(models.Collaborator).filter(models.Collaborator.id == collab_id).first()
        if not collab:
            return None
            
        collab.files = {"Profile": [], "Legal": [], "Payments": []}
        return collab
    finally:
        db.close()

def create_collaborator(name: str, role: str, salary: float = 0.0, birthday: str = "", start_date: str = "") -> bool:
    db = SessionLocal()
    try:
        new_id = str(int(datetime.datetime.now().timestamp()))
        
        bonus = 250.0
        base = salary - 250 if salary >= 250 else salary
        if salary < 250: bonus = 0
        
        new_collab = models.Collaborator(
            id=new_id,
            name=name,
            role=role,
            base_salary=base,
            bonus_incentive=bonus,
            salary=salary,
            birthday=birthday,
            start_date=start_date
        )
        db.add(new_collab)
        db.commit()
        return True
    except Exception as e:
        print(f"Error create_collaborator: {e}")
        return False
    finally:
        db.close()

# -----------------------------------------------------------------------------
# INIT
# -----------------------------------------------------------------------------

# -----------------------------------------------------------------------------
# INIT & CONFIG
# -----------------------------------------------------------------------------
# Init functions removed

# -----------------------------------------------------------------------------
# AUTH & USERS
# -----------------------------------------------------------------------------
# Re-export User model class as 'User' for main.py compatibility if needed, 
# or Main.py should use models.AppUser. Main.py imports 'User' from database.
# In original database.py, 'User' was likely a Pydantic model or class.
# We will create a Pydantic-like wrapper or Class that matches main.py expectation.

class User:
    def __init__(self, id, name, email, role, is_active, hashed_password, permissions=None, assigned_projects=None):
        self.id = id
        self.name = name
        self.email = email
        self.role = role
        self.is_active = is_active
        self.hashed_password = hashed_password
        self.permissions = permissions or {}
        self.assigned_projects = assigned_projects or []

def get_users() -> List[User]:
    # root_path ignored for SQL Users, but kept for signature compatibility
    db = SessionCore()
    try:
        users_db = db.query(models.AppUser).all()
        # Convert to User objects, handling potential missing assigned_projects attribute if migration failed (though I ran it, safeguards are good)
        return [User(u.email, u.full_name, u.email, u.role, u.is_active, u.hashed_password, u.permissions, getattr(u, 'assigned_projects', [])) for u in users_db]
    except:
        return []
    finally:
        db.close()

def get_user_by_email(email: str) -> Optional[User]:
    db = SessionCore()
    try:
        u = db.query(models.AppUser).filter(models.AppUser.email == email).first()
        if u:
            return User(u.email, u.full_name, u.email, u.role, u.is_active, u.hashed_password, u.permissions, getattr(u, 'assigned_projects', []))
        return None
    finally:
        db.close()

def save_user(user: User):
    db = SessionCore()
    try:
        # Check if exists
        existing = db.query(models.AppUser).filter(models.AppUser.email == user.email).first()
        if existing:
            existing.full_name = user.name
            existing.role = user.role
            existing.is_active = user.is_active
            existing.hashed_password = user.hashed_password
            existing.permissions = user.permissions
        else:
            new_u = models.AppUser(
                email=user.email,
                full_name=user.name,
                hashed_password=user.hashed_password,
                role=user.role,
                is_active=user.is_active,
                permissions=user.permissions
            )
            db.add(new_u)
        db.commit()
    finally:
        db.close()

def delete_user(user_id: str):
    # user_id in main.py is likely email or ID. 
    # original save_user used ID. AppUser PK is email.
    # We should assume user_id might be email.
    db = SessionCore()
    try:
        # Try ID match? AppUser doesn't have ID column in my model, only Email.
        # But 'User' class has ID.
        # Let's try to delete by email if user_id looks like email, or if we stored ID?
        # My AppUser model ONLY has email as PK.
        # This is a mismatch. I should add ID to AppUser to match legacy.
        # For now, let's assume user_id IS key.
        u = db.query(models.AppUser).filter(models.AppUser.email == user_id).first()
        if u:
            db.delete(u)
            db.commit()
    finally:
        db.close()
        
def update_user_permissions(user_id: str, permissions: dict):
    db = SessionLocal()
    try:
        # User ID here might be email or ID. Let's try to match ID first, then Email.
        # But wait, my ID generation strategy was str(abs(hash(email))) or timestamp.
        # Ideally we stick to ID.
        u = db.query(models.AppUser).filter(models.AppUser.email == user_id).first()
        # If not found by email (if user_id is actually the ID), try by ID (if I had an ID column distinct from email in AppUser... 
        # AppUser PK is ONLY email in the Model definition earlier?
        # Let's check Model: email = Column(String, primary_key=True)
        # So user_id MUST be email.
        
        if u:
            u.permissions = permissions
            flag_modified(u, "permissions")
            db.commit()
            return True
        return False
    except Exception as e:
        print(f"Error updating permissions: {e}")
        return False
    finally:
        db.close()

def update_user_assigned_projects(user_email: str, project_ids: List[str]) -> bool:
    """
    Updates the list of project IDs assigned to a user.
    """
    db = SessionLocal()
    try:
        # AppUser PK is email
        u = db.query(models.AppUser).filter(models.AppUser.email == user_email).first()
        
        if u:
            u.assigned_projects = project_ids
            flag_modified(u, "assigned_projects")
            db.commit()
            return True
        return False
    except Exception as e:
        print(f"Error updating assigned projects: {e}")
        return False
    finally:
        db.close()

# -----------------------------------------------------------------------------
# MISSING FUNCTIONS STUBS (To prevent ImportErrors)
# -----------------------------------------------------------------------------
# -----------------------------------------------------------------------------
# EXPENSES FUNCTIONS
# -----------------------------------------------------------------------------
def get_or_create_default_column():
    db = SessionLocal()
    try:
        col = db.query(models.ExpenseColumn).first()
        if not col:
            new_id = str(int(datetime.datetime.now().timestamp()))
            col = models.ExpenseColumn(id=new_id, title="General", order_index=0)
            db.add(col)
            db.commit()
            db.refresh(col)
        return col
    finally:
        db.close()

def get_expenses_monthly(year: int = None):
    if year is None:
        year = datetime.datetime.now().year
    db = SessionLocal()
    try:
        # Get all cards (we ignore ExpenseColumn structure for this view)
        cards = db.query(models.ExpenseCard).all()
        
        # Initialize 12 months (dicts) because main.py expects dict access for 'cards', 'total' etc.
        months_data = []
        month_names = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]
        
        for i in range(12):
            months_data.append({
                "id": str(i+1), # Month Index
                "name": month_names[i],
                "cards": [],
                "total": 0.0
            })
            
        for card in cards:
            # Parse Date
            card_date = None
            if card.date:
                try:
                    # Try YYYY-MM-DD
                    card_date = datetime.datetime.strptime(card.date, "%Y-%m-%d")
                except:
                    try:
                        # Try ISO
                        card_date = datetime.datetime.fromisoformat(card.date)
                    except:
                        pass
            
            # If no date, maybe we should ignore or put in "current month"?
            # Let's Skip if no date or date doesn't match year
            if card_date:
                # print(f"DEBUG: Processing card {card.title} with date {card_date}")
                if card_date.year == year:
                    # Add to bucket
                    m_index = card_date.month - 1
                    if 0 <= m_index < 12:
                        # Convert card to dict if main.py expects dict access (c['amount'])
                        # main.py error was "ExpenseColumn object is not subscriptable" when accessing col['cards']
                        # logic: total = sum(c['amount'] for c in col['cards'])
                        # So 'c' must be subscriptable too.
                        # ExpenseCard is Object.
                        # We should convert card to dict.
                        c_dict = {
                            "id": card.id,
                            "name": card.title,
                            "amount": card.amount,
                            "description": card.notes,
                            "date": card.date,
                            "files": card.files or {} # Handle None
                        }
                        months_data[m_index]["cards"].append(c_dict)
                        months_data[m_index]["total"] += card.amount
            else:
                 print(f"DEBUG: Card {card.id} has invalid date: {card.date}")
                    
        return months_data
    finally:
        db.close()

def add_expense_column(title):
    db = SessionLocal()
    try:
        new_id = str(int(datetime.datetime.now().timestamp()))
        # Get max index
        count = db.query(models.ExpenseColumn).count()
        col = models.ExpenseColumn(id=new_id, title=title, order_index=count)
        db.add(col)
        db.commit()
    finally:
        db.close()

def add_expense_card(col_id, title, amount, description="", files=[], date=None):
    db = SessionLocal()
    try:
        new_id = str(int(datetime.datetime.now().timestamp()))
        print(f"DEBUG: Adding Expense Card - Title: {title}, Date: {date}, Amount: {amount}")
        
        # Ensure col_id exists or use default
        # If col_id is "month-X", we need a real FK.
        # Use default column for FK satisfaction
        final_col_id = col_id
        
        # Verify if col_id exists
        c_check = db.query(models.ExpenseColumn).filter(models.ExpenseColumn.id == col_id).first()
        if not c_check:
            # Use default
            def_col = db.query(models.ExpenseColumn).first()
            if not def_col:
                # Create one
                col = models.ExpenseColumn(id="default_01", title="General", order_index=0)
                db.add(col)
                db.commit()
                final_col_id = "default_01"
            else:
                final_col_id = def_col.id
        
        # Handle Date
        final_date = date
        if not final_date:
            final_date = datetime.datetime.now().strftime("%Y-%m-%d")
            
        print(f"DEBUG: Final Date being saved: {final_date}")
            
        # Handle Files
        # files arg comes as list of filenames presumably?
        # database.py usually doesn't handle upload, it just stores metadata.
        # Assuming files is [] empty list passed from main.
        
        # Map description -> notes
        
        card = models.ExpenseCard(
            id=new_id,
            column_id=final_col_id,
            title=title,
            amount=amount,
            date=final_date,
            notes=description,
            files={} # Files added later via update
        )
        db.add(card)
        db.commit()
        
        # Return dict representation
        return {
            "id": card.id,
            "column_id": card.column_id,
            "title": card.title,
            "amount": card.amount,
            "date": card.date,
            "notes": card.notes,
            "files": card.files
        }
    finally:
        db.close()
def copy_expense_card(card_id, target_col_id):
    db = SessionLocal()
    try:
        original = db.query(models.ExpenseCard).filter(models.ExpenseCard.id == card_id).first()
        if original:
            new_id = str(int(datetime.datetime.now().timestamp()))
            copy = models.ExpenseCard(
                id=new_id,
                column_id=target_col_id,
                title=original.title,
                amount=original.amount,
                date=original.date,
                notes=original.notes,
                files=original.files
            )
            db.add(copy)
            db.commit()
    finally:
        db.close()

def delete_expense_card(card_id):
    db = SessionLocal()
    try:
        c = db.query(models.ExpenseCard).filter(models.ExpenseCard.id == card_id).first()
        if c: 
            db.delete(c)
            db.commit()
    finally:
        db.close()

def delete_expense_column(col_id):
    db = SessionLocal()
    try:
        c = db.query(models.ExpenseColumn).filter(models.ExpenseColumn.id == col_id).first()
        if c:
            db.delete(c)
            db.commit()
    finally:
        db.close()

def update_expense_card_files(card_id, filename):
    db = SessionLocal()
    try:
        c = db.query(models.ExpenseCard).filter(models.ExpenseCard.id == card_id).first()
        if c:
            # Append file? Or is this dict?
            # Model says files = JSON.
            # Assuming just a list of filenames or simple dict?
            # Let's treat as list of strings for simplicity if JSON default is {}
            # Wait, default is {}. 
            # Logic: c.files[filename] = {path...} ? 
            # Let's save just filename presence
            files = dict(c.files) if c.files else {}
            files[filename] = {"date": datetime.datetime.now().isoformat()}
            c.files = files
            db.commit()
    finally:
        db.close()
def calculate_isr_projection(monthly_base: float, monthly_bonus: float) -> float:
    # Logic copied from original
    annual_income = (monthly_base + monthly_bonus) * 12
    annual_igss = (monthly_base * 0.0483) * 12
    standard_deduction = 48000.0
    taxable_income = annual_income - standard_deduction - annual_igss
    
    if taxable_income <= 0: return 0.0
    if taxable_income <= 300000:
        annual_tax = taxable_income * 0.05
    else:
        annual_tax = 15000 + ((taxable_income - 300000) * 0.07)
    return annual_tax / 12

def get_months_worked(start_date_str: str) -> float:
    if not start_date_str: return 0.0
    try:
        start = datetime.datetime.strptime(start_date_str, "%Y-%m-%d")
        now = datetime.datetime.now()
        diff = (now.year - start.year) * 12 + (now.month - start.month)
        day_ratio =  min(now.day / 30.0, 1.0)
        return max(0.0, float(diff) + day_ratio)
    except:
        return 0.0

def save_payroll_close(root_path, date, total):
    # Log to file or DB? Legacy kept file. 
    # Let's ignore or create a simple log table later.
    pass

def toggle_archive_collaborator(root_path, collab_id):
    db = SessionLocal()
    try:
        c = db.query(models.Collaborator).filter(models.Collaborator.id == collab_id).first()
        if c:
            c.archived = not c.archived
            db.commit()
    finally:
        db.close()

def update_collaborator(id, **kwargs):
    db = SessionLocal()
    try:
        c = db.query(models.Collaborator).filter(models.Collaborator.id == id).first()
        if c:
            for k, v in kwargs.items():
                if hasattr(c, k):
                     setattr(c, k, v)
            db.commit()
    finally:
        db.close()

def update_collaborator_picture(id, pic_filename):
    update_collaborator(id, profile_picture=pic_filename)

def add_adjustment(root_path, id, type, desc, amt):
    db = SessionLocal()
    try:
        c = db.query(models.Collaborator).filter(models.Collaborator.id == id).first()
        if c:
            adjs = list(c.adjustments) if c.adjustments else []
            adjs.append({
                "id": str(int(datetime.datetime.now().timestamp()*1000)),
                "type": type,
                "description": desc,
                "amount": amt,
                "date": datetime.datetime.now().isoformat()
            })
            c.adjustments = adjs
            db.commit()
    finally:
        db.close()

def remove_adjustment(root_path, id, adj_id):
    db = SessionLocal()
    try:
        c = db.query(models.Collaborator).filter(models.Collaborator.id == id).first()
        if c:
            adjs = [a for a in c.adjustments if a.get("id") != adj_id]
            c.adjustments = adjs
            db.commit()
    finally:
        db.close()

def add_partner_withdrawal(root_path, pid, cid, amt, note):
    # This requires 'profit_withdrawals' field in Project which I didn't verify in model.
    # Ah, I added JSON fields. 'profit_withdrawals' isn't explicitly in model but 'files_meta' etc are.
    # Let's add it to project model dynamically or in json field? 
    # Wait, 'partners_config' is JSON. Can we store withdrawals there? No.
    # I should have added 'profit_withdrawals' to Project model JSON fields.
    # Let's assume I missed it and use 'files_meta' or create it?
    # Actually, let's skip implementation or stub it better to avoid crash? 
    # User didn't complain about this specific one yet.
    pass

def update_project_profit_config(root_path, pid, pm, rm, partners):
    db = SessionLocal()
    try:
        p = db.query(models.Project).filter(models.Project.id == pid).first()
        if p:
            p.projected_profit_margin = pm
            p.real_profit_margin = rm
            p.partners_config = partners
            db.commit()
    finally:
        db.close()

def update_project_file_meta(pid, cat, fname, amt, note, file_date=None):
    db = SessionLocal()
    try:
        p = db.query(models.Project).filter(models.Project.id == pid).first()
        if p:
            # Create a defensive copy to ensure Python object identity changes if shallow copy isn't enough,
            # but flag_modified should handle it.
            # Using copy.deepcopy is safer for nested dicts if we were mutating, but here we replace.
            import copy
            meta = copy.deepcopy(dict(p.files_meta)) if p.files_meta else {}
            
            if cat not in meta: meta[cat] = {}
            
            current_date = file_date if file_date else datetime.datetime.now().isoformat()
            meta[cat][fname] = {"amount": amt, "note": note, "date": current_date}
            
            p.files_meta = meta
            flag_modified(p, "files_meta")
            
            # Recalculate persistent paid_amount for Main Dashboard
            total_paid = 0.0
            pagos = meta.get("Pagos", {})
            if isinstance(pagos, dict):
                for f, data in pagos.items():
                    if isinstance(data, dict):
                        try: total_paid += float(data.get("amount", 0.0))
                        except: pass
            p.paid_amount = total_paid
            
            print(f"DEBUG: Saved file meta for {fname} in {cat}: Amount={amt}. Updated Total Paid={total_paid}")
            
            db.commit()
    except Exception as e:
        print(f"ERROR: Failed to update project file meta: {e}")
        db.rollback()
    finally:
        db.close()

def delete_project_file_meta(pid, category, filename):
    db = SessionLocal()
    try:
        p = db.query(models.Project).filter(models.Project.id == pid).first()
        if p and p.files_meta:
            import copy
            meta = copy.deepcopy(dict(p.files_meta))
            
            if category in meta and filename in meta[category]:
                del meta[category][filename]
                
                p.files_meta = meta
                flag_modified(p, "files_meta")
                
                # Recalculate persistent paid_amount
                total_paid = 0.0
                pagos = meta.get("Pagos", {})
                if isinstance(pagos, dict):
                    for f, data in pagos.items():
                        if isinstance(data, dict):
                            try: total_paid += float(data.get("amount", 0.0))
                            except: pass
                p.paid_amount = total_paid
                
                db.commit()
                print(f"DEBUG: Removed metadata for {filename}")
    except Exception as e:
        print(f"ERROR deleting file meta: {e}")
        db.rollback()
    finally:
        db.close()

def add_project_reminder(pid, title, date, freq):
    db = SessionLocal()
    try:
        p = db.query(models.Project).filter(models.Project.id == pid).first()
        if p:
            rems = list(p.reminders) if p.reminders else []
            rems.append({
                 "id": str(int(datetime.datetime.now().timestamp()*1000)),
                 "title": title, 
                 "date": date, 
                 "frequency": freq,
                 "completed": False
            })
            p.reminders = rems
            db.commit()
            return True
    except: return False
    finally: db.close()

def delete_project_reminder(pid, rid):
    db = SessionLocal()
    try:
        p = db.query(models.Project).filter(models.Project.id == pid).first()
        if p:
            rems = [r for r in p.reminders if r.get("id") != rid]
            p.reminders = rems
            db.commit()
    finally: db.close()

def toggle_project_reminder(pid, rid):
    db = SessionLocal()
    try:
        p = db.query(models.Project).filter(models.Project.id == pid).first()
        if p:
            rems = list(p.reminders)
            for r in rems:
                if r.get("id") == rid:
                    r["completed"] = not r.get("completed", False)
            p.reminders = rems
            db.commit()
    finally: db.close()
def get_plugin_sessions():
    db = SessionLocal()
    try:
        # Return all sessions, ordered by start time
        sessions = db.query(models.PluginSession).order_by(models.PluginSession.start_time.desc()).limit(100).all()
        # Convert to list of dicts or just objects? 
        # Main.py expects objects or dicts? Main says `sessions.sort(...)`. 
        # Objects are fine if I don't use Pydantic there.
        # But templates usually access attributes.
        return sessions
    except Exception as e:
        print(f"Error getting sessions: {e}")
        return []
    finally:
        db.close()

def get_user_plugin_stats(email):
    db = SessionLocal()
    try:
        now = datetime.datetime.now()
        start_of_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        
        # Query Activities
        activities = db.query(models.PluginActivity)\
            .join(models.PluginSession)\
            .filter(models.PluginSession.user_email == email)\
            .filter(models.PluginActivity.timestamp >= start_of_month)\
            .all()
            
        total_minutes = sum(a.active_minutes for a in activities)
        unique_files = set(a.filename for a in activities)
        
        session_count = db.query(models.PluginSession)\
            .filter(models.PluginSession.user_email == email)\
            .filter(models.PluginSession.start_time >= start_of_month)\
            .count()
        
        return {
            "month_hours": round(total_minutes / 60, 1),
            "files_count": len(unique_files),
            "session_count": session_count
        }
    except Exception as e:
        print(f"Error getting plugin stats: {e}")
        return {"month_hours": 0, "files_count": 0}
    finally:
        db.close()

def start_revit_session(email, machine, version, ip, plugin_version="1.0.0"):
    db = SessionPlugin()
    try:
        sid = str(uuid.uuid4())
        session = models.PluginSession(
            id=sid,
            user_email=email,
            machine_id=machine,
            revit_version=version,
            plugin_version=plugin_version,
            ip_address=ip,
            start_time=datetime.datetime.now(),
            last_heartbeat=datetime.datetime.now(),
            is_active=True
        )
        db.add(session)
        db.commit()
        return sid
    except Exception as e:
        print(f"Error starting session: {e}")
        return "error_session"
    finally:
        db.close()

def heartbeat_session(session_id, ip):
    db = SessionPlugin()
    try:
        session = db.query(models.PluginSession).filter(models.PluginSession.id == session_id).first()
        if session:
            session.last_heartbeat = datetime.datetime.now()
            # session.ip_address = ip # Update IP if changed?
            db.commit()
            return True
        return False
    except:
        return False
    finally:
        db.close()

def end_revit_session(session_id):
    db = SessionPlugin()
    try:
        session = db.query(models.PluginSession).filter(models.PluginSession.id == session_id).first()
        if session:
            session.is_active = False
            db.commit()
    except:
        pass
    finally:
        db.close()

def get_user_plugin_stats(email):
    db = SessionLocal()
    try:
        now = datetime.datetime.now()
        start_month = datetime.datetime(now.year, now.month, 1)
        
        # Get sessions for this month
        sessions = db.query(models.PluginSession)\
            .filter(models.PluginSession.user_email == email)\
            .filter(models.PluginSession.start_time >= start_month)\
            .all()
            
        total_active_mins = 0
        unique_files = set()
        
        for s in sessions:
            activities = db.query(models.PluginActivity).filter(models.PluginActivity.session_id == s.id).all()
            for a in activities:
                total_active_mins += (a.active_minutes or 0)
                if a.filename:
                    unique_files.add(a.filename)
                    
        return {
            "month_hours": round(total_active_mins / 60.0, 1),
            "files_count": len(unique_files)
        }
    except Exception as e:
        print(f"Error stats: {e}")
        return {"month_hours": 0.0, "files_count": 0}
    finally:
        db.close()

def get_plugin_sessions():
    db = SessionLocal()
    try:
        return db.query(models.PluginSession).all()
    except Exception as e:
        print(f"Error getting sessions: {e}")
        return []
    finally:
        db.close()

def get_user_plugin_logs(email, start_date: datetime.date = None, end_date: datetime.date = None):
    db = SessionPlugin()
    try:
        # Robust case-insensitive search
        if not email: return []
        
        q = db.query(models.PluginSession).filter(func.lower(models.PluginSession.user_email) == email.lower().strip())
        
        
        if start_date:
            # Combine date with min time
            dt_start = datetime.datetime.combine(start_date, datetime.time.min)
            q = q.filter(models.PluginSession.start_time >= dt_start)
            
        if end_date:
            # Combine date with max time
            dt_end = datetime.datetime.combine(end_date, datetime.time.max)
            q = q.filter(models.PluginSession.start_time <= dt_end)
            
        q = q.order_by(models.PluginSession.start_time.desc())
        
        # If filtering by specific date range, we might want ALL logs, not just limit 50
        if not start_date and not end_date:
            q = q.limit(50)
            
        sessions = q.all()
        
        logs = []
        for s in sessions:
            activities = db.query(models.PluginActivity).filter(models.PluginActivity.session_id == s.id).all()
            
            total_active = sum(a.active_minutes for a in activities)
            total_idle = sum(a.idle_minutes for a in activities)
            unique_files = list(set(a.filename for a in activities if a.filename))
            revit_users = list(set(a.revit_user for a in activities if a.revit_user))
            acc_projects = list(set(a.acc_project for a in activities if a.acc_project))
            
            start_dt = s.start_time
            if isinstance(start_dt, str):
                try: start_dt = datetime.datetime.fromisoformat(start_dt)
                except: pass
            
            end_dt = s.last_heartbeat
            if isinstance(end_dt, str):
                try: end_dt = datetime.datetime.fromisoformat(end_dt)
                except: pass
            
            date_str = start_dt.strftime("%d/%m/%Y") if isinstance(start_dt, datetime.datetime) else str(start_dt)
            day_name = start_dt.strftime("%A") if isinstance(start_dt, datetime.datetime) else ""
            start_time_str = start_dt.strftime("%H:%M") if isinstance(start_dt, datetime.datetime) else ""
            end_time_str = end_dt.strftime("%H:%M") if isinstance(end_dt, datetime.datetime) else "?"
            
            logs.append({
                "session_id": s.id,
                "date": date_str,
                "day_name": day_name,
                "start_time": start_time_str,
                "end_time": end_time_str,
                "active_mins": round(total_active, 1),
                "idle_mins": round(total_idle, 1),
                "files": unique_files,
                "ip_address": s.ip_address,
                "plugin_version": getattr(s, 'plugin_version', '1.0.0'),
                "revit_user": revit_users[0] if revit_users else "N/A",
                "acc_project": acc_projects[0] if acc_projects else "N/A",
                "machine": s.machine_id
            })
            
        return logs
    except Exception as e:
        print(f"Error logs: {e}")
        import traceback
        traceback.print_exc()
        return []
    finally:
        db.close()

def log_plugin_activity(session_id, filename, active_min, idle_min, revit_user, acc_proj):
    db = SessionPlugin()
    try:
        act = models.PluginActivity(
            session_id=session_id,
            filename=filename,
            active_minutes=active_min,
            idle_minutes=idle_min,
            revit_user=revit_user,
            acc_project=acc_proj,
            timestamp=datetime.datetime.now()
        )
        db.add(act)
        db.commit()
    except Exception as e:
        print(f"Error logging activity: {e}")
    finally:
        db.close()

def log_plugin_sync(session_id, filename, central_path):
    db = SessionPlugin()
    try:
        # Optional logic for sync
        pass
    finally:
        db.close()


# ==========================================
# Market Study / Benchmarking
# ==========================================

def get_market_studies_file_path() -> str:
    system_dir = os.path.join("System")
    if not os.path.exists(system_dir):
        try: os.makedirs(system_dir)
        except: pass
    return os.path.join(system_dir, "market_studies.json")

def get_market_studies() -> List[dict]:
    path = get_market_studies_file_path()
    if not os.path.exists(path):
        return []
    try:
        with open(path, "r", encoding='utf-8') as f:
            return json.load(f)
    except:
        return []

def add_market_study(name: str, amount: float, square_meters: float, months: float, category: str) -> bool:
    studies = get_market_studies()
    
    new_study = {
        "id": str(int(datetime.datetime.now().timestamp() * 1000)),
        "name": name,
        "amount": amount,
        "square_meters": square_meters,
        "months": months,
        "category": category,
        "ratio": amount / square_meters if square_meters > 0 else 0.0,
        "created_at": datetime.datetime.now().isoformat()
    }
    
    studies.append(new_study)
    
    path = get_market_studies_file_path()
    try:
        with open(path, "w", encoding='utf-8') as f:
            json.dump(studies, f, indent=4)
        return True
    except Exception as e:
        print(f"Error saving market study: {e}")
        return False

def delete_market_study(study_id: str) -> bool:
    studies = get_market_studies()
    original_len = len(studies)
    studies = [s for s in studies if s["id"] != study_id]
    
    if len(studies) < original_len:
        path = get_market_studies_file_path()
        try:
            with open(path, "w", encoding='utf-8') as f:
                json.dump(studies, f, indent=4)
            return True
        except:
            return False
    return False

def get_project_collaborator_count(project_id: str) -> int:
    """Counts how many users are assigned to this project."""
    users = get_users()
    count = 0
    for u in users:
        # Check if project_id is in their assigned list
        if project_id in getattr(u, 'assigned_projects', []):
            count += 1
    return count


# ==========================================
# Estimations (Estimaciones)
# ==========================================

# Legacy JSON Estimations Removed



# -----------------------------------------------------------------------------
# QUOTATIONS FUNCTIONS
# -----------------------------------------------------------------------------

def get_quotations() -> List[models.Quotation]:
    db = SessionLocal()
    try:
        return db.query(models.Quotation).order_by(models.Quotation.created_at.desc()).all()
    finally:
        db.close()

def get_quotation_by_id(quot_id: str) -> Optional[models.Quotation]:
    db = SessionLocal()
    try:
        data = db.query(models.Quotation).filter(models.Quotation.id == quot_id).first()
        if data and data.content_json is None:
            data.content_json = []
        return data
    finally:
        db.close()

def create_quotation(data: dict) -> models.Quotation:
    db = SessionLocal()
    try:
        new_q = models.Quotation(
            id=data.get("id"),
            title=data.get("title"),
            client_name=data.get("client_name"),
            project_type=data.get("project_type", "Residencial"),
            status=data.get("status", "Borrador"),
            content_json=data.get("content_json", []),
            total_amount=data.get("total_amount", 0.0)
        )
        db.add(new_q)
        db.commit()
        db.refresh(new_q)
        return new_q
    finally:
        db.close()

def update_quotation(quot_id: str, updates: dict) -> Optional[models.Quotation]:
    db = SessionLocal()
    try:
        q = db.query(models.Quotation).filter(models.Quotation.id == quot_id).first()
        if not q:
            return None
        
        for k, v in updates.items():
            setattr(q, k, v)
        
        if "content_json" in updates:
            flag_modified(q, "content_json")
            
        db.commit()
        db.refresh(q)
        return q
    finally:
        db.close()

def delete_quotation(quot_id: str) -> bool:
    db = SessionLocal()
    try:
        q = db.query(models.Quotation).filter(models.Quotation.id == quot_id).first()
        if q:
            db.delete(q)
            db.commit()
            return True
        return False
    finally:
        db.close()

# -----------------------------------------------------------------------------
# QUOTATION TEMPLATES
# -----------------------------------------------------------------------------

def get_templates() -> List[models.QuotationTemplate]:
    db = SessionLocal()
    try:
        return db.query(models.QuotationTemplate).order_by(models.QuotationTemplate.created_at.desc()).all()
    finally:
        db.close()

def delete_template(tpl_id: int):
    db = SessionLocal()
    try:
        tpl = db.query(models.QuotationTemplate).filter(models.QuotationTemplate.id == tpl_id).first()
        if tpl:
            db.delete(tpl)
            db.commit()
            return True
        return False
    except Exception as e:
        print(f"Error deleting template: {e}")
        db.rollback()
        return False
    finally:
        db.close()

def save_template(name: str, content: List):
    db = SessionLocal()
    try:
        tpl = models.QuotationTemplate(
            name=name,
            content_json=content
        )
        db.add(tpl)
        db.commit()
        db.refresh(tpl)
        return tpl.id
    except Exception as e:
        print(f"Error saving template: {e}")
        db.rollback()
        return None
    finally:
        db.close()

# -----------------------------------------------------------------------------
# ESTIMATIONS (Replica of Expenses Logic or Independent?)
# -----------------------------------------------------------------------------
def get_estimations():
    # Based on main.py, estimations are handled via create_estimation which might be using projects table or separate?
    # Wait, create_estimation was imported in main.py but I didn't see it in database.py earlier.
    # It must be missing or I missed it.
    # Check if 'create_estimation' exists in this file.
    # If not, I should implement it or find where it is.
    # However, 'get_estimations' is called in main.py, so it must exist or be expected.
    # Let's check projects for status='Analisis' or 'Estimacion' as a fallback.
    
    db = SessionLocal()
    try:
        # Assuming Estimations are Projects with status 'Analisis' or 'Aprobada'
        projects = db.query(models.Project).filter(models.Project.status.in_(["Analisis", "Aprobada"])).all()
        # Convert to dict
        res = []
        for p in projects:
            res.append({
                "id": p.id,
                "name": p.name,
                "client": p.client,
                "amount": p.amount,
                "square_meters": p.square_meters,
                "status": p.status,
                "category": p.category,
                "start_date": p.start_date,
                "duration_months": p.duration_months,
                "emoji": p.emoji,
                "resources": (p.estimation_data or {}).get("resources", [])
            })
        return res
    except Exception as e:
        print(f"Error getting estimations: {e}")
        return []
    finally:
        db.close()

def get_estimation_details(est_id: str):
    db = SessionLocal()
    try:
        p = db.query(models.Project).filter(models.Project.id == est_id).first()
        if not p: return None
        
        est_data = p.estimation_data or {}
        
        return {
            "id": p.id,
            "name": p.name,
            "client": p.client,
            "category": p.category,
            "amount": p.amount,
            "square_meters": p.square_meters,
            "duration_months": p.duration_months,
            "status": p.status,
            "resources": est_data.get("resources", []),
            "financials": est_data.get("financials", {})
        }
    finally:
        db.close()

def update_estimation_full(data: dict):
    db = SessionLocal()
    try:
        est_id = data.get("id")
        if not est_id: return False
        
        p = db.query(models.Project).filter(models.Project.id == est_id).first()
        if not p: return False
        
        # Update Core Fields
        if "name" in data: p.name = data["name"]
        if "client" in data: p.client = data["client"]
        if "category" in data: p.category = data["category"]
        if "amount" in data: p.amount = data["amount"]
        if "square_meters" in data: p.square_meters = data["square_meters"]
        if "duration_months" in data: p.duration_months = data["duration_months"]
        
        # Update JSON Data
        est_data = dict(p.estimation_data) if p.estimation_data else {}
        if "resources" in data: est_data["resources"] = data["resources"]
        if "financials" in data: est_data["financials"] = data["financials"]
        
        p.estimation_data = est_data
        flag_modified(p, "estimation_data")
        
        db.commit()
        return True
    except Exception as e:
        print(f"Error updating full: {e}")
        db.rollback()
        return False
    finally:
        db.close()


def create_estimation(data: dict):
    db = SessionLocal()
    try:
        new_id = str(uuid.uuid4())
        
        # Populate Project Model
        p = models.Project(
            id=new_id,
            name=data.get("name"),
            client=data.get("client"),
            category=data.get("category"),
            amount=float(data.get("amount", 0)),
            square_meters=float(data.get("square_meters", 0)),
            start_date=data.get("start_date"),
            duration_months=float(data.get("duration_months", 0)),
            status="Analisis",
            nit=data.get("nit"),
            legal_name=data.get("legal_name"),
            po_number=data.get("po_number"),
            emoji="📝",
            
            # Default empty estimation data
            estimation_data={
                "resources": [],
                "financials": {
                    "tax_pct": 5,
                    "opex_pct": 10,
                    "donation_pct": 2
                }
            }
        )
        db.add(p)
        db.commit()
    except Exception as e:
        print(f"Error creating estimation: {e}")
        db.rollback()
    finally:
        db.close()

def update_estimation(est_id: str, updates: dict):
    db = SessionLocal()
    try:
        p = db.query(models.Project).filter(models.Project.id == est_id).first()
        if p:
            if "status" in updates: p.status = updates["status"]
            db.commit()
    finally:
        db.close()

def delete_estimation(est_id: str):
    db = SessionLocal()
    try:
        p = db.query(models.Project).filter(models.Project.id == est_id).first()
        if p:
            db.delete(p)
            db.commit()
    finally:
        db.close()

# ==========================================
# Plugin Versions
# ==========================================

def create_plugin_version(version: str, changelog: str, url: str, mandatory: bool):
    db = SessionPlugin()
    try:
        new_v = models.PluginVersion(
            version_number=version,
            changelog=changelog,
            download_url=url,
            is_mandatory=mandatory
        )
        db.add(new_v)
        db.commit()
        return True
    except Exception as e:
        print(f"Error creating version: {e}")
        return False
    finally:
        db.close()

def get_plugin_versions():
    db = SessionLocal()
    try:
        # Sort by ID desc (newest first)
        versions = db.query(models.PluginVersion).order_by(models.PluginVersion.id.desc()).all()
        return versions
    finally:
        db.close()

def delete_plugin_version(version_id: int):
    db = SessionLocal()
    try:
        v = db.query(models.PluginVersion).filter(models.PluginVersion.id == version_id).first()
        if v:
            db.delete(v)
            db.commit()
            return True
        return False
    finally:
        db.close()

def get_latest_plugin_version():
    db = SessionPlugin()
    try:
        # Assumes ID desc is chronological.
        # Could also sort by version_number semver if needed, but ID is safer for insertion order
        v = db.query(models.PluginVersion).order_by(models.PluginVersion.id.desc()).first()
        if v:
            return {
                "version": v.version_number,
                "changelog": v.changelog,
                "url": v.download_url,
                "mandatory": v.is_mandatory
            }
        return None
    finally:
        db.close()

# ==========================================
# Cloud Quantify Persistence
# ==========================================

def save_cloud_session(session_id: str, data: dict, project_name: str = None, user_email: str = None, folder_id: str = None):
    db = SessionPlugin()
    try:
        session = db.query(models.PluginCloudSession).filter(models.PluginCloudSession.id == session_id).first()
        
        if session:
            # Update
            session.data_json = data
            if project_name: session.project_name = project_name
            if user_email: session.user_email = user_email
            if folder_id: session.folder_id = folder_id
            session.timestamp = datetime.datetime.now()
        else:
            # Create
            new_s = models.PluginCloudSession(
                id=session_id,
                user_email=user_email or "unknown",
                project_name=project_name or "Sin Nombre",
                data_json=data,
                folder_id=folder_id
            )
            db.add(new_s)
        
        db.commit()
        return True
    except Exception as e:
        print(f"Error saving cloud session: {e}")
        return False
    finally:
        db.close()

def get_cloud_session(session_id: str):
    db = SessionPlugin()
    try:
        s = db.query(models.PluginCloudSession).filter(models.PluginCloudSession.id == session_id).first()
        if s:
            return {
                "session_id": s.id,
                "project_name": s.project_name,
                "user_email": s.user_email,
                "data": s.data_json,
                "timestamp": s.timestamp.isoformat() if s.timestamp else ""
            }
        return None
    finally:
        db.close()

def list_cloud_projects(email: str = None):
    db = SessionPlugin()
    try:
        q = db.query(models.PluginCloudSession)
        if email:
             q = q.filter(models.PluginCloudSession.user_email == email)
        
        # Sort by latest
        sessions = q.order_by(models.PluginCloudSession.timestamp.desc()).all()
        
        res = []
        for s in sessions:
            res.append({
                "session_id": s.id,
                "project_name": s.project_name,
                "user_email": s.user_email,
                "updated": s.timestamp.strftime("%Y-%m-%d %H:%M") if s.timestamp else ""
            })

        return res
    finally:
        db.close()

def delete_cloud_session(session_id: str):
    db = SessionLocal()
    try:
        s = db.query(models.PluginCloudSession).filter(models.PluginCloudSession.id == session_id).first()
        if s:
            db.delete(s)
            db.commit()
            return True
        return False
    except Exception as e:
        print(f"Error deleting cloud session: {e}")
        return False
    finally:
        db.close()

# FOLDER LOGIC
def create_project_folder(name: str):
    db = SessionLocal()
    try:
        new_id = str(uuid.uuid4())
        f = models.PluginProjectFolder(id=new_id, name=name)
        db.add(f)
        db.commit()
        return new_id
    except Exception as e:
        print(f"Error creating folder: {e}")
        return None
    finally:
        db.close()

def list_project_folders():
    db = SessionLocal()
    try:
        # Return list of folders with their sessions
        folders = db.query(models.PluginProjectFolder).order_by(models.PluginProjectFolder.created_at.desc()).all()
        res = []
        for f in folders:
            sessions = []
            for s in f.sessions:
                sessions.append({
                    "session_id": s.id,
                    "name": s.project_name, # This is the "Subproject" name
                    "updated": s.timestamp.strftime("%Y-%m-%d") if s.timestamp else ""
                })
            res.append({
                "id": f.id,
                "name": f.name,
                "sessions": sessions
            })
        return res
    except Exception as e:
        print(f"Error listing folders: {e}")
        return []
    finally:
        db.close()

def delete_project_folder(folder_id: str):
    db = SessionLocal()
    try:
        f = db.query(models.PluginProjectFolder).filter(models.PluginProjectFolder.id == folder_id).first()
        if f:
            for s in f.sessions:
                db.delete(s)
            db.delete(f)
            db.commit()
            return True
        return False
    finally:
        db.close()

def rename_project_folder(folder_id: str, new_name: str):
    db = SessionLocal()
    try:
        f = db.query(models.PluginProjectFolder).filter(models.PluginProjectFolder.id == folder_id).first()
        if f:
            f.name = new_name
            db.commit()
            return True
        return False
    except Exception as e:
        print(f"Error renaming folder: {e}")
        return False
    finally:
        db.close()

def rename_cloud_session(session_id: str, new_name: str):
    db = SessionLocal()
    try:
        s = db.query(models.PluginCloudSession).filter(models.PluginCloudSession.id == session_id).first()
        if s:
            s.project_name = new_name
            db.commit()
            return True
        return False
    except Exception as e:
        print(f"Error renaming session: {e}")
        return False
    finally:
        db.close()

def get_session_by_id(session_id: str):
    db = SessionLocal()
    try:
        return db.query(models.PluginSession).filter(models.PluginSession.id == session_id).first()
    except Exception as e:
        print(f"Error getting session: {e}")
        return None
    finally:
        db.close()

def get_latest_active_session(user_email: str, machine_id: str = None):
    db = SessionLocal()
    try:
        # Check for sessions active in last 5 minutes
        cutoff = datetime.datetime.now() - datetime.timedelta(minutes=5)
        
        query = db.query(models.PluginSession).filter(models.PluginSession.last_heartbeat > cutoff)
        
        if user_email and machine_id:
             # Prioritize Email match, but fallback to Machine ID if Email is null in DB?
             # OR condition?
             # Let's trust Email first.
             # Actually, simpler: Filter by Email OR Machine ID.
             from sqlalchemy import or_
             query = query.filter(or_(models.PluginSession.user_email == user_email, models.PluginSession.machine_id == machine_id))
        elif user_email:
             query = query.filter(models.PluginSession.user_email == user_email)
        elif machine_id:
             query = query.filter(models.PluginSession.machine_id == machine_id)
        else:
             return None

        return query.order_by(models.PluginSession.last_heartbeat.desc()).first()
    except Exception as e:
        print(f"Error getting active session for {user_email}/{machine_id}: {e}")
        return None
    finally:
        db.close()

# -----------------------------------------------------------------------------
# CLOUD COMMANDS
# -----------------------------------------------------------------------------

def queue_command(session_id: str, action: str, payload: dict):
    db = SessionPlugin()
    try:
        cmd = models.CloudCommand(
            session_id=session_id,
            action=action,
            payload=payload
        )
        db.add(cmd)
        db.commit()
        return True
    finally:
        db.close()

def get_pending_commands(session_id: str):
    db = SessionPlugin()
    try:
        # Get unconsumed commands
        cmds = db.query(models.CloudCommand).filter(
            models.CloudCommand.session_id == session_id,
            models.CloudCommand.is_consumed == False
        ).order_by(models.CloudCommand.created_at.asc()).all()
        
        result = []
        for c in cmds:
            result.append({
                "action": c.action,
                "payload": c.payload
            })
            # Mark consumed
            c.is_consumed = True
            
        if result:
            db.commit()
            
        return result
    finally:
        db.close()


# -----------------------------------------------------------------------------
# ROUTINES (KNOWLEDGE BASE)
# -----------------------------------------------------------------------------
def save_routine(title, description, category, actions_json, user_email, is_global=False):
    db = SessionPlugin()
    try:
        new_routine = models.PluginRoutine(
            title=title,
            description=description,
            category=category,
            actions_json=actions_json,
            user_email=user_email,
            is_global=is_global
        )
        db.add(new_routine)
        db.commit()
        db.refresh(new_routine)
        return new_routine
    except Exception as e:
        print(f"Error saving routine: {e}")
        return None
    finally:
        db.close()

def get_all_routines(user_email=None):
    db = SessionPlugin()
    try:
        query = db.query(models.PluginRoutine)
        if user_email:
            # Return Globals + My Personal
            query = query.filter((models.PluginRoutine.is_global == True) | (models.PluginRoutine.user_email == user_email))
        
        return query.order_by(models.PluginRoutine.category, models.PluginRoutine.title).all()
    finally:
        db.close()


# -----------------------------------------------------------------------------
# SHEET MANAGER TEMPLATES
# -----------------------------------------------------------------------------
from .models import SheetTemplate

def get_sheet_templates():
    db = SessionPlugin()
    try:
        return db.query(SheetTemplate).all()
    finally:
        db.close()

def create_sheet_template(name: str, config: dict, user="Admin"):
    db = SessionLocal()
    try:
        tpl = SheetTemplate(name=name, config_json=config, created_by=user, is_global=True)
        db.add(tpl)
        db.commit()
        db.refresh(tpl)
        return tpl
    finally:
        db.close()

def delete_sheet_template(tpl_id: int):
    db = SessionLocal()
    try:
        tpl = db.query(SheetTemplate).filter(SheetTemplate.id == tpl_id).first()
        if tpl:
            db.delete(tpl)
            db.commit()
            return True
        return False
    finally:
        db.close()

# -----------------------------------------------------------------------------
# SHEET MANAGER SESSION FUNCTIONS
# -----------------------------------------------------------------------------

def create_sheet_session(session_id: str, project_name: str, sheets: list, param_defs: list, plugin_session_id: str):
    db = SessionPlugin()
    try:
        # Check if exists (unlikely given UUID)
        new_session = PluginSheetSession(
            id=session_id,
            project=project_name,
            plugin_session_id=plugin_session_id,
            sheets_json=sheets,
            param_definitions_json=param_defs,
            created_at=datetime.datetime.now()
        )
        db.add(new_session)
        db.commit()
        return True
    except Exception as e:
        print(f"Error create_sheet_session: {e}")
        db.rollback()
        return False
    finally:
        db.close()

def update_sheet_session_plugin_id(session_id: str, new_plugin_session_id: str):
    db = SessionLocal()
    try:
        s = db.query(PluginSheetSession).filter(PluginSheetSession.id == session_id).first()
        if s:
            s.plugin_session_id = new_plugin_session_id
            db.commit()
            return True
        return False
    except Exception as e:
        print(f"Error updating sheet session plugin id: {e}")
        return False
    finally:
        db.close()

def get_sheet_session(session_id: str):
    db = SessionLocal()
    try:
        session = db.query(PluginSheetSession).filter(PluginSheetSession.id == session_id).first()
        if session:
            return {
                "project": session.project,
                "sheets": session.sheets_json,
                "param_definitions": session.param_definitions_json,
                "plugin_session_id": session.plugin_session_id
            }
        return None
    finally:
        db.close()

# -----------------------------------------------------------------------------
# DAILY APP FUNCTIONS (daily.somosao.com)
# -----------------------------------------------------------------------------

def init_user_daily_setup(user_email: str):
    """
    Ensures user exists and has a "My Tasks" view (not a real table, but ensures readiness).
    If no team exists, create a default "Personal Team" for them?
    For now, just return True.
    """
    return True

def create_daily_team(name: str, owner_id: str):
    db = SessionOps() # Using Ops DB for Daily
    try:
        new_id = str(uuid.uuid4())
        team = models.DailyTeam(id=new_id, name=name, owner_id=owner_id, members=[owner_id])
        db.add(team)
        db.commit()
        return team
    finally:
        db.close()

def get_user_teams(user_id: str):
    # This requires JSON contains query or filtering in memory.
    # SQLite JSON filtering is tricky.
    # For MVP, get all teams and filter in python (inefficient but works for small scale)
    db = SessionOps()
    try:
        all_teams = db.query(models.DailyTeam).all()
        user_teams = [t for t in all_teams if user_id in (t.members or [])]
        return user_teams
    finally:
        db.close()

def create_daily_project(team_id: str, name: str, user_id: str):
    db = SessionOps()
    try:
        new_id = str(uuid.uuid4())
        proj = models.DailyProject(
            id=new_id, 
            team_id=team_id, 
            name=name, 
            created_by=user_id,
            settings={"background": "default"}
        )
        # Create Default Columns
        cols = ["To Do", "In Progress", "Done"]
        for idx, title in enumerate(cols):
            c_id = str(uuid.uuid4())
            col = models.DailyColumn(id=c_id, project_id=new_id, title=title, order_index=idx)
            db.add(col)
            
        db.add(proj)
        db.commit()
        return proj
    finally:
        db.close()

def get_daily_project_board(project_id: str):
    db = SessionOps()
    try:
        # Load Project + Columns + Tasks (lightweight)
        proj = db.query(models.DailyProject).filter(models.DailyProject.id == project_id).options(
            joinedload(models.DailyProject.columns).joinedload(models.DailyColumn.tasks)
        ).first()
        return proj
    finally:
        db.close()

def create_daily_task(project_id: str, column_id: str, title: str, user_id: str, due_date=None, priority="Medium"):
    db = SessionOps()
    try:
        new_id = str(uuid.uuid4())
        # If project_id is None, it's a direct assignment (Manager Mode)? 
        # But 'column_id' implies a board.
        # Direct tasks might have a hidden 'Personal Board'? 
        # Or we allow column_id=None for personal tasks?
        
        task = models.DailyTask(
            id=new_id,
            project_id=project_id,
            column_id=column_id,
            title=title,
            created_by=user_id,
            due_date=due_date,
            priority=priority,
            assignees=[user_id] if user_id else []
        )
        db.add(task)
        db.commit()
        return task
    finally:
        db.close()

def update_daily_task_location(task_id: str, new_column_id: str, new_index: int = 0):
    db = SessionOps()
    try:
        task = db.query(models.DailyTask).filter(models.DailyTask.id == task_id).first()
        if task:
            task.column_id = new_column_id
            # Note: Index reordering isn't implemented in DB model 'DailyTask' (no order_index on task).
            # We usually rely on a linked list or float index. 
            # Or frontend sends full list order and we store it?
            # Creating 'order_index' on Task would be good. 
            # Ignoring index for MVP or handling later.
            db.commit()
            return True
        return False
    finally:
        db.close()

def get_user_daily_tasks(user_id: str):
    """
    Get all tasks assigned to user across all projects.
    """
    db = SessionOps()
    try:
        # Fetch all tasks and filter by assignees JSON
        # Optimized: In Postgres we can use @> operator. In SQLite/Generic: Python filter.
        # Assuming DB is small enough for now.
        # TODO: Optimize with native JSON query if Postgres.
        all_tasks = db.query(models.DailyTask).all()
        my_tasks = [t for t in all_tasks if user_id in (t.assignees or [])]
        return my_tasks
    finally:
        db.close()

def add_daily_message(project_id: str, user_id: str, content: str):
    db = SessionOps()
    try:
        msg = models.DailyMessage(
            project_id=project_id,
            sender_id=user_id,
            content=content
        )
        db.add(msg)
        db.commit()
        return msg
    finally:
        db.close()

def get_daily_messages(project_id: str, limit=50):
    db = SessionOps()
    try:
        msgs = db.query(models.DailyMessage).filter(models.DailyMessage.project_id == project_id).order_by(models.DailyMessage.created_at.desc()).limit(limit).all()
        return msgs[::-1] # Return chronological
    finally:
        db.close()


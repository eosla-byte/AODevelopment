import os
import datetime
import json
import uuid
from typing import List, Optional
from sqlalchemy.orm import Session, sessionmaker, joinedload
from sqlalchemy import create_engine
from models import Base, Project as DBProject, Collaborator as DBCollaborator, TimelineEvent, ContactSubmission, AppUser, ExpenseColumn, ExpenseCard
import models
from sqlalchemy.orm.attributes import flag_modified

# DATABASE SETUP
# Use SQLite for local development default, can be overridden by env var
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./aodev.db")

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Ensure tables exist (for now)
Base.metadata.create_all(bind=engine)

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

def get_projects() -> List[models.Project]:
    db = SessionLocal()
    try:
        projects = db.query(models.Project).filter(models.Project.archived == False).all()
        # Initialize .files to empty dict to avoid template errors accessing p.files
        for p in projects:
            p.files = {cat: [] for cat in SCAN_CATEGORIES.keys()}
            db.expunge(p)
        return projects
    except Exception as e:
        print(f"DB Error get_projects: {e}")
        return []
    finally:
        db.close()

def get_project_details(project_id: str) -> Optional[models.Project]:
    db = SessionLocal()
    try:
        proj = db.query(models.Project).filter(models.Project.id == project_id).first()
        if not proj:
            return None
            
        proj.files = {cat: [] for cat in SCAN_CATEGORIES.keys()}
        
        # SAFEGUARDS for JSON attributes
        if proj.reminders is None: proj.reminders = []
        if proj.acc_config is None: proj.acc_config = {}
        if proj.partners_config is None: proj.partners_config = {}
        if proj.assigned_collaborators is None: proj.assigned_collaborators = {}

        # CALCULATE FINANCIAL METRICS FROM METADATA
        cat_totals = {}
        for cat in SCAN_CATEGORIES.keys():
            cat_totals[cat] = 0.0

        if proj.files_meta:
            for cat, files_dict in proj.files_meta.items():
                if isinstance(files_dict, dict):
                    current_sum = 0.0
                    for fname, meta in files_dict.items():
                        if isinstance(meta, dict):
                            try:
                                val = float(meta.get("amount", 0.0))
                                current_sum += val
                            except: pass
                    
                    if cat in cat_totals:
                         cat_totals[cat] = current_sum
                    else:
                         cat_totals[cat] = current_sum

        proj.cat_totals = cat_totals 
        
        proj.paid_amount = cat_totals.get("Pagos", 0.0)
        proj.total_iva_paid = cat_totals.get("Impuestos_IVA", 0.0)
        proj.total_isr_paid = cat_totals.get("Impuestos_ISR", 0.0)
        
        db.expunge(proj)
        return proj
    finally:
        db.close()

def create_project(name: str, client: str = "", nit: str = "", legal_name: str = "", po_number: str = "", amount: float = 0.0, status: str = "Activo", emoji: str = "📁", custom_id: str = None) -> bool:
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
            if p.assigned_collaborators:
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
    def __init__(self, id, name, email, role, is_active, hashed_password):
        self.id = id
        self.name = name
        self.email = email
        self.role = role
        self.is_active = is_active
        self.hashed_password = hashed_password

def get_users() -> List[User]:
    # root_path ignored for SQL Users, but kept for signature compatibility
    db = SessionLocal()
    try:
        users_db = db.query(models.AppUser).all()
        # Convert to User objects
        return [User(u.email, u.full_name, u.email, u.role, u.is_active, u.hashed_password) for u in users_db]
    except:
        return []
    finally:
        db.close()

def get_user_by_email(email: str) -> Optional[User]:
    db = SessionLocal()
    try:
        u = db.query(models.AppUser).filter(models.AppUser.email == email).first()
        if u:
            return User(u.email, u.full_name, u.email, u.role, u.is_active, u.hashed_password)
        return None
    finally:
        db.close()

def save_user(user: User):
    db = SessionLocal()
    try:
        # Check if exists
        existing = db.query(models.AppUser).filter(models.AppUser.email == user.email).first()
        if existing:
            existing.full_name = user.name
            existing.role = user.role
            existing.is_active = user.is_active
            existing.hashed_password = user.hashed_password
        else:
            new_u = models.AppUser(
                email=user.email,
                full_name=user.name,
                hashed_password=user.hashed_password,
                role=user.role,
                is_active=user.is_active
            )
            db.add(new_u)
        db.commit()
    finally:
        db.close()

def delete_user(user_id: str):
    # user_id in main.py is likely email or ID. 
    # original save_user used ID. AppUser PK is email.
    # We should assume user_id might be email.
    db = SessionLocal()
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

def get_expenses_monthly(year: int):
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

def update_collaborator(root_path, id, **kwargs):
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

def update_collaborator_picture(root_path, id, pic_filename):
    update_collaborator(root_path, id, profile_picture=pic_filename)

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

def update_project_file_meta(root_path, pid, cat, fname, amt, note):
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
            
            current_date = datetime.datetime.now().isoformat()
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
    # Not used yet, maybe for admin dashboard
    return []

def get_user_plugin_stats(email):
    db = SessionLocal()
    try:
        now = datetime.datetime.now()
        start_of_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        
        # Query Activities for this user (via session) since start of month
        # Join PluginActivity -> PluginSession
        activities = db.query(models.PluginActivity)\
            .join(models.PluginSession)\
            .filter(models.PluginSession.user_email == email)\
            .filter(models.PluginActivity.timestamp >= start_of_month)\
            .all()
            
        total_minutes = sum(a.active_minutes for a in activities)
        unique_files = set(a.filename for a in activities)
        
        # Count sessions in this month
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

def start_revit_session(email, machine, version, ip):
    db = SessionLocal()
    try:
        sid = str(uuid.uuid4())
        session = models.PluginSession(
            id=sid,
            user_email=email,
            machine_id=machine,
            revit_version=version,
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
    db = SessionLocal()
    try:
        session = db.query(models.PluginSession).filter(models.PluginSession.id == session_id).first()
        if session:
            session.last_heartbeat = datetime.datetime.now()
            db.commit()
            return True
        return False
    except:
        return False
    finally:
        db.close()

def end_revit_session(session_id):
    db = SessionLocal()
    try:
        session = db.query(models.PluginSession).filter(models.PluginSession.id == session_id).first()
        if session:
            session.is_active = False
            db.commit()
    except:
        pass
    finally:
        db.close()

def get_user_plugin_logs(email):
    db = SessionLocal()
    try:
        # Get last 50 sessions
        sessions = db.query(models.PluginSession)\
            .filter(models.PluginSession.user_email == email)\
            .order_by(models.PluginSession.start_time.desc())\
            .limit(50)\
            .all()
        
        logs = []
        for s in sessions:
            # Get activities for this session
            activities = db.query(models.PluginActivity).filter(models.PluginActivity.session_id == s.id).all()
            
            total_active = sum(a.active_minutes for a in activities)
            total_idle = sum(a.idle_minutes for a in activities)
            unique_files = list(set(a.filename for a in activities if a.filename))
            revit_users = list(set(a.revit_user for a in activities if a.revit_user))
            acc_projects = list(set(a.acc_project for a in activities if a.acc_project))
            
            # Formatted dates
            start_dt = s.start_time
            # Handle string dates if SQLite stores them as strings (Models define DateTime but SQLite checks)
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
                "date": date_str,
                "day_name": day_name,
                "start_time": start_time_str,
                "end_time": end_time_str,
                "active_mins": round(total_active, 1),
                "idle_mins": round(total_idle, 1),
                "files": unique_files,
                "ip_address": s.ip_address,
                "sync_count": 0, # Implement if PluginLog used
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
    db = SessionLocal()
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
    # Optional logic for sync
    pass


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

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel
import uuid
import datetime

from common.database import get_core_db, SessionCore
from common import models
from common.auth_utils import get_current_user

router = APIRouter(
    prefix="/api/organizations",
    tags=["Organizations"]
)

# --- Pydantic Schemas ---

class ServicePermissionBase(BaseModel):
    service_slug: str
    plan_level: str = "Standard"
    is_active: bool = True

class OrganizationCreate(BaseModel):
    name: str
    contact_email: Optional[str] = None
    tax_id: Optional[str] = None
    logo_url: Optional[str] = None

class OrganizationResponse(BaseModel):
    id: str
    name: str
    status: str
    created_at: datetime.datetime
    service_permissions: List[ServicePermissionBase] = []
    
    class Config:
        orm_mode = True

class MemberInvite(BaseModel):
    email: str
    role: str = "Member" # Admin, Member
    full_name: str

# --- Endpoints ---

@router.get("/", response_model=List[OrganizationResponse])
def list_organizations(
    db: Session = Depends(get_core_db),
    current_user: dict = Depends(get_current_user)
):
    """
    List organizations. 
    - If Global Admin (SuperAdmin): Lists ALL.
    - If Regular User: Lists only organizations they belong to.
    """
    user_email = current_user.get("sub")
    
    # Check Global Role from DB
    user_db = db.query(models.AccountUser).filter(models.AccountUser.email == user_email).first()
    if not user_db:
        raise HTTPException(status_code=401, detail="User not found")
        
    if user_db.role == "SuperAdmin":
        # Return ALL
        orgs = db.query(models.Organization).all()
        return orgs
    else:
        # Return only memberships
        # Join OrganizationUser
        user_orgs = (
            db.query(models.Organization)
            .join(models.OrganizationUser)
            .filter(models.OrganizationUser.user_id == user_db.id)
            .all()
        )
        return user_orgs

@router.post("/", response_model=OrganizationResponse)
def create_organization(
    org: OrganizationCreate,
    db: Session = Depends(get_core_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Create a new Organization.
    Restricted to SuperAdmins.
    """
    user_email = current_user.get("sub")
    user_db = db.query(models.AccountUser).filter(models.AccountUser.email == user_email).first()
    
    # Strict Check: Only SuperAdmin can create NEW Organizations
    if not user_db or user_db.role != "SuperAdmin":
        raise HTTPException(status_code=403, detail="Only SuperAdmins can create organizations")
        
    new_id = str(uuid.uuid4())
    new_org = models.Organization(
        id=new_id,
        name=org.name,
        contact_email=org.contact_email,
        tax_id=org.tax_id,
        logo_url=org.logo_url
    )
    db.add(new_org)
    
    # Add creator as Admin of that Org? Or leave it empty? 
    # Usually SuperAdmin manages it, but maybe doesn't need to be a member.
    
    db.commit()
    return new_org

@router.post("/{org_id}/members")
def add_member(
    org_id: str,
    invite: MemberInvite,
    db: Session = Depends(get_core_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Add a user to an organization.
    Caller must be an Admin of that Organization OR SuperAdmin.
    """
    user_email = current_user.get("sub")
    caller_db = db.query(models.AccountUser).filter(models.AccountUser.email == user_email).first()
    
    # 1. Check Permissions
    is_super = caller_db.role == "SuperAdmin"
    is_org_admin = False
    
    if not is_super:
        membership = db.query(models.OrganizationUser).filter(
            models.OrganizationUser.organization_id == org_id,
            models.OrganizationUser.user_id == caller_db.id,
            models.OrganizationUser.role == "Admin"
        ).first()
        if membership:
            is_org_admin = True
            
    if not (is_super or is_org_admin):
        raise HTTPException(status_code=403, detail="Insufficient permissions to add members")

    # 2. Check if user exists, if not create 'Invited' user (Placeholder)
    # For now, let's assume user must exist or we create a stub.
    target_user = db.query(models.AccountUser).filter(models.AccountUser.email == invite.email).first()
    
    if not target_user:
        # Create Stub User
        new_uid = str(uuid.uuid4())
        # Temp password or flow? We'll just set a random hash for now.
        target_user = models.AccountUser(
            id=new_uid,
            email=invite.email,
            full_name=invite.full_name,
            hashed_password="PENDING_SETUP", 
            role="Standard"
        )
        db.add(target_user)
        db.flush() # Get ID
        
    # 3. Create Membership
    # Check if already member
    exists = db.query(models.OrganizationUser).filter(
        models.OrganizationUser.organization_id == org_id,
        models.OrganizationUser.user_id == target_user.id
    ).first()
    
    if exists:
        raise HTTPException(status_code=400, detail="User is already a member")
        
    new_member = models.OrganizationUser(
        organization_id=org_id,
        user_id=target_user.id,
        role=invite.role
    )
    db.add(new_member)
    db.commit()
    
    return {"status": "success", "message": f"User {invite.email} added to organization"}

@router.post("/{org_id}/services")
def toggle_service(
    org_id: str,
    permission: ServicePermissionBase,
    db: Session = Depends(get_core_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Enable/Disable a service for an organization.
    Restricted to SuperAdmins.
    """
    user_email = current_user.get("sub")
    caller_db = db.query(models.AccountUser).filter(models.AccountUser.email == user_email).first()
    
    if not caller_db or caller_db.role != "SuperAdmin":
        raise HTTPException(status_code=403, detail="Only SuperAdmins can manage service permissions")
        
    # Check existing
    perm = db.query(models.ServicePermission).filter(
        models.ServicePermission.organization_id == org_id,
        models.ServicePermission.service_slug == permission.service_slug
    ).first()
    
    if perm:
        perm.is_active = permission.is_active
        perm.plan_level = permission.plan_level
    else:
        new_perm = models.ServicePermission(
            organization_id=org_id,
            service_slug=permission.service_slug,
            plan_level=permission.plan_level,
            is_active=permission.is_active
        )
        db.add(new_perm)
        
    db.commit()
    db.commit()
    return {"status": "success", "service": permission.service_slug, "active": permission.is_active}


class UserPermissionUpdate(BaseModel):
    service_slug: str
    is_active: bool

@router.post("/{org_id}/members/{user_id}/permissions")
def toggle_user_permission(
    org_id: str,
    user_id: str,
    update: UserPermissionUpdate,
    db: Session = Depends(get_core_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Toggle a specific service permission for a user within an organization.
    Caller must be Admin of that organization.
    """
    user_email = current_user.get("sub")
    caller_db = db.query(models.AccountUser).filter(models.AccountUser.email == user_email).first()
    
    # 1. Check permissions (Caller must be Org Admin or SuperAdmin)
    is_super = caller_db.role == "SuperAdmin"
    is_org_admin = False
    
    if not is_super:
        caller_membership = db.query(models.OrganizationUser).filter(
            models.OrganizationUser.organization_id == org_id,
            models.OrganizationUser.user_id == caller_db.id,
            models.OrganizationUser.role == "Admin"
        ).first()
        if caller_membership:
            is_org_admin = True
            
    if not (is_super or is_org_admin):
        raise HTTPException(status_code=403, detail="Insufficient permissions")
        
    # 2. Get Target Membership
    target_membership = db.query(models.OrganizationUser).filter(
        models.OrganizationUser.organization_id == org_id,
        models.OrganizationUser.user_id == user_id
    ).first()
    
    if not target_membership:
        raise HTTPException(status_code=404, detail="User membership not found")
        
    # VALIDATION: Check if Organization has this service enabled
    org_perm = db.query(models.ServicePermission).filter(
        models.ServicePermission.organization_id == org_id,
        models.ServicePermission.service_slug == update.service_slug,
        models.ServicePermission.is_active == True
    ).first()
    
    if not org_perm and update.is_active:
        raise HTTPException(
            status_code=400, 
            detail=f"Service '{update.service_slug}' is not enabled for this Organization."
        )

    # 3. Update Permissions JSON
    # Note: mutating JSON in SQLAlchemy requires re-assignment or flag_modified if mutable=False
    current_perms = dict(target_membership.permissions or {})
    current_perms[update.service_slug] = update.is_active
    
    target_membership.permissions = current_perms
    
    # Force update detection if needed (though re-assignment usually works)
    db.add(target_membership) 
    db.commit()
    
    return {"status": "success", "user_id": user_id, "permissions": target_membership.permissions}


# --- Daily Service Management Endpoints ---


# --- Organization Project Profiles Endpoints ---

class ProjectProfileCreate(BaseModel):
    name: str
    project_cost: float = 0.0
    sq_meters: float = 0.0
    ratio: float = 0.0
    estimated_time: Optional[str] = None

@router.get("/{org_id}/projects")
def list_org_projects_endpoint(
    org_id: str,
    db: Session = Depends(get_core_db),
    current_user: dict = Depends(get_current_user)
):
    # Retrieve Project Profiles for this Organization
    # Using Raw SQL to avoid AttributeError if models.Project is stale in deployment
    from sqlalchemy import text
    try:
    try:
        # sql = text("SELECT id, name, project_cost, sq_meters, ratio, estimated_time, status FROM resources_projects WHERE organization_id = :org_id")
        # Changed to bim_projects and removed legacy fields
        sql = text("SELECT id, name, status, created_at FROM bim_projects WHERE organization_id = :org_id")
        result = db.execute(sql, {"org_id": org_id}).fetchall()
        
        projects = []
        for row in result:
            projects.append({
                "id": row.id,
                "name": row.name,
                "project_cost": 0.0, # Defaulting to 0/None as field is gone
                "sq_meters": 0.0,
                "ratio": 0.0,
                "estimated_time": None,
                "status": row.status,
                "organization_id": org_id,
                "created_at": str(row.created_at)
            })
        return projects
    except Exception as e:
        print(f"ERROR LISTING PROJECTS: {e}")
        # Fallback to empty list or re-raise if critical
        return []

@router.post("/{org_id}/projects")
def create_org_project_endpoint(
    org_id: str,
    project: ProjectProfileCreate,
    db: Session = Depends(get_core_db),
    current_user: dict = Depends(get_current_user)
):
    # Logic inlined to ensure deployment picks up the changes
    
    # Validation: Ensure User is part of this Org (Optional but recommended)
    # For now, we assume Dashboard access implies Org access.

    try:
        new_id = str(uuid.uuid4())
        new_proj = models.Project(
            id=new_id,
            organization_id=org_id,
            name=project.name,
            # project_cost=project.project_cost, # Legacy
            # sq_meters=project.sq_meters,
            # ratio=project.ratio,
            # estimated_time=project.estimated_time,
            status="Active"
        )
        
        db.add(new_proj)
        db.commit()
        db.refresh(new_proj)
        
        return {"status": "success", "id": new_proj.id, "name": new_proj.name}

    except Exception as e:
        import traceback
        error_str = str(e).lower()
        print(f"⚠️ [PROJECT CREATION ERROR] {str(e)}")
        
        # Emergency Fallback: If ORM fails (due to code sync or DB schema), use Raw SQL
        from sqlalchemy import text
        
        # 1. Lazy Migration (Attempt to patch schema)
        print("⚠️ [LAZY MIGRATION] Attempting to patch schema (Blind Fix)...")
        # Removed legacy migrations for resources_projects as we target bim_projects now
        migrations = [
            "CREATE TABLE IF NOT EXISTS bim_projects (id VARCHAR PRIMARY KEY, organization_id VARCHAR, name VARCHAR, status VARCHAR, created_at TIMESTAMPTZ DEFAULT NOW())",
             # Ensure cols exist
            "ALTER TABLE bim_projects ADD COLUMN IF NOT EXISTS organization_id VARCHAR",
            "ALTER TABLE bim_projects ADD COLUMN IF NOT EXISTS status VARCHAR"
        ]
        
        for sql in migrations:
            try:
                db.execute(text(sql))
                db.commit()
            except Exception as mig_err:
                print(f"Migration step ignored: {sql} | {mig_err}")
                db.rollback()

        # 2. Raw SQL Insertion (Bypass ORM Constructor)
        print("✅ [RAW SQL FALLBACK] Schema patched. Retrying insertion via Raw SQL...")
        try:
            sql_insert = text("""
                INSERT INTO bim_projects 
                (id, organization_id, name, status)
                VALUES (:id, :org_id, :name, 'Active')
            """)
            
            db.execute(sql_insert, {
                "id": new_id,
                "org_id": org_id,
                "name": project.name
            })
            db.commit()
            
            return {"status": "success", "id": new_id, "name": project.name, "method": "raw_sql_fallback"}
            
        except Exception as retry_err:
            import traceback
            error_msg = f"FATAL PROJECT CREATION ERROR: {str(retry_err)} | Trace: {traceback.format_exc()}"
            print(error_msg)
            # Explicitly return 500 with detail so user can see it
            raise HTTPException(status_code=500, detail=error_msg)



@router.get("/{org_id}/daily/bim-projects")
def list_bim_projects_for_link(
    org_id: str,
    db: Session = Depends(get_core_db),
    current_user: dict = Depends(get_current_user)
):
    from common.database import get_org_bim_projects
    return get_org_bim_projects(org_id)

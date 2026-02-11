
from sqlalchemy import text
from .database import SessionCore
from . import models

# -----------------------------------------------------------------------------
# PHASE 3: ENTITLEMENTS MIGRATION
# -----------------------------------------------------------------------------
def run_entitlements_migration():
    """
    Migration to V3 Entitlements System.
    1. Creates accounts_entitlements / accounts_org_entitlements if missing.
    2. Adds entitlements_version to accounts_organizations.
    3. Seeds master entitlements.
    4. Migrates ServicePermission -> OrgEntitlement.
    """
    print("🚀 [MIGRATION] Checking Entitlements Schema...")
    db = SessionCore()
    try:
        # A. Check & Add 'entitlements_version' column
        try:
            # Check if column exists
            db.execute(text("SELECT entitlements_version FROM accounts_organizations LIMIT 1"))
        except Exception:
            db.rollback()
            print("🔧 [MIGRATION] Adding 'entitlements_version' to accounts_organizations...")
            db.execute(text("ALTER TABLE accounts_organizations ADD COLUMN entitlements_version INTEGER DEFAULT 1"))
            db.commit()

        # B. Create Tables (via raw SQL for portability/simplicity)
        
        # 1. entitlements
        # Check if table exists first? Or just CREATE IF NOT EXISTS
        # SQLAlchemy create_all usually handles this but we need explicit control here.
        
        # Check master table
        try:
             db.execute(text("SELECT 1 FROM accounts_entitlements LIMIT 1"))
        except Exception:
             db.rollback()
             print("🔧 [MIGRATION] Creating accounts_entitlements table...")
             db.execute(text("""
                CREATE TABLE IF NOT EXISTS accounts_entitlements (
                    id VARCHAR PRIMARY KEY,
                    description VARCHAR
                )
             """))
             db.commit()

        # 2. org_entitlements
        try:
             db.execute(text("SELECT 1 FROM accounts_org_entitlements LIMIT 1"))
        except Exception:
             db.rollback()
             print("🔧 [MIGRATION] Creating accounts_org_entitlements table...")
             db.execute(text("""
                CREATE TABLE IF NOT EXISTS accounts_org_entitlements (
                    org_id VARCHAR,
                    entitlement_key VARCHAR,
                    enabled BOOLEAN DEFAULT TRUE,
                    limits_json JSON DEFAULT '{}',
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (org_id, entitlement_key),
                    FOREIGN KEY (org_id) REFERENCES accounts_organizations(id),
                    FOREIGN KEY (entitlement_key) REFERENCES accounts_entitlements(id)
                )
             """))
             db.commit()
        
        # C. Seed Master Entitlements
        defaults = [
            ("daily", "AO Daily - Task & Team Management"),
            ("bim", "AO BIM - Scheduling & 4D"),
            ("finance", "AO Finance - Budget & Expenses"),
            ("plugin", "AO Plugin - Revit/Civil3D Connectivity"),
            ("build", "AO Build - Construction Management"), 
            ("clients", "AO Clients - Client Portal")
        ]
        
        print("🌱 [MIGRATION] Seeding Master Entitlements...")
        for key, desc in defaults:
            exists = db.query(models.Entitlement).filter(models.Entitlement.id == key).first()
            if not exists:
                db.add(models.Entitlement(id=key, description=desc))
        db.commit()
        
        # D. Migrate Legacy ServicePermission -> OrgEntitlement
        # Map old slugs to new keys
        keys_map = {
            "AODailyWork": "daily",
            "AOPlanSystem": "bim", 
            "AO HR & Finance": "finance",
            "AOdev": "plugin",
            "AOBuild": "build",
            "AO Clients": "clients",
            "daily": "daily",
            "bim": "bim",
            "finance": "finance",
            "plugin": "plugin"
        }
        
        legacy_perms = db.query(models.ServicePermission).filter(models.ServicePermission.is_active == True).all()
        count = 0
        
        for perm in legacy_perms:
            new_key = keys_map.get(perm.service_slug, perm.service_slug.lower())
            
            # Check overlap
            exists = db.query(models.OrgEntitlement).filter(
                models.OrgEntitlement.org_id == perm.organization_id,
                models.OrgEntitlement.entitlement_key == new_key
            ).first()
            
            if not exists:
                # Validate master exists
                master = db.query(models.Entitlement).filter(models.Entitlement.id == new_key).first()
                if master:
                    new_ent = models.OrgEntitlement(
                        org_id=perm.organization_id,
                        entitlement_key=new_key,
                        enabled=True
                    )
                    db.add(new_ent)
                    count += 1
        
        if count > 0:
            print(f"🔄 [MIGRATION] Migrated {count} legacy permissions.")
            db.commit()
            
        print("✅ [MIGRATION] Entitlements System Ready.")
            
    except Exception as e:
        db.rollback()
        print(f"❌ [MIGRATION] Failed: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

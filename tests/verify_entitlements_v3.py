
import sys
import os
import uuid
import time
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# Add backend to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Force Auth Load (to register models?)
from backend.common import auth
from backend.common import models
from backend.common.database import Base, SessionCore, engine_core
from backend.common.entitlements import EntitlementsClient, entitlements_client
from backend.common.db_migration_entitlements import run_entitlements_migration

def verify_entitlements():
    print("[TEST] Starting V3 Entitlements Verification (Hardened)...")
    
    # 0. DB Setup
    db_url = os.getenv("CORE_DB_URL", "sqlite:///./aodev.db")
    print(f"[TEST] DB URL: {db_url}")
    
    # Init DB
    # For SQLite, we might need create_all if deleted. For Postgres, we assume it exists or we run migration.
    # We'll run migration just in case (safe idempotent)
    run_entitlements_migration()
    print("[TEST] Migration/Seeding Complete.")

    db = SessionCore()
    
    try:
        # A. Create Test Organization
        org_id = str(uuid.uuid4())
        org = models.Organization(
            id=org_id,
            name="Entitlements Hardening Test",
            slug=f"test-hardening-{org_id[:8]}",
            entitlements_version=1
        )
        db.add(org)
        db.commit()
        print(f"[SETUP] Created Org: {org.name} (ID: {org_id}, Ver: 1)")
        
        # B. Enable 'daily'
        ent = models.OrgEntitlement(
            org_id=org_id,
            entitlement_key="daily",
            enabled=True
        )
        db.add(ent)
        db.commit()
        print("[SETUP] Enabled 'daily' for Org.")

        # C. Concurrency Simulation
        # Create two separate client instances to simulate two different service pods
        client_a = EntitlementsClient()
        client_b = EntitlementsClient()
        
        print("[TEST] Concurrency: Created Client A and Client B.")
        
        # 1. Client A fetches (Cache Miss -> Hit)
        access_a = client_a.check_access(org_id, 1, "daily")
        print(f"[CHECK A] Ver 1: {access_a} (Expected True)")
        if not access_a: raise Exception("Client A failed initial check")

        # 2. Client B fetches (Cache Miss -> Hit)
        access_b = client_b.check_access(org_id, 1, "daily")
        print(f"[CHECK B] Ver 1: {access_b} (Expected True)")
        if not access_b: raise Exception("Client B failed initial check")
        
        # 3. Modify Plan (Disable 'daily' & Bump Version)
        print("[ACTION] Disabling 'daily' and bumping version to 2...")
        ent.enabled = False
        org.entitlements_version = 2
        db.commit()
        
        # 4. Old Token (Ver 1) on Client A (Should FORCE refresh due to Metadata Check)
        # Note: New "Metadata-First" logic checks DB Version on every request.
        # So even with Old Token, we detect DB Version changed -> Refresh Cache -> Deny.
        access_a_old = client_a.check_access(org_id, 1, "daily")
        print(f"[CHECK A] Old Token (Ver 1): {access_a_old} (Expected False - Immediate Consistency)")
        
        if not access_a_old:
             print("✅ [PASS] Client A correctly detected version change (Immediate Consistency).")
        else:
             print("❌ [FAIL] Client A returned True (Stale Cache detected - unexpected for Metadata-First).")

        # 5. New Token (Ver 2) on Client B (Should FORCE refresh)
        access_b_new = client_b.check_access(org_id, 2, "daily")
        print(f"[CHECK B] New Token (Ver 2): {access_b_new} (Expected False - Forced Refresh)")
        if access_b_new:
             print("❌ [FAIL] Client B returned True for Ver 2 (Should be False)")
        else:
             print("✅ [PASS] Client B correctly refreshed and denied access.")

        # 6. New Token (Ver 2) on Client A (Should Converge)
        access_a_new = client_a.check_access(org_id, 2, "daily")
        print(f"[CHECK A] New Token (Ver 2): {access_a_new} (Expected False - Converged)")
        if access_a_new:
             print("❌ [FAIL] Client A returned True after bump (Should be False)")
        else:
             print("✅ [PASS] Client A converged.")

        # 7. Test Suspension (Hard Revoke)
        print("[ACTION] Suspending Org (Hard Revoke)...")
        # Re-enable daily first to verify suspension blocks it
        ent.enabled = True
        org.status = "Suspended"
        org.entitlements_version += 1 # Bump version to force cache update or we rely on status check? 
        # Logic: If cache is valid, we check status inside cache. 
        # But we need to update cache first. 
        # If we suspend, we likely won't bump version unless we want to force refresh? 
        # Actually our logic checks status IN the cache. 
        # So we need to refresh cache to see the "Suspended" status.
        # Let's bump version to ensure clients pick it up.
        new_ver_susp = org.entitlements_version
        db.commit()
        
        print(f"[CHECK 4] Checking 'daily' for SUSPENDED Org (New Token v{new_ver_susp})...")
        access_susp = client_a.check_access(org_id, new_ver_susp, "daily")
        
        if not access_susp:
             print("✅ [PASS] Suspended Org Access DENIED.")
        else:
             print("❌ [FAIL] Suspended Org Access GRANTED (Crucial Failure).")

    except Exception as e:
        print(f"❌ [TEST] Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()
        print("[TEST] Done.")

if __name__ == "__main__":
    verify_entitlements()

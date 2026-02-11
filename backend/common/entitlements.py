
import os
import time
from typing import Dict, Set
from .database import SessionCore
from . import models

# FEATURE FLAG: Enforcement
ENTITLEMENTS_ENFORCED = os.getenv("ENTITLEMENTS_ENFORCED", "true").lower() == "true"

class EntitlementsClient:
    """
    Client for checking Organization Entitlements with caching.
    Source of Truth: Core DB (accounts_org_entitlements).
    Signal: Token 'entitlements_version' claim.
    """
    
    def __init__(self):
        self._cache: Dict[str, Dict] = {} # { org_id: { version: int, entitlements: Set[str], expires_at: float, status: str } }
        self.TTL_SECONDS = 60
    
    def check_access(self, org_id: str, token_version: int, service_slug: str) -> bool:
        """
        Validates if an Org has access to a Service.
        Strategy: Metadata-First (Hybrid Cache).
        1. Always fetch Org Status & Version (Fast PK Lookup).
        2. Check Revocation (Suspended).
        3. Check Cache vs DB Version (Consistency).
        4. Return Decision.
        """
        if not ENTITLEMENTS_ENFORCED:
            print(f"⚠️ [ENTITLEMENTS] Enforcement DISABLED (Allowing '{service_slug}' for {org_id})")
            return True

        if not org_id:
            return False
            
        # 1. Metadata Lookup (Fast, Real-time)
        try:
             # We use a lightweight session for metadata only
             db = SessionCore()
             # Query only what we need: status, entitlements_version
             # Note: SQLAlchemy might fetch full object, but it's by PK.
             org = db.query(models.Organization).filter(models.Organization.id == org_id).first()
             
             if not org:
                 db.close()
                 return False
                 
             db_status = getattr(org, "status", "Active")
             db_version = getattr(org, "entitlements_version", 1)
             db.close()
             
        except Exception as e:
            print(f"❌ [ENTITLEMENTS] Metadata Fetch Error: {e}")
            return False

        # 2. Hard Revoke Check (Immediate)
        if db_status == "Suspended":
             # print(f"⛔ [ENTITLEMENTS] Org {org_id} is SUSPENDED. Access Denied.")
             return False

        # 3. Cache Revalidation
        # If DB Version != Cache Version, our Cache is STALE. Refresh it.
        # We ignore Token Version for *Correctness* (Source of Truth is DB), 
        # but Token Version tells us what the Client *thinks* it has.
        # Ideally, we enforce DB Version.
        
        cached = self._cache.get(org_id)
        
        if not cached or cached["version"] != db_version:
             # MISS or STALE -> Refresh Entitlements
             return self._refresh_and_check(org_id, db_version, service_slug) # Use DB version
        
        # HIT (Cache Version == DB Version)
        return service_slug in cached["entitlements"]

    def _refresh_and_check(self, org_id: str, db_version: int, service_slug: str) -> bool:
        db = SessionCore()
        try:
            # 2. Fetch Active Entitlements
            ents = db.query(models.OrgEntitlement).filter(
                models.OrgEntitlement.org_id == org_id,
                models.OrgEntitlement.enabled == True
            ).all()
            
            active_slugs = {e.entitlement_key for e in ents}
            
            # 3. Update Cache
            self._cache[org_id] = {
                "version": db_version,
                "entitlements": active_slugs,
                # "status": org_status, # Status is checked real-time now
                "expires_at": time.time() + self.TTL_SECONDS
            }
            
            return service_slug in active_slugs
            
        except Exception as e:
            print(f"❌ [ENTITLEMENTS] DB Error: {e}")
            return False
        finally:
            db.close()
            
    def invalidate(self, org_id: str):
        if org_id in self._cache:
            del self._cache[org_id]

# Singleton Instance
entitlements_client = EntitlementsClient()

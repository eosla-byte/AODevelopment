
import sys
import os

# Path Setup
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)
    
from common.database import get_db, SessionCore 
from common.models import AccountUser, Organization, OrganizationUser

def inspect_user(email_fragment):
    db = SessionCore()
    try:
        print(f"--- Searching for user containing '{email_fragment}' ---")
        users = db.query(AccountUser).filter(AccountUser.email.contains(email_fragment)).all()
        
        for u in users:
            print(f"\nUser: {u.full_name} ({u.email})")
            print(f"ID: {u.id}")
            print(f"Role: {u.role}")
            print(f"Status: {u.status}")
            
            # Org Memberships
            memberships = db.query(OrganizationUser).filter(OrganizationUser.user_id == u.id).all()
            print(f"Organization Memberships ({len(memberships)}):")
            for m in memberships:
                org = db.query(Organization).filter(Organization.id == m.organization_id).first()
                org_name = org.name if org else "UNKNOWN"
                print(f"  - Org: {org_name} (ID: {m.organization_id}) | Role: {m.role}")
                
        if not users:
            print("No users found.")
            
    finally:
        db.close()

if __name__ == "__main__":
    inspect_user("@") # Dump all users basically, or filtering by common domain

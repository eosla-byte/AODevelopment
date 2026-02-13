from backend.services.finance.common.database import SessionExt
from backend.services.finance.common.models import BimOrganization, Base
from sqlalchemy import text

def list_orgs():
    db = SessionExt()
    try:
        # Check if table exists first (it should, as FK exists)
        orgs = db.query(BimOrganization).all()
        print(f"Found {len(orgs)} organizations:")
        for o in orgs:
            print(f"ID: {o.id}, Name: {o.name}")
        
        if not orgs:
            print("No organizations found. Attempting to create org_default...")
            try:
                new_org = BimOrganization(id="org_default", name="Organizacion Predeterminada")
                db.add(new_org)
                db.commit()
                print("Created org_default successfully.")
            except Exception as e:
                print(f"Failed to create org_default: {e}")
                db.rollback()
    except Exception as e:
        print(f"Error querying: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    list_orgs()

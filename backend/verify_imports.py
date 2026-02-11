import sys
import os

# Add backend and AODevelopment root to path
current = os.path.dirname(os.path.abspath(__file__))
root = os.path.abspath(os.path.join(current, "../"))

if current not in sys.path:
    sys.path.append(current)
if root not in sys.path:
    sys.path.append(root)

print("Testing Imports...")

try:
    from common.models import Project, Base
    print("✅ Global Models Import OK")
except Exception as e:
    print(f"❌ Global Models Import FAILED: {e}")
    sys.exit(1)

try:
    from common.auth_constants import ACCESS_COOKIE_NAME
    print("✅ Auth Constants Import OK")
except Exception as e:
    print(f"❌ Auth Constants Import FAILED: {e}")

try:
    from services.accounts import main as accounts_main
    print("✅ Accounts Service Import OK")
except Exception as e:
    print(f"❌ Accounts Service Import FAILED: {e}")

try:
    from services.bim import main as bim_main
    print("✅ BIM Service Import OK")
except Exception as e:
    print(f"❌ BIM Service Import FAILED: {e}")

try:
    from services.daily import main as daily_main
    print("✅ Daily Service Import OK")
except Exception as e:
    print(f"❌ Daily Service Import FAILED: {e}")

try:
    from common.models import Project
    from services.accounts.common import models as accounts_models
    from services.bim.common import models as bim_models
    from services.daily.common import models as daily_models

    print(f"Global Project: {Project}")
    print(f"Accounts Project: {accounts_models.Project}")
    print(f"BIM Project: {bim_models.Project}")

    # DECOUPLED ARCHITECTURE CHECK
    # Services now define their own Project class to avoid 'backend' dependency.
    # So we expect them to be DIFFERENT classes, but with SAME table name.
    
    if Project is not accounts_models.Project:
        print("ℹ️  Project Models are Decoupled (As Expected for Railway Fix)")
        
    if accounts_models.Project.__tablename__ == 'bim_projects':
        print("✅ Accounts Project maps to 'bim_projects'")
    else:
        print(f"❌ Accounts Project Key Mismatch: {accounts_models.Project.__tablename__}")
        
    if bim_models.Project.__tablename__ == 'bim_projects':
        print("✅ BIM Project maps to 'bim_projects'")
        
    if daily_models.Project.__tablename__ == 'bim_projects':
        print("✅ Daily Project maps to 'bim_projects'")

except Exception as e:
    print(f"❌ Verification FAILED: {e}")

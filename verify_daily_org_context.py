import requests
import uuid
import sys

# Configuration
BASE_URL = "http://localhost:8000" # Assuming Daily runs on 8000 or I need to check Procfile/main
# Actually Daily might be running on a different port if run locally via uvicorn.
# I will try to start the service first or assume it's offline and import code directly?
# Importing code directly is safer for unit testing without spinning up server.
# But I need to test specific Models and Database logic.

sys.path.append("a:/AO_DEVELOPMENT/AODevelopment/backend/services/daily")
sys.path.append("a:/AO_DEVELOPMENT/AODevelopment/backend")

from common import database, models
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Setup In-Memory DB for testing
TEST_DB_PATH = "./test_daily_orgs.db"
import os
if os.path.exists(TEST_DB_PATH):
    os.remove(TEST_DB_PATH)

TEST_DB = f"sqlite:///{TEST_DB_PATH}"
engine = create_engine(TEST_DB)
models.Base.metadata.create_all(engine)
SessionTest = sessionmaker(bind=engine)

# DEBUG: Check columns
print("Reflected Columns for DailyTeam:", models.DailyTeam.__table__.columns.keys())

# Monkey Patch database.SessionOps to use our Test DB
database.SessionOps = SessionTest

def verify_multi_tenancy():
    print("--- Verifying Multi-Tenancy ---")
    
    user_id = "user_test_1"
    org_a = str(uuid.uuid4())
    org_b = str(uuid.uuid4())
    
    print(f"User: {user_id}")
    print(f"Org A: {org_a}")
    print(f"Org B: {org_b}")

    # 0. Create Dummy User (Just in case FK matters)
    user = models.AccountUser(id=user_id, email="test@test.com", hashed_password="pw", role="Standard", services_access={})
    session = SessionTest()
    session.add(user)
    session.commit()
    session.close()
    
    try:
        # 1. Create Team in Org A
        team_a = database.create_daily_team("Team Alpha", user_id, organization_id=org_a)
        print(f"Created Team A: {team_a.name} (Org: {team_a.organization_id})")
        
        # 2. Create Team in Org B
        team_b = database.create_daily_team("Team Beta", user_id, organization_id=org_b)
        print(f"Created Team B: {team_b.name} (Org: {team_b.organization_id})")
    except Exception as e:
        print(f"CRITICAL FAILIURE: {e}")
        import traceback
        traceback.print_exc()
        return
    
    # 3. Create Team with No Org (Global/Personal)
    team_global = database.create_daily_team("Team Global", user_id, organization_id=None)
    print(f"Created Team Global: {team_global.name} (Org: {team_global.organization_id})")
    
    # 4. Verify Fetching for Org A
    print("\n[Test] Fetching for Org A...")
    teams_a = database.get_user_teams(user_id, organization_id=org_a)
    names_a = [t.name for t in teams_a]
    print(f"Teams found: {names_a}")
    
    if "Team Alpha" in names_a and "Team Beta" not in names_a:
        print("✅ Org A Isolation Passed")
    else:
        print("❌ Org A Isolation FAILED")
        
    # 5. Verify Fetching for Org B
    print("\n[Test] Fetching for Org B...")
    teams_b = database.get_user_teams(user_id, organization_id=org_b)
    names_b = [t.name for t in teams_b]
    print(f"Teams found: {names_b}")
    
    if "Team Beta" in names_b and "Team Alpha" not in names_b:
        print("✅ Org B Isolation Passed")
    else:
        print("❌ Org B Isolation FAILED")

    # 6. Verify Fetching Global (No Org)
    # The logic I implemented: 
    # if organization_id and t.organization_id != organization_id: continue
    # If organization_id is None, it returns ALL teams (Global + Orgs)? 
    # Let's check logic:
    # if organization_id (is None) -> logic doesn't filter.
    # So retrieving without Org ID returns EVERYTHING (Access All Areas / or Personal View).
    # This might be desired or not. For now, let's verify that behavior.
    print("\n[Test] Fetching without context (Global View)...")
    teams_all = database.get_user_teams(user_id, organization_id=None)
    names_all = [t.name for t in teams_all]
    print(f"Teams found: {names_all}")
    
    if "Team Alpha" in names_all and "Team Beta" in names_all and "Team Global" in names_all:
         print("✅ Global View checks out (Returns all)")
    else:
         print("❌ Global View Unexpected")

if __name__ == "__main__":
    verify_multi_tenancy()
    
    # Cleanup
    import os
    try:
        os.remove("./test_daily_orgs.db")
    except: pass

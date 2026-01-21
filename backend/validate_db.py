
import os
import sys
sys.path.append(os.getcwd())

import database
from database import get_projects, get_expenses_monthly, get_root_path, init_database

def test_db():
    print("Testing AO_Development Backend DB...")
    
    # 1. Config/Root
    root_path = get_root_path()
    print(f"Root Path: {root_path}")
    if not root_path:
        # Try finding one? Use current dir for testing
        print("Set root path to current dir for test")
        root_path = os.getcwd()

    # 2. Expenses
    print("\nTesting get_expenses_monthly...")
    try:
        data = get_expenses_monthly(root_path, 2024)
        print(f"Got {len(data)} months")
        for m in data:
            if m['total'] > 0:
                print(f"  Month {m['name']}: {m['total']}")
                for c in m['cards']:
                     print(f"    - {c['name']} ({c['amount']})")
    except Exception as e:
        print(f"ERROR get_expenses_monthly: {e}")
        import traceback
        traceback.print_exc()

    # 3. Projects
    print("\nTesting get_projects...")
    try:
        projs = get_projects(root_path)
        print(f"Found {len(projs)} projects")
    except Exception as e:
         print(f"ERROR get_projects: {e}")
         traceback.print_exc()

if __name__ == "__main__":
    test_db()

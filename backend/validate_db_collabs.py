
import os
import sys
sys.path.append(os.getcwd())

import database
from database import get_projects, get_expenses_monthly, get_root_path, init_database, get_collaborators

def test_db():
    print("Testing AO_Development Backend DB...")
    
    root_path = get_root_path()
    if not root_path:
        root_path = os.getcwd()

    # Test Collaborators
    print("\nTesting get_collaborators...")
    try:
        collabs = get_collaborators(root_path)
        print(f"Found {len(collabs)} collaborators")
        for c in collabs:
            base = c.base_salary
            bonus = c.bonus_incentive
            print(f"  - {c.name}: Base={base} ({type(base)}), Bonus={bonus} ({type(bonus)})")
            
            # Simulate main.py logic
            try:
                calc = base + bonus
            except Exception as ex:
                print(f"    CRASH in calculation: {ex}")
                
            # Simulate months logic
            try:
                months = 5 # dummy
                total = months * (base + bonus)
            except Exception as ex:
                print(f"    CRASH in total: {ex}")

    except Exception as e:
         print(f"ERROR get_collaborators: {e}")
         import traceback
         traceback.print_exc()

if __name__ == "__main__":
    test_db()

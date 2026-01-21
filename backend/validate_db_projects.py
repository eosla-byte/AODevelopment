
import os
import sys
sys.path.append(os.getcwd())

import database
from database import get_projects, get_root_path

def test_projects():
    print("Testing Projects...")
    
    root_path = get_root_path()
    if not root_path: root_path = os.getcwd()

    try:
        projs = get_projects(root_path)
        print(f"Found {len(projs)} projects")
        for p in projs:
            paid = p.paid_amount
            print(f"  - {p.name}: Status={p.status}, Paid={paid} ({type(paid)})")
            
            # Simulate main.py logic
            try:
                if not getattr(p, 'archived', False):
                    total = 0.0 + paid
            except Exception as ex:
                print(f"    CRASH in paid_amount: {ex}")

    except Exception as e:
         print(f"ERROR: {e}")
         import traceback
         traceback.print_exc()

if __name__ == "__main__":
    test_projects()

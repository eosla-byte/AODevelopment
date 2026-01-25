
import os
import sys

# Set up environment
sys.path.append(os.getcwd())

from database import get_projects, get_project_details

def debug_specific_project():
    print("--- Searching for Project with Saldo 88,500.00 ---")
    
    projects = get_projects()
    target_project = None
    
    for p in projects:
        try:
            print(f"Project: {p.name} (ID: {p.id})")
            print(f"  Amount: {p.amount}")
            print(f"  Paid: {p.paid_amount}")
            print(f"  Files Meta Keys: {p.files_meta.keys() if p.files_meta else 'None'}")
            
            full_p = get_project_details(p.id)
            print(f"  Files (Processed): {full_p.files.keys() if full_p.files else 'None'}")
            if full_p.files:
                 for cat, flist in full_p.files.items():
                     if flist:
                         print(f"    Category [{cat}]: {len(flist)} files")
                         for f in flist:
                             print(f"      - {f}")
            print("-" * 30)
            
        except Exception as e:
            print(f"Error checking project {p.id}: {e}")

if __name__ == "__main__":
    debug_specific_project()

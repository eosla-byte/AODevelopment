
import os
import sys
# Add current directory to path
sys.path.append(os.getcwd())

from database import get_projects, get_collaborators, get_project_stats_by_category, get_expenses_data, get_root_path

def test_db():
    print("Testing DB functions...")
    root_path = get_root_path()
    print(f"Root path: {root_path}")
    
    if not root_path:
        print("Root path not found")
        return

    print("Testing get_projects...")
    try:
        projects = get_projects(root_path)
        print(f"Found {len(projects)} projects")
        for p in projects:
            print(f"  - {p.name} ({p.status}) Paid: {p.paid_amount}")
    except Exception as e:
        print(f"ERROR in get_projects: {e}")
        import traceback
        traceback.print_exc()

    print("\nTesting get_collaborators...")
    try:
        collabs = get_collaborators(root_path)
        print(f"Found {len(collabs)} collaborators")
    except Exception as e:
        print(f"ERROR in get_collaborators: {e}")
        traceback.print_exc()

    print("\nTesting get_project_stats_by_category...")
    try:
        stats = get_project_stats_by_category(root_path)
        print(f"Stats: {stats}")
    except Exception as e:
        print(f"ERROR in get_project_stats_by_category: {e}")
        traceback.print_exc()

    print("\nTesting get_expenses_data...")
    try:
        expenses = get_expenses_data(root_path)
        print(f"Found {len(expenses)} expense columns")
    except Exception as e:
        print(f"ERROR in get_expenses_data: {e}")
        traceback.print_exc()

if __name__ == "__main__":
    test_db()

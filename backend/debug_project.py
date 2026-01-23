import sys
import os
# Add backend to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database import get_projects, get_project_details

print("--- PROJECTS DEBUG ---")
projects = get_projects()
print(f"Found {len(projects)} projects.")

if not projects:
    print("No projects found.")
    sys.exit(0)

# Try to get details for the first active project
target_id = projects[0].id
print(f"Attempting to get details for Project ID: {target_id}")

try:
    proj = get_project_details(target_id)
    print("SUCCESS: Retrieved project details.")
    print(f"Name: {proj.name}")
    print(f"Files Meta Type: {type(proj.files_meta)}")
    if proj.files_meta:
        print(f"Files Meta: {proj.files_meta}")
    
    # Check calculated fields
    print(f"Cat Totals: {proj.cat_totals}")

except Exception as e:
    print(f"ERROR: {e}")
    import traceback
    traceback.print_exc()

print("--- END DEBUG ---")

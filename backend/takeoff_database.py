
import json
import os

# "Separate Database" simulation (File System for now)
DB_PATH = "takeoff_storage_db"

def save_project_packages(project_id: str, packages_json_str: str):
    """Saves the raw JSON string of packages for a project."""
    if not os.path.exists(DB_PATH):
        os.makedirs(DB_PATH)
    
    # Sanitize project_id just in case
    safe_id = "".join([c for c in project_id if c.isalnum() or c in ('-','_')])
    if not safe_id: safe_id = "default_project"
    
    file_path = os.path.join(DB_PATH, f"{safe_id}.json")
    
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(packages_json_str)
    return True

def get_project_packages(project_id: str) -> str:
    """Returns the raw JSON string."""
    safe_id = "".join([c for c in project_id if c.isalnum() or c in ('-','_')])
    file_path = os.path.join(DB_PATH, f"{safe_id}.json")
    
    if os.path.exists(file_path):
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()
    return "[]"

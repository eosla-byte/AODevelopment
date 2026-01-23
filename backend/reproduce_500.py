
import os
import sys
from jinja2 import Environment, FileSystemLoader

# Add current directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database import get_project_details, get_total_collaborator_allocations, get_collaborators

def reproduce_render():
    project_id = "POR1" # Using the ID from the screenshot/previous logs
    
    print(f"Loading data for project {project_id}...")
    p = get_project_details(project_id)
    if not p:
        print("Project not found.")
        return

    collabs = get_collaborators()
    total_allocs = get_total_collaborator_allocations()

    # Setup Jinja env
    template_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "templates")
    env = Environment(loader=FileSystemLoader(template_dir))
    
    # helper for tojson
    import json
    def tojson(value):
        return json.dumps(value)
    env.filters['tojson'] = tojson

    print("Attempting to render project_detail.html...")
    try:
        template = env.get_template("project_detail.html")
        output = template.render(
            request={}, # Mock request
            p=p, 
            collaborators=collabs, 
            total_allocations=total_allocs,
            files=p.files # It seems the template uses 'files' variable directly in the loop? 
                          # Wait, lines 801: {% for f in files %} ??
                          # Let's check if 'files' is passed in main.py.
                          # main.py: "files": ... NO. main.py passes "p", "collaborators", "total_allocations".
                          # project_detail.html might access p.files? 
                          # Re-check line 801 in project_detail.html.
        )
        print("Render Successful! Length:", len(output))
    except Exception as e:
        print("\n!!! RENDER ERROR !!!")
        print(e)
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    reproduce_render()

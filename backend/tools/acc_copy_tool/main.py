import sys
import os

# Ensure we can import modules from current dir
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from copier import AccCopier

def print_menu(options, title="Select Option"):
    print(f"\n--- {title} ---")
    for i, opt in enumerate(options):
        print(f"{i+1}. {opt['name']}")
    return options

def select_option(options):
    while True:
        try:
            val = input("Selection (Number): ")
            idx = int(val) - 1
            if 0 <= idx < len(options):
                return options[idx]
        except:
            pass
        print("Invalid selection.")

def navigate_browser(copier, hub_id, project_id, current_folder_id, current_path="/"):
    while True:
        print(f"\n📂 Browsing: {current_path}")
        print("Actions: [S]elect This Folder | [B]ack | [Enter Number] to Enter Folder")
        
        if current_folder_id == "ROOT":
             sub_folders = copier.get_top_folders(hub_id, project_id)
             items = []
        else:
             sub_folders, items = copier.get_folder_contents(project_id, current_folder_id)
        
        # Display Folders
        for i, f in enumerate(sub_folders):
            print(f"{i+1}. 📁 {f['attributes']['name']}")
            
        # Display Files (Just for visual, not navigation)
        if items:
            print(f"   ({len(items)} files in this folder)")

        choice = input("Option: ").strip().lower()
        
        if choice == 's':
            return {"id": current_folder_id, "name": os.path.basename(current_path) or "Project Files", "attrs": {"attributes": {"name": os.path.basename(current_path)}}}
            
        if choice == 'b':
            return None # Go back logic handled by caller? Or stack?
            # Basic browsers are hard to implement stateless.
            # Simplified: We only support drilling Down.
            # To go back, user has to restart Nav.
            print("Cannot go back in this simple navigator. Restarting at root...")
            return "RESTART"
            
        try:
            idx = int(choice) - 1
            if 0 <= idx < len(sub_folders):
                # Recurse / Dive
                selected = sub_folders[idx]
                fname = selected["attributes"]["name"]
                
                # Check if user meant to SELECT this folder (Target) or ENTER it
                # Prompt: Enter or Select?
                # Actually, standard file picker: Single Click selects? Double click enters?
                # CLI: "Enter" dives. "Select" selects current context.
                # So if I want to select "Folder A" inside Root, I must enter Root? No that selects Root.
                # I must have a way to return the subfolder object.
                
                action = input(f"Selected '{fname}'. [1] Enter Folder | [2] Pick as Selection: ")
                if action == '2':
                    return selected
                elif action == '1':
                    # Recursive Call
                    res = navigate_browser(copier, hub_id, project_id, selected["id"], f"{current_path}{fname}/")
                    if res == "RESTART": return "RESTART"
                    if res: return res
            else:
                print("Invalid index.")
        except Exception as e:
            print(f"Invalid input: {e}")

def main():
    print("Welcome to ACC Batch Copy Tool")
    print("Initializing...")
    
    try:
        app = AccCopier()
        print("Connected with 2-legged Auth.")
    except Exception as e:
        print(f"Auth Failed: {e}")
        print("Check config.py credentials. Ensure Client ID has 'Custom Integration' access in ACC Admin.")
        return

    # 1. Select Hub
    hubs = app.get_hubs()
    if not hubs:
        print("No Hubs found. Check Permissions.")
        return
        
    hub = select_option(print_menu([{"name": h["attributes"]["name"], "id": h["id"]} for h in hubs], "Select Hub"))
    hub_id = hub["id"]
    
    # 2. Select Project
    projects = app.get_projects(hub_id)
    if not projects:
        print("No Projects found.")
        return
        
    proj = select_option(print_menu([{"name": p["attributes"]["name"], "id": p["id"]} for p in projects], "Select Project"))
    proj_id = proj["id"]
    
    print("\n--- SOURCE FOLDER SELECTION ---")
    source_folder = navigate_browser(app, hub_id, proj_id, "ROOT")
    if not source_folder or source_folder == "RESTART":
        print("Selection cancelled.")
        return
        
    print(f"\n✅ Selected Source: {source_folder['attributes']['name']} ({source_folder['id']})")
    
    print("\n--- TARGET PARENT FOLDER SELECTION ---")
    print("Where should the SOURCE folder be placed?")
    target_folder = navigate_browser(app, hub_id, proj_id, "ROOT")
    if not target_folder or target_folder == "RESTART": 
         # Handle restart or cancel
         pass
         
    # Handle Root Selection
    # If navigate_browser returns the specialized ROOT object, it might likely fail 'id' check if not careful.
    # get_top_folders returns folders. navigate_browser returns 'selected' which is a folder object.
    # BUT if they selected 'ROOT' context (choice 's' at top level):
    # 'id' is "ROOT". 
    # API requires a valid Folder ID to create children.
    # Top Folders (Project Files) has a real URN. 
    # Logic fix: We need the proper "Project Files" folder ID, not "ROOT".
    # get_top_folders returns usually "Project Files" and "Plans".
    # User should select "Project Files" (the folder itself), not the abstract Root.
    
    target_id = target_folder["id"]
    print(f"\n✅ Selected Target Parent: {target_folder['attributes']['name']} ({target_id})")
    
    # 3. Confirmation
    print(f"\nWARNING: This will recursively copy '{source_folder['attributes']['name']}' into '{target_folder['attributes']['name']}'.")
    confirm = input("Type 'YES' to proceed: ")
    
    if confirm == "YES":
        app.recursive_copy(proj_id, source_folder, target_id)
        print("\nDone!")
    else:
        print("Aborted.")

if __name__ == "__main__":
    main()

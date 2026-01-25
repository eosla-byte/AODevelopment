
import os
import sys

# Set up environment
sys.path.append(os.getcwd())

from database import update_project_file_meta, get_project_details, create_project, delete_project_file_meta

def test_upload_fix():
    print("--- Testing Upload Fix (Signature Mismatch) ---")
    
    # We will use "repro_test_proj" if it exists, or create it
    pid = "repro_test_proj"
    
    # Ensure project exists
    p = get_project_details(pid)
    if not p:
        create_project(name="Repro Project", custom_id=pid)
        print("Created test project.")
        
    print("Calling update_project_file_meta with 5 arguments (as main.py does)...")
    
    try:
        # Simulate main.py call: update_project_file_meta(project_id, category, file.filename, val, final_note)
        # Note: Previous version (with root_path) would take pid as root_path, cat as pid.
        # So it would search for project with id="Facturas" -> Fail.
        
        update_project_file_meta(
            pid,                 # pid
            "Facturas",          # cat
            "signature_test.pdf",# fname
            500.0,               # amt
            "Signature Test"     # note
        )
        print("Call completed without exception.")
        
        # Verify persistence
        p = get_project_details(pid)
        if p and p.files_meta and "Facturas" in p.files_meta and "signature_test.pdf" in p.files_meta["Facturas"]:
             print("  [SUCCESS] Metadata saved!")
             print(f"  Data: {p.files_meta['Facturas']['signature_test.pdf']}")
        else:
             print("  [FAIL] Metadata NOT saved.")
             
    except TypeError as e:
        print(f"  [FAIL] TypeError: {e} (Signature mismatch?)")
    except Exception as e:
        print(f"  [FAIL] Exception: {e}")

if __name__ == "__main__":
    test_upload_fix()

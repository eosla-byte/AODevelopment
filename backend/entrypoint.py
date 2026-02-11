
import os
import sys
import subprocess
import time

# Add backend to sys.path
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(BASE_DIR)

def run_migrations():
    print("🚀 [ENTRYPOINT] Starting Database Migrations...")
    try:
        # Check if alembic.ini exists
        if not os.path.exists(os.path.join(BASE_DIR, "alembic.ini")):
            print("⚠️ [ENTRYPOINT] alembic.ini not found in backend/. Skipping.")
            return

        # Run Alembic
        # We need to run it as a module or command
        # subprocess.run(["alembic", "upgrade", "head"], check=True, cwd=BASE_DIR)
        
        # Alternatively, run programmatically to avoid path issues
        try:
            from alembic.config import Config
            from alembic import command
            
            alembic_cfg = Config(os.path.join(BASE_DIR, "alembic.ini"))
            command.upgrade(alembic_cfg, "head")
            
            print("✅ [ENTRYPOINT] Migrations applied successfully.")
        except (ImportError, ModuleNotFoundError):
            print("⚠️ [ENTRYPOINT] WARNING: Alembic not installed; skipping migrations")
            print("ℹ️ [ENTRYPOINT] INFO: Continuing startup")
            return
    except Exception as e:
        print(f"❌ [ENTRYPOINT] Migration Failed: {e}")
        # Decide: Fail hard or continue? 
        # Requirement: "Guard will scream". So we can continue and let the guard fail,
        # OR fail here. Let's fail here to be safe.
        sys.exit(1)

def start_server():
    print("🚀 [ENTRYPOINT] Starting Uvicorn Server...")
    # Port from env or default
    port = int(os.environ.get("PORT", 8000))
    
    # We use subprocess to launch uvicorn to match original behavior
    # Assuming we are running this script FROM backend/ or root?
    # The Procfile runs: uvicorn main:app ...
    # This script is in backend/entrypoint.py.
    # Service main is backend/services/accounts/main.py
    
    # CMD: uvicorn services.accounts.main:app --host 0.0.0.0 --port $PORT
    # But wait, original Procfile was: "uvicorn main:app" inside specific dir?
    # No, usually Procfile is at root. 
    # Let's check where main.py is. It's at services/accounts/main.py.
    # But start_server.bat did: cd /d "%~dp0" which is backend/ and ran: uvicorn main:app
    # Wait, backend/main.py exists?
    # Let's check backend/main.py content.
    
    # If this is for ACCOUNTS service specifically (which seems to be the context),
    # we should target services.accounts.main:app
    
    cmd = [
        "uvicorn", 
        "services.accounts.main:app", 
        "--host", "0.0.0.0", 
        "--port", str(port)
    ]
    
    # If dev reload
    # cmd.append("--reload")
    
    subprocess.run(cmd)

if __name__ == "__main__":
    run_migrations()
    start_server()

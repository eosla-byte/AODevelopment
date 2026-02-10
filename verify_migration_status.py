
import sys
import os
import sqlalchemy
from sqlalchemy import create_engine, text

# Add backend to path
sys.path.append(os.path.join(os.getcwd(), 'backend'))

# Mock env setup
os.environ['BUILD_DB_URL'] = os.environ.get('BUILD_DB_URL', 'sqlite:///./build_dev.db')
# Don't mock others to fail if not found or default to sqlite in module

def check_db(name, url_env_var, module_path, check_table=None):
    print(f"\n🔍 Checking {name} Service...")
    
    try:
        import importlib
        mod = importlib.import_module(f"backend.{module_path}")
        
        url = getattr(mod, url_env_var, None)
        
        if not url:
            print(f"❌ {name}: {url_env_var} NOT FOUND in {module_path}")
            return False
            
        # Mask password
        safe_url = url.split("@")[-1] if "@" in url else "sqlite"
        if "sqlite" in url:
            safe_url = "SQLite Local"
            
        print(f"✅ FOUND configuration: {url_env_var}")
        print(f"   URL Host: {safe_url}")
        
        # Test Connection
        try:
            # Create engine
            engine = create_engine(url)
            with engine.connect() as conn:
                res = conn.execute(text("SELECT 1")).scalar()
                print(f"✅ CONNECTION Successful (Ping: {res})")
                
                if check_table:
                    # Check table via inspection or select
                    try:
                        count = conn.execute(text(f"SELECT count(*) FROM {check_table}")).scalar()
                        print(f"✅ TABLE CHECK: '{check_table}' exists with {count} rows")
                    except Exception as e:
                        print(f"⚠️ TABLE CHECK WARNING: '{check_table}' query failed: {e}")
                        # Could be empty/not created yet
                
        except Exception as e:
            print(f"❌ CONNECTION FAILED: {e}")
            return False
            
    except ImportError as e:
        print(f"❌ IMPORT FAILED: Could not import {module_path}: {e}")
        # Try finding file
        return False
    except Exception as e:
        print(f"❌ UNEXPECTED ERROR: {e}")
        return False
        
    return True

def main():
    print("🚀 Database Migration Verification")
    print("================================")
    
    # 1. Monolith (Shared) - Checks Plugin isolation
    check_db("Monolith (Plugin)", "PLUGIN_DB_URL", "common.database", "plugin_sessions")
    
    # 2. Monolith (Ops) - Checks Ops isolation
    check_db("Monolith (Ops)", "OPS_DB_URL", "common.database", "projects") # 'projects' table expected

    # 3. Plugin Microservice
    check_db("Plugin Service", "PLUGIN_DB_URL", "services.plugin.common.database", "plugin_sessions")

    # 4. Finance Microservice
    check_db("Finance Service", "OPS_DB_URL", "services.finance.common.database", "projects")

    # 5. Build Microservice (New)
    check_db("Build Service", "BUILD_DB_URL", "services.build.common.database", "build_projects")

if __name__ == "__main__":
    main()

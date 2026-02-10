
import sys
import os

def check_startup():
    print("--- Checking Accounts Service Startup ---")
    
    # 1. Add Accounts Service Path
    base_path = os.path.join(os.getcwd(), 'backend/services/accounts')
    if base_path not in sys.path:
        sys.path.insert(0, base_path)
    
    try:
        # 2. Import Main
        import main
        print("✅ Accounts Service Imported Successfully")
        print(f"   App Title: {main.app.title}")
        
        # 3. Check AccountUser availability in module
        try:
            au = main.AccountUser
            print(f"✅ AccountUser class is available: {au}")
        except AttributeError:
            print("❌ AccountUser class NOT available in main module (Import failed)")

    except ImportError as e:
        print(f"❌ Failed to import accounts.main: {e}")
    except NameError as e:
        print(f"❌ NameError: {e}")
    except Exception as e:
        print(f"❌ Unexpected Error: {e}")

if __name__ == "__main__":
    check_startup()


import os
import sys
# Add current directory to path
sys.path.append(os.getcwd())

from database import get_users, get_plugin_sessions, get_user_plugin_stats, get_root_path

def test_db_more():
    print("Testing More DB functions...")
    root_path = get_root_path()
    
    print("\nTesting get_users...")
    try:
        users = get_users(root_path)
        print(f"Found {len(users)} users")
        if users:
            print(f"First user: {users[0].email} / {users[0].role}")
            
            # Test Stats for first user
            print("Testing get_user_plugin_stats...")
            stats = get_user_plugin_stats(root_path, users[0].email)
            print(f"Stats: {stats}")
            
    except Exception as e:
        print(f"ERROR in get_users: {e}")
        import traceback
        traceback.print_exc()

    print("\nTesting get_plugin_sessions...")
    try:
        sessions = get_plugin_sessions(root_path)
        print(f"Found {len(sessions)} sessions")
    except Exception as e:
        print(f"ERROR in get_plugin_sessions: {e}")
        traceback.print_exc()

if __name__ == "__main__":
    test_db_more()

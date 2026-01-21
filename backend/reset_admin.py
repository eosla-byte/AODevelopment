from database import save_user, User
from auth_utils import get_password_hash
import datetime

def reset_admin():
    print("Resetting Admin User...")
    # 1. Create User Object
    admin = User(
        id="admin_01",
        name="Administrador",
        email="admin@ao.com",
        role="admin",
        is_active=True,
        hashed_password=get_password_hash("admin123")
    )
    
    # 2. Save (Upsert)
    save_user(None, admin)
    print("Admin user 'admin@ao.com' with password 'admin123' has been ensured.")

if __name__ == "__main__":
    reset_admin()

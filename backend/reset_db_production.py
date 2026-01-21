from database import Base, engine, SessionLocal, User, save_user
from auth_utils import get_password_hash
import models

def reset_db():
    print("WARNING: This will DROP ALL TABLES and DATA.")
    val = input("Type 'DELETE' to confirm: ")
    if val != "DELETE":
        print("Aborted.")
        return

    print("Dropping all tables...")
    Base.metadata.drop_all(bind=engine)
    
    print("Creating all tables...")
    Base.metadata.create_all(bind=engine)
    
    print("Creating Default Admin...")
    admin = User(
        id="admin_01",
        name="Administrador",
        email="admin@ao.com",
        role="admin",
        is_active=True,
        hashed_password=get_password_hash("admin123")
    )
    save_user(admin)
    print("Done. Admin created: admin@ao.com / admin123")

if __name__ == "__main__":
    reset_db()

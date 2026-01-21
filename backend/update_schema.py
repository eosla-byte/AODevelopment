from database import engine
import models

def update_schema():
    print("Creating missing tables (ExpenseColumn, ExpenseCard)...")
    models.Base.metadata.create_all(bind=engine)
    print("Done.")

if __name__ == "__main__":
    update_schema()

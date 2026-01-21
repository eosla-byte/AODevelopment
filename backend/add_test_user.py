
from database import get_users, save_user, User
from auth_utils import get_password_hash
import os
import json

# Setup Root Path manually since we might be outside app context or config might be unset if never run
CONFIG_FILE = "config.json"
root_path = "c:\\Users\\arqui\\.gemini\\antigravity\\scratch\\AO-Resources-1.0\\Local_DB"

# Check config content
if os.path.exists(CONFIG_FILE):
    with open(CONFIG_FILE, "r") as f:
        data = json.load(f)
        if "root_path" in data:
            root_path = data["root_path"]

print(f"Using Root Path: {root_path}")

# Ensure system dir exists
system_dir = os.path.join(root_path, "System")
if not os.path.exists(system_dir):
    os.makedirs(system_dir)

# Create User
email = "cliente@archipelago.com"
password = "admin"
hashed = get_password_hash(password)

new_user = User(
    id="test_client_01",
    name="Cliente Prueba",
    email=email,
    role="client",
    is_active=True,
    hashed_password=hashed,
    assigned_projects=[], # Empty for now
    permissions={"financials": True, "acc_viewer": True, "timeline": True}
)

users = get_users(root_path)
# Update if exists
updated = False
for i, u in enumerate(users):
    if u.email == email:
        users[i] = new_user
        updated = True
        break

if not updated:
    users.append(new_user)

# Save
# We have to reimplement save logic briefly or rely on database.py imports which we did
if save_user(root_path, new_user):
    print(f"Successfully created/updated user: {email} / {password}")
else:
    print("Failed to save user.")

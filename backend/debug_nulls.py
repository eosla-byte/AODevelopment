import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database import get_projects

print("--- CHECKING FOR NULLS ---")
projects = get_projects()
found_issue = False

for p in projects:
    print(f"Checking Project: {p.name} (ID: {p.id})")
    if p.amount is None:
        print(f"  [WARNING] 'amount' is None")
        found_issue = True
    if p.paid_amount is None:
        print(f"  [WARNING] 'paid_amount' is None")
        found_issue = True
    if p.square_meters is None:
        print(f"  [WARNING] 'square_meters' is None")
        found_issue = True
    if p.projected_profit_margin is None:
        print(f"  [WARNING] 'projected_profit_margin' is None")
        found_issue = True
    if p.real_profit_margin is None:
        print(f"  [WARNING] 'real_profit_margin' is None")
        found_issue = True

if not found_issue:
    print("SUCCESS: No None values found in critical numeric fields.")
else:
    print("FAILURE: Found None values which will crash the template.")

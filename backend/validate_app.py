
import sys
import os
try:
    from main import app
    print("Syntax OK")
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()

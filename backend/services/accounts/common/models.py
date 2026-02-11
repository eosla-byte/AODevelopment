import sys
import os

# PROXY TO GLOBAL MODELS
# This file ensures all services use the Single Source of Truth (common/models.py)
# We prioritize the ROOT common module over local/relative ones.

current_dir = os.path.dirname(os.path.abspath(__file__))
# Assumes structure: services/SERVICE/common/models.py -> .../backend/ (Root)
root_dir = os.path.abspath(os.path.join(current_dir, "../../../"))

if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

try:
    # This should now pick up backend/common/models.py (as common.models)
    from common.models import *
except ImportError as e:
    # If that fails, try explicit relative? No, stick to common.
    # Print error to help debug in logs
    print(f"CRITICAL: Could not import common.models in proxy. Path: {sys.path}")
    raise e

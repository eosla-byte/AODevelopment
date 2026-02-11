import sys
import os

# PROXY TO GLOBAL MODELS
# This file ensures all services use the Single Source of Truth (backend/common/models.py)

try:
    from backend.common.models import *
except ImportError:
    # Fallback for environments where 'backend' is not in path
    # Attempt to find root (AODevelopment)
    current = os.path.dirname(os.path.abspath(__file__))
    # .../services/SERVICE/common/models.py -> up 3 levels to AODevelopment
    root = os.path.abspath(os.path.join(current, "../../../"))
    if root not in sys.path:
        sys.path.append(root)
    
    try:
        from backend.common.models import *
    except ImportError:
        # Last resort: Try simple common.models if we are inside backend?
        # No, we want distinct global models.
        raise ImportError("Could not import backend.common.models. Ensure AODevelopment root is in sys.path.")

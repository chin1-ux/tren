import os
import sys

# Ensure project root is on PYTHONPATH so backend modules can be imported
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from backend.api import app

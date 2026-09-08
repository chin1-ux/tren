import os
import sys

# Ensure project root and backend are on PYTHONPATH
root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.append(root_dir)
sys.path.append(os.path.join(root_dir, 'backend'))

from backend.api import app
from mangum import Mangum

handler = Mangum(app, lifespan="off")



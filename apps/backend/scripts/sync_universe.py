import sys
import os
import logging
from pathlib import Path

# Ensure the root of the backend is in sys.path so we can import 'app'
# In Docker, this is usually /app
backend_root = Path(__file__).parent.parent
if str(backend_root) not in sys.path:
    sys.path.append(str(backend_root))

from app.universe.sync import sync_universe

if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    sync_universe()

import sys
import os
from pathlib import Path

# Add apps/backend to sys.path
backend_path = Path(__file__).parent.parent / "apps" / "backend"
sys.path.append(str(backend_path))

from app.universe.sync import sync_universe

if __name__ == "__main__":
    import logging
    logging.basicConfig(level=logging.INFO)
    sync_universe()

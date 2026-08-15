import os
import sys
import shutil
from pathlib import Path
import argparse

def cleanup(apply=False):
    root = Path(__file__).parent.parent

    candidates = [
        "apps/backend/debug_sync.py",
        "apps/backend/debug_mirror.py",
        "apps/backend/ta.tar.gz",
        "apps/backend/pandas-ta.tar.gz",
        "apps/backend/requirements.txt.bak"
    ]

    print(f"Cleanup mode: {'APPLY' if apply else 'DRY RUN'}")

    for c in candidates:
        path = root / c
        if path.exists():
            if apply:
                print(f"Deleting {c}...")
                path.unlink()
            else:
                print(f"[DRY RUN] Would delete {c}")

    # Cleanup __pycache__
    for p in list(root.rglob("__pycache__")):
        if apply:
            print(f"Removing {p}...")
            shutil.rmtree(p)
        else:
            print(f"[DRY RUN] Would remove {p}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true", help="Actually delete files")
    args = parser.parse_args()
    cleanup(apply=args.apply)

import os
from pathlib import Path

def audit():
    root = Path(__file__).parent.parent
    print(f"Auditing repository: {root}")

    candidates = [
        "apps/backend/debug_sync.py",
        "apps/backend/debug_mirror.py",
        "apps/backend/ta.tar.gz",
        "apps/backend/pandas-ta.tar.gz",
        "apps/backend/requirements.txt.bak"
    ]

    print("\n--- Cleanup Candidates ---")
    for c in candidates:
        path = root / c
        if path.exists():
            size = path.stat().st_size
            print(f"[CANDIDATE] {c} ({size} bytes)")
        else:
            print(f"[NOT FOUND] {c}")

    # Check for __pycache__
    print("\n--- Temporary Folders ---")
    for p in root.rglob("__pycache__"):
        print(f"[TEMP] {p.relative_to(root)}")

if __name__ == "__main__":
    audit()

import os
import re
import sys

# Konfigurasi Pemetaan Simbol (Enforce Otak & Mesin Architecture)
# Jika simbol di kiri ditemukan, pastikan diimpor dari jalur di kanan.
SYMBOL_MAP = {
    "BullishDivergenceStrategy": "app.strategies.technical_logic",
    "DoubleBullishDivergenceStrategy": "app.strategies.technical_logic",
    "CorrectionStrategy": "app.strategies.technical_logic",
    "HiddenBullishDivergenceStrategy": "app.strategies.technical_logic",
    "IDXCalendar": "app.scanner.scanner_core",
    "is_idx_market_open": "app.scanner.scanner_core",
    "ScannerEngine": "app.scanner.scanner_core",
    "is_ara": "app.core.market_utils",
    "is_arb": "app.core.market_utils",
    "Fees": "app.core.market_utils",
    "round_to_tick": "app.scanner.scanner_core",
    "PivotDetector": "app.scanner.scanner_core",
    "MovementClassifier": "app.scanner.scanner_core"
}

PROJECT_ROOT = os.path.join(os.path.dirname(__file__), "..", "apps", "backend")

def fix_imports_in_file(file_path):
    if not file_path.endswith(".py"): return

    # Jangan ubah file inti (Otak & Mesin) sesuai instruksi user
    if "technical_logic.py" in file_path or "scanner_core.py" in file_path:
        return

    with open(file_path, "r") as f:
        content = f.read()

    new_content = content
    modified = False

    for symbol, correct_path in SYMBOL_MAP.items():
        # Cari pola: from ... import ... symbol
        # Jika ditemukan impor yang SALAH untuk simbol ini, perbaiki.
        pattern = rf"from ([\w\.]+) import (.*{symbol}.*)"
        matches = re.finditer(pattern, new_content)

        for match in matches:
            current_path = match.group(1)
            imports = match.group(2)

            if current_path != correct_path:
                # Cek apakah simbol benar-benar ada di baris itu
                if symbol in imports:
                    old_line = match.group(0)
                    new_line = f"from {correct_path} import {imports}"
                    new_content = new_content.replace(old_line, new_line)
                    modified = True

    if modified:
        with open(file_path, "w") as f:
            f.write(new_content)
        print(f"✅ AUTO-FIXED imports in: {os.path.relpath(file_path, PROJECT_ROOT)}")

def scan_and_fix():
    for root, _, files in os.walk(PROJECT_ROOT):
        for file in files:
            if file.endswith(".py"):
                fix_imports_in_file(os.path.join(root, file))

if __name__ == "__main__":
    # Jalankan sekali saat startup
    scan_and_fix()
    print("🚀 Auto-Fixer is watching for import inconsistencies...")

# Repository Cleanup Plan - Screener Project

## 1. Candidate Files for Deletion

| File Path | Status | Reason |
|---|---|---|
| `apps/backend/debug_sync.py` | UNUSED | Temporary debug script. |
| `apps/backend/debug_mirror.py` | UNUSED | Temporary debug script. |
| `apps/backend/ta.tar.gz` | LEGACY | Artifact. |
| `apps/backend/pandas-ta.tar.gz` | LEGACY | Artifact. |
| `apps/backend/requirements.txt.bak` | UNUSED | Backup file. |

## 2. Directory Audit

| Directory | Status | Action |
|---|---|---|
| `hermes-idx-main/` | USED_AS_REF | Keep as methodology reference, but do not import directly into Screener production if possible (copy methodology to Screener). |
| `backtests/` | ACTIVE | Keep for storage of backtest reports. |
| `data/` | ACTIVE | Keep for local datasets. |

## 3. Protocol

1. **Audit**: Confirm no hidden dependencies.
2. **Dry Run**: List files to be deleted.
3. **Commit**: Git checkpoint before deletion.
4. **Delete**: Physically remove files.
5. **Verify**: Run tests and application.

## 4. Automation

- `scripts/audit_repository.py` will be created to automate Step 1.
- `scripts/cleanup_repository.py` will be created to automate Step 4 (with `--dry-run` and `--apply`).

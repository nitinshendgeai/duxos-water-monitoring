#!/usr/bin/env python3
"""One-time data migration: Google Sheets Excel export -> PostgreSQL.

Usage:
    python scripts/migrate_excel.py --file "/path/to/export.xlsx" [--dry-run]

Reads the four sheets the live app actually uses (Meter_Readings,
Tank_Status, Att_Staff, Att_Attendance) — Att_Config and Staff_Directory
are intentionally skipped: Att_Config had zero saved rows in the source
data (the app is still running on hardcoded defaults, which the backend
already falls back to), and Staff_Directory is empty and unreferenced by
any code path.

Safe to re-run: every insert is checked against the same natural key the
database enforces uniqueness on (created_at for readings, staff id,
(staff_id, occurred_at) for attendance events), so running this twice
against the same file reports the second run as all-skipped, not
duplicated rows.

Historical Date/Time columns in Meter_Readings/Tank_Status are imported
as-is (they're real typed Date/Time cells from the sheet, not the
locale-formatted display strings the live API now derives from the
server clock for *new* submissions going forward).

The actual per-sheet validation/import rules live in app/migration.py,
shared with the one-time admin HTTP import endpoint used during the
Railway cutover (see app/routers/admin_import.py).
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import openpyxl

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.database import SessionLocal  # noqa: E402
from app.migration import run_migration  # noqa: E402


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--file", required=True, help="Path to the Excel export")
    parser.add_argument(
        "--dry-run", action="store_true", help="Validate only, write nothing"
    )
    args = parser.parse_args()

    path = Path(args.file)
    if not path.exists():
        print(f"File not found: {path}", file=sys.stderr)
        sys.exit(1)

    wb = openpyxl.load_workbook(path, data_only=True)
    db = SessionLocal()
    try:
        reports = run_migration(db, wb, args.dry_run)
    finally:
        db.close()

    print("=" * 70)
    print(f"MIGRATION REPORT{'  (DRY RUN — nothing written)' if args.dry_run else ''}")
    print("=" * 70)
    total_imported = total_skipped = total_failed = 0
    for r in reports:
        d = r.to_dict()
        total_imported += d["imported"]
        total_skipped += d["skipped_duplicate"]
        total_failed += d["failed_count"]
        print(
            f"\n{d['sheet']}: imported={d['imported']} "
            f"skipped_duplicate={d['skipped_duplicate']} failed={d['failed_count']}"
        )
        for f in d["failed"]:
            print(f"    row {f['row']}: {f['reason']}")

    print("\n" + "-" * 70)
    print(
        f"TOTAL: imported={total_imported} skipped_duplicate={total_skipped} failed={total_failed}"
    )
    print("-" * 70)

    if total_failed:
        sys.exit(1)


if __name__ == "__main__":
    main()

"""
Standalone script to fetch external signals (weather, AQI) and store them.

Designed to be run by GitHub Actions cron, local scheduler, or manually.
No FastAPI dependency — connects directly to the database.

Usage:
    python fetch_external_signals.py
"""

import sys
from datetime import datetime, timezone

from database.session import SessionLocal
from app.services.external_data_service import fetch_and_store_external_signals


def main() -> int:
    print(f"[{datetime.now(timezone.utc).isoformat()}] Starting external signal ingestion...")

    db = SessionLocal()
    try:
        result = fetch_and_store_external_signals(db)
    except Exception as exc:
        print(f"FATAL: {exc}")
        db.close()
        return 1
    finally:
        db.close()

    print(f"  hospitals_total : {result['hospitals_total']}")
    print(f"  processed       : {result['processed']}")
    print(f"  failed          : {result['failed']}")
    print(f"  upserted        : {result['upserted']}")

    if result["failed"] > 0:
        print(f"WARNING: {result['failed']} hospital(s) failed to fetch signals")

    if result["upserted"] == 0 and result["hospitals_total"] > 0:
        print("WARNING: No rows upserted despite hospitals existing — check API connectivity")
        return 1

    print(f"[{datetime.now(timezone.utc).isoformat()}] Done.")
    return 0


if __name__ == "__main__":
    sys.exit(main())


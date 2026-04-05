#!/usr/bin/env python
"""Ingestion CLI — dispatches batch_index_act Celery tasks for one or all acts.

Usage (from repo root, outside container):
    python scripts/ingest.py --act all

Usage (inside backend/celery container, where app is installed):
    python scripts/ingest.py --act all
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# When running outside a container (e.g. local dev), add backend/ to path.
# When running inside the container the package is already installed — the
# insert is a no-op because Python will find the installed package first.
_backend_path = str(Path(__file__).resolve().parent.parent / "backend")
if _backend_path not in sys.path:
    sys.path.insert(0, _backend_path)

from app.ingestion.loader import list_available_acts  # noqa: E402
from app.workers.batch_index_task import batch_index_act  # noqa: E402


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Dispatch LexGrid ingestion tasks via Celery."
    )
    parser.add_argument(
        "--act",
        default="all",
        help=(
            "Act code(s) to index. Pass 'all' (default) or a comma-separated list "
            "of act codes, e.g. --act ipc,crpc"
        ),
    )
    return parser.parse_args()


def main() -> None:
    args = _parse_args()

    if args.act.strip().lower() == "all":
        act_codes = list_available_acts()
        print(f"Discovered {len(act_codes)} act(s): {', '.join(act_codes)}")
    else:
        act_codes = [code.strip() for code in args.act.split(",") if code.strip()]

    if not act_codes:
        print("No act codes resolved — nothing to dispatch.", file=sys.stderr)
        sys.exit(1)

    for act_code in act_codes:
        batch_index_act.delay(act_code)
        print(f"Dispatched {act_code}")

    print(
        "\nAll tasks dispatched. Monitor with:\n"
        "  celery -A app.workers.celery_app flower"
    )


if __name__ == "__main__":
    main()

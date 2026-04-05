"""Streaming watcher — polls legal-acts/ for modified JSON files."""

from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncGenerator
from pathlib import Path

STATE_FILE: Path = Path(".embedding_state.json")


def load_state() -> dict[str, float]:
    """Load {path: mtime} map from the state file, or empty dict."""
    if not STATE_FILE.exists():
        return {}
    try:
        return json.loads(STATE_FILE.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}


def save_state(state: dict[str, float]) -> None:
    """Persist the {path: mtime} map to disk."""
    STATE_FILE.write_text(json.dumps(state, indent=2), encoding="utf-8")


async def watch_for_updates(
    legal_acts_dir: Path,
    poll_interval: float = 30.0,
) -> AsyncGenerator[list[Path], None]:
    """Yield lists of JSON paths modified since the last poll.

    Compares each file's mtime against a persisted state file. Yields
    a (possibly empty) batch every *poll_interval* seconds.

    Args:
        legal_acts_dir: Root directory to scan recursively for *.json files.
        poll_interval: Seconds between scans (default 30).
    """
    state = load_state()

    while True:
        changed: list[Path] = []

        for path in sorted(legal_acts_dir.rglob("*.json")):
            key = str(path)
            mtime = path.stat().st_mtime
            if state.get(key) != mtime:
                changed.append(path)
                state[key] = mtime

        if changed:
            save_state(state)
            yield changed

        await asyncio.sleep(poll_interval)

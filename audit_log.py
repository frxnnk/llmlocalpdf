"""Append-only audit log with hash-chain verification."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from model_registry import compute_sha256


def _canonical_json(event: dict[str, Any]) -> bytes:
    payload = {key: value for key, value in event.items() if key != "event_hash"}
    return json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def compute_event_hash(event: dict[str, Any]) -> str:
    return hashlib.sha256(_canonical_json(event)).hexdigest()


def read_events(log_path: Path) -> list[dict[str, Any]]:
    if not log_path.exists():
        return []

    events = []
    with open(log_path, encoding="utf-8") as f:
        for line in f:
            stripped = line.strip()
            if stripped:
                events.append(json.loads(stripped))
    return events


def append_event(log_path: Path, event: dict[str, Any]) -> dict[str, Any]:
    existing_events = read_events(log_path)
    prev_hash = existing_events[-1]["event_hash"] if existing_events else None

    event_to_write = dict(event)
    event_to_write.setdefault("timestamp", datetime.now(timezone.utc).isoformat())
    event_to_write["prev_hash"] = prev_hash
    event_to_write["event_hash"] = compute_event_hash(event_to_write)

    log_path.parent.mkdir(parents=True, exist_ok=True)
    with open(log_path, "a", encoding="utf-8") as f:
        f.write(json.dumps(event_to_write, ensure_ascii=False, sort_keys=True) + "\n")

    return event_to_write


def append_pdf_processed_event(
    log_path: Path,
    source_sha256: str,
    output_path: Path,
    timestamp: str | None = None,
) -> dict[str, Any]:
    event = {
        "event": "pdf_processed",
        "source_sha256": source_sha256,
        "output_sha256": compute_sha256(output_path),
    }
    if timestamp is not None:
        event["timestamp"] = timestamp
    return append_event(log_path, event)


def verify_log_chain(log_path: Path) -> list[str]:
    errors = []
    previous_hash = None

    for line_number, event in enumerate(read_events(log_path), start=1):
        if event.get("prev_hash") != previous_hash:
            errors.append(f"prev_hash mismatch at line {line_number}")

        expected_hash = compute_event_hash(event)
        if event.get("event_hash") != expected_hash:
            errors.append(f"event_hash mismatch at line {line_number}")

        previous_hash = event.get("event_hash")

    return errors

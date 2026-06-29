"""Comparador deterministico para fixtures golden de extraccion."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def load_json(path: Path) -> dict[str, Any]:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def flatten_json(value: Any, prefix: str = "") -> dict[str, Any]:
    if isinstance(value, dict):
        flattened: dict[str, Any] = {}
        for key in sorted(value):
            path = f"{prefix}.{key}" if prefix else str(key)
            flattened.update(flatten_json(value[key], path))
        return flattened

    if isinstance(value, list):
        flattened = {}
        for index, item in enumerate(value):
            path = f"{prefix}[{index}]"
            flattened.update(flatten_json(item, path))
        return flattened

    return {prefix: value}


def compare_result(actual: dict[str, Any], expected: dict[str, Any]) -> dict[str, Any]:
    expected_fields = flatten_json(expected)
    actual_fields = flatten_json(actual)

    missing_fields = sorted(
        path for path in expected_fields if path not in actual_fields
    )
    mismatches = [
        {
            "path": path,
            "expected": expected_fields[path],
            "actual": actual_fields[path],
        }
        for path in sorted(expected_fields)
        if path in actual_fields and actual_fields[path] != expected_fields[path]
    ]
    matched = sum(
        1
        for path, expected_value in expected_fields.items()
        if path in actual_fields and actual_fields[path] == expected_value
    )
    total = len(expected_fields)
    score = round(matched / total, 6) if total else 1.0

    return {
        "passed": not missing_fields and not mismatches,
        "score": score,
        "matched": matched,
        "total": total,
        "missing_fields": missing_fields,
        "mismatches": mismatches,
    }


def summarize_report(report: dict[str, Any]) -> str:
    missing = ",".join(report["missing_fields"]) or "-"
    mismatch_paths = ",".join(item["path"] for item in report["mismatches"]) or "-"
    return (
        f"score={report['score']:.6f}; "
        f"matched={report['matched']}/{report['total']}; "
        f"passed={str(report['passed']).lower()}; "
        f"missing={missing}; "
        f"mismatch={mismatch_paths}"
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Compare extraction JSON to a golden fixture")
    parser.add_argument("--actual", required=True, type=Path)
    parser.add_argument("--expected", required=True, type=Path)
    args = parser.parse_args()

    report = compare_result(load_json(args.actual), load_json(args.expected))
    print(summarize_report(report))
    if not report["passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()

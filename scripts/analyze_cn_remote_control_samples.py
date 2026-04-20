#!/usr/bin/env python3
from __future__ import annotations

import argparse
import importlib.util
import json
import statistics
import sys

from collections import Counter
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
SCRIPT_ROOT = ROOT / "scripts"
DEFAULT_SAMPLE_DIR = ROOT / "artifacts" / "remote_control_samples"


def load_script_module(module_name: str, script_name: str):
    if module_name in sys.modules:
        return sys.modules[module_name]

    spec = importlib.util.spec_from_file_location(
        module_name,
        SCRIPT_ROOT / script_name,
    )
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


replay_module = load_script_module(
    "replay_cn_remote_control_from_logcat",
    "replay_cn_remote_control_from_logcat.py",
)
compare_module = load_script_module(
    "compare_cn_remote_control_signature",
    "compare_cn_remote_control_signature.py",
)


def redact(value: str | None, head: int = 12, tail: int = 10) -> str:
    if not value:
        return "<empty>"
    if len(value) <= head + tail:
        return "*" * len(value)
    return f"{value[:head]}...{value[-tail:]}"


def _redact_header_value(header_name: str, value: str) -> str:
    if header_name in {"authorization", "x-vehicle-identifier", "x-signature"}:
        return redact(value)
    return value


def _load_sample_payload(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _collect_sample_paths(sample_dir: Path, explicit_paths: list[str]) -> list[Path]:
    if explicit_paths:
        return [Path(path) for path in explicit_paths]
    return sorted(sample_dir.glob("*.json"))


def classify_header_values(sample_payloads: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    header_keys = sorted(
        {
            key
            for payload in sample_payloads
            for key in replay_module.captured_request_from_dict(payload).headers.keys()
        }
    )
    stable: dict[str, Any] = {}
    variable: dict[str, list[str]] = {}

    for key in header_keys:
        values = [
            replay_module.captured_request_from_dict(payload).headers.get(key, "<missing>")
            for payload in sample_payloads
        ]
        unique_values = list(dict.fromkeys(values))
        if len(unique_values) == 1:
            stable[key] = unique_values[0]
        else:
            variable[key] = unique_values

    return {"stable": stable, "variable": variable}


def analyze_header_order(sample_payloads: list[dict[str, Any]]) -> dict[str, Any]:
    orders = [
        tuple(replay_module.captured_request_from_dict(payload).header_order)
        for payload in sample_payloads
    ]
    distinct_orders = list(dict.fromkeys(orders))
    return {
        "consistent": len(distinct_orders) <= 1,
        "distinct_count": len(distinct_orders),
        "common_order": list(distinct_orders[0]) if distinct_orders else [],
    }


def analyze_nonce_and_timestamp(sample_payloads: list[dict[str, Any]]) -> dict[str, Any]:
    nonces = []
    timestamps = []
    for payload in sample_payloads:
        captured = replay_module.captured_request_from_dict(payload)
        nonce = captured.headers.get("x-api-signature-nonce")
        if nonce:
            nonces.append(nonce)
        timestamp = captured.headers.get("x-timestamp")
        if timestamp and timestamp.isdigit():
            timestamps.append(int(timestamp))

    sorted_timestamps = sorted(timestamps)
    deltas = [
        current - previous
        for previous, current in zip(sorted_timestamps, sorted_timestamps[1:])
    ]
    return {
        "sample_count": len(sample_payloads),
        "unique_nonce_count": len(set(nonces)),
        "duplicate_nonces": [nonce for nonce, count in Counter(nonces).items() if count > 1],
        "timestamp_count": len(sorted_timestamps),
        "timestamp_min": min(sorted_timestamps) if sorted_timestamps else None,
        "timestamp_max": max(sorted_timestamps) if sorted_timestamps else None,
        "timestamp_deltas": {
            "min": min(deltas) if deltas else None,
            "max": max(deltas) if deltas else None,
            "avg": statistics.mean(deltas) if deltas else None,
        },
    }


def summarize_candidate_matches(sample_payloads: list[dict[str, Any]]) -> dict[str, int]:
    counts: Counter[str] = Counter()
    for payload in sample_payloads:
        captured = replay_module.captured_request_from_dict(payload)
        for comparison in compare_module.build_signature_comparisons(captured):
            if comparison["matched"]:
                counts[comparison["variant"]] += 1

    return dict(sorted(counts.items()))


def _print_header_report(classification: dict[str, dict[str, Any]]) -> None:
    stable = classification["stable"]
    variable = classification["variable"]

    print("Stable headers:")
    if not stable:
        print("  <none>")
    else:
        for key, value in stable.items():
            print(f"  {key}: {_redact_header_value(key, str(value))}")

    print("\nVariable headers:")
    if not variable:
        print("  <none>")
    else:
        for key, values in variable.items():
            rendered_values = ", ".join(
                _redact_header_value(key, str(value))
                for value in values[:4]
            )
            suffix = "" if len(values) <= 4 else ", ..."
            print(f"  {key}: {rendered_values}{suffix}")


def _print_order_report(order_info: dict[str, Any]) -> None:
    print("\nHeader order analysis:")
    if order_info["consistent"]:
        print("  Header order is identical across all samples.")
    else:
        print(
            "  Header order varies across samples. "
            f"Distinct orders: {order_info['distinct_count']}"
        )
    if order_info["common_order"]:
        print("  Reference order:")
        print("  " + " -> ".join(order_info["common_order"]))


def _print_nonce_timestamp_report(report: dict[str, Any]) -> None:
    print("\nNonce / timestamp analysis:")
    print(f"  Samples: {report['sample_count']}")
    print(f"  Unique nonces: {report['unique_nonce_count']}")
    if report["duplicate_nonces"]:
        print(
            "  Duplicate nonces: "
            + ", ".join(report["duplicate_nonces"])
        )
    if report["timestamp_count"]:
        print(
            "  Timestamp range: "
            f"{report['timestamp_min']} -> {report['timestamp_max']}"
        )
        deltas = report["timestamp_deltas"]
        if deltas["min"] is not None:
            print(
                "  Timestamp deltas (ms): "
                f"min={deltas['min']} avg={deltas['avg']:.2f} max={deltas['max']}"
            )


def _print_match_report(match_counts: dict[str, int], sample_count: int) -> None:
    print("\nCandidate variant matches:")
    if not match_counts:
        print(
            "  No current candidate variant matched any captured sample. "
            "That is consistent with a protected signer path."
        )
        return

    for variant, count in match_counts.items():
        print(f"  {variant}: {count}/{sample_count}")


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Analyze archived mainland-China remoteControl/control samples to "
            "highlight stable fields, changing fields, header order, and "
            "timestamp/nonce patterns."
        )
    )
    parser.add_argument(
        "sample_paths",
        nargs="*",
        help="Optional specific archived sample JSON files to analyze.",
    )
    parser.add_argument(
        "--sample-dir",
        default=str(DEFAULT_SAMPLE_DIR),
        help="Directory containing archived sample JSON files when explicit paths are not provided.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print the full analysis result as JSON.",
    )
    args = parser.parse_args()

    sample_paths = _collect_sample_paths(Path(args.sample_dir), args.sample_paths)
    if not sample_paths:
        raise SystemExit("No archived sample JSON files found to analyze.")

    sample_payloads = [_load_sample_payload(path) for path in sample_paths]
    classification = classify_header_values(sample_payloads)
    order_info = analyze_header_order(sample_payloads)
    nonce_timestamp = analyze_nonce_and_timestamp(sample_payloads)
    match_counts = summarize_candidate_matches(sample_payloads)

    result = {
        "sample_count": len(sample_payloads),
        "sample_paths": [str(path) for path in sample_paths],
        "header_values": classification,
        "header_order": order_info,
        "nonce_timestamp": nonce_timestamp,
        "candidate_matches": match_counts,
    }

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0

    print(f"Analyzed samples: {len(sample_payloads)}")
    _print_header_report(classification)
    _print_order_report(order_info)
    _print_nonce_timestamp_report(nonce_timestamp)
    _print_match_report(match_counts, len(sample_payloads))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

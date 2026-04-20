#!/usr/bin/env python3
from __future__ import annotations

import argparse
import importlib.util
import json
import sys

from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT_ROOT = ROOT / "scripts"
DEFAULT_OUTPUT_DIR = ROOT / "artifacts" / "remote_control_samples"


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


def build_archive_payload(
    captured,
    *,
    label: str | None,
    serial: str | None,
    watch: bool,
) -> dict:
    return {
        "schema_version": 1,
        "captured_at": datetime.now().isoformat(timespec="seconds"),
        "target_url": replay_module.TARGET_URL,
        "source": {
            "watch": watch,
            "serial": serial,
            "label": label or "",
        },
        "request": replay_module.captured_request_to_dict(captured),
    }


def build_archive_filename(captured, label: str | None) -> str:
    timestamp = captured.headers.get("x-timestamp", "unknown")
    nonce = captured.headers.get("x-api-signature-nonce", "no-nonce").replace("-", "")
    prefix = label.strip().replace(" ", "-") if label else "sample"
    return f"{prefix}-{timestamp}-{nonce[:8]}.json"


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Capture a mainland-China remoteControl/control request from logcat "
            "and archive it as JSON for later comparison."
        )
    )
    parser.add_argument(
        "--watch",
        action="store_true",
        help="Clear logcat and wait for the next remoteControl/control request instead of using the latest cached one.",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=120,
        help="Seconds to wait when --watch is enabled.",
    )
    parser.add_argument(
        "--serial",
        help="Optional adb device serial to use when multiple devices are connected.",
    )
    parser.add_argument(
        "--label",
        help="Optional short label to include in the archive filename.",
    )
    parser.add_argument(
        "--output-dir",
        default=str(DEFAULT_OUTPUT_DIR),
        help="Directory where captured samples should be saved.",
    )
    args = parser.parse_args()

    captured = replay_module.capture_request(
        watch=args.watch,
        timeout=args.timeout,
        serial=args.serial,
    )
    payload = build_archive_payload(
        captured,
        label=args.label,
        serial=args.serial,
        watch=args.watch,
    )

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / build_archive_filename(captured, args.label)
    output_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print(f"Archived sample: {output_path}")
    print(
        json.dumps(
            {
                "timestamp": captured.headers.get("x-timestamp"),
                "nonce": captured.headers.get("x-api-signature-nonce"),
                "signature": captured.headers.get("x-signature"),
                "response": replay_module._response_summary(captured.response_json or {}),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

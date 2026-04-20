#!/usr/bin/env python3
from __future__ import annotations

import argparse
import importlib.util
import json
import sys
import types

from pathlib import Path
from typing import Any, Dict


ROOT = Path(__file__).resolve().parents[1]
PACKAGE_ROOT = ROOT / "custom_components" / "zeekr"
SCRIPT_ROOT = ROOT / "scripts"


def load_zeekr_module(module_name: str):
    custom_components_name = "custom_components"
    package_name = "custom_components.zeekr"
    full_name = f"{package_name}.{module_name}"

    if custom_components_name not in sys.modules:
        custom_components = types.ModuleType(custom_components_name)
        custom_components.__path__ = [str(ROOT / "custom_components")]
        sys.modules[custom_components_name] = custom_components

    if package_name not in sys.modules:
        package = types.ModuleType(package_name)
        package.__path__ = [str(PACKAGE_ROOT)]
        sys.modules[package_name] = package

    if full_name in sys.modules:
        return sys.modules[full_name]

    spec = importlib.util.spec_from_file_location(
        full_name,
        PACKAGE_ROOT / f"{module_name}.py",
    )
    module = importlib.util.module_from_spec(spec)
    sys.modules[full_name] = module
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


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


load_zeekr_module("zeekr_storage")
load_zeekr_module("zeekr_config")
remote_control_module = load_zeekr_module("remote_control_api")
replay_module = load_script_module(
    "replay_cn_remote_control_from_logcat",
    "replay_cn_remote_control_from_logcat.py",
)

ZeekrRemoteControlAPI = remote_control_module.ZeekrRemoteControlAPI
CapturedRequest = replay_module.CapturedRequest


def redact(value: str | None, head: int = 12, tail: int = 10) -> str:
    if not value:
        return "<empty>"
    if len(value) <= head + tail:
        return "*" * len(value)
    return f"{value[:head]}...{value[-tail:]}"


def build_signature_comparisons(captured: CapturedRequest) -> list[dict[str, Any]]:
    client = ZeekrRemoteControlAPI(
        device_id=captured.headers.get("x-device-id", ""),
        access_token=captured.headers.get("authorization", ""),
    )

    comparisons: list[dict[str, Any]] = []
    expected_signature = captured.headers.get("x-signature", "")
    for variant in client._signature_variants():
        debug = client._calculate_signature(
            "POST",
            replay_module.TARGET_URL,
            captured.headers.get("x-timestamp", ""),
            captured.headers.get("x-api-signature-nonce", ""),
            captured.body,
            headers=captured.headers,
            signed_headers=variant["signed_headers"],
            include_body_md5=bool(variant["include_body_md5"]),
            canonicalize_body_for_md5=bool(variant["canonicalize_body_for_md5"]),
            always_include_query_newline=bool(
                variant.get("always_include_query_newline", False)
            ),
        )
        comparisons.append(
            {
                "variant": variant["name"],
                "matched": debug["signature"] == expected_signature,
                "captured_signature": expected_signature,
                "computed_signature": debug["signature"],
                "signed_headers": debug["signed_headers"],
                "canonical_headers": debug["canonical_headers"],
                "body_md5": debug["body_md5"],
                "body_for_md5": debug["body_for_md5"],
                "always_include_query_newline": debug["always_include_query_newline"],
                "signature_base": debug["signature_base"],
            }
        )

    return comparisons


def _capture_request(args: argparse.Namespace) -> CapturedRequest:
    if args.input_json:
        return replay_module.load_captured_request_json(args.input_json)
    return replay_module.capture_request(
        watch=args.watch,
        timeout=args.timeout,
        serial=args.serial,
    )


def _print_captured_summary(captured: CapturedRequest) -> None:
    print("Captured request summary:")
    print(f"Path: {replay_module.TARGET_URL}")
    print(f"Captured signature: {captured.headers.get('x-signature', '<missing>')}")
    print(f"Authorization: {redact(captured.headers.get('authorization'))}")
    print(f"Device ID: {captured.headers.get('x-device-id', '<missing>')}")
    print(
        "Vehicle identifier: "
        f"{redact(captured.headers.get('x-vehicle-identifier'))}"
    )
    print(f"Vehicle series: {captured.headers.get('x-vehicle-series', '<missing>')}")
    print(f"Nonce: {captured.headers.get('x-api-signature-nonce', '<missing>')}")
    print(f"Timestamp: {captured.headers.get('x-timestamp', '<missing>')}")
    print(f"Header count: {len(captured.headers)}")
    if captured.header_order:
        print("Header order:")
        print("  " + " -> ".join(captured.header_order))
    print(f"Request body: {captured.body}")
    if captured.response_status:
        print(f"App response status: {captured.response_status}")
    if captured.response_json is not None:
        print(
            "App response summary: "
            f"{json.dumps(replay_module._response_summary(captured.response_json), ensure_ascii=False)}"
        )


def _print_comparisons(
    comparisons: list[dict[str, Any]],
    *,
    verbose: bool = False,
) -> None:
    any_match = any(item["matched"] for item in comparisons)
    print("\nComparison results:")

    for item in comparisons:
        status = "MATCH" if item["matched"] else "MISS"
        print(
            f"- {item['variant']}: {status}\n"
            f"  computed={item['computed_signature']}\n"
            f"  body_md5={item['body_md5'] or '<empty>'}\n"
            f"  empty_query_line={item['always_include_query_newline']}"
        )

        if verbose:
            print("  canonical_headers:")
            for line in str(item["canonical_headers"]).splitlines():
                print(f"    {line}")
            print("  signature_base:")
            for line in str(item["signature_base"]).splitlines():
                print(f"    {line}")

    if any_match:
        print("\nAt least one candidate variant matches the captured x-signature.")
    else:
        print("\nNo current candidate variant matches the captured x-signature.")


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Compare current candidate mainland-China remote-control signature "
            "variants against a real signed request captured from logcat."
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
        "--input-json",
        help="Compare against an archived sample JSON instead of capturing from adb/logcat.",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Print canonical headers and signature base for every candidate variant.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print the full comparison payload as JSON.",
    )
    args = parser.parse_args()

    captured = _capture_request(args)
    comparisons = build_signature_comparisons(captured)

    if args.json:
        print(
            json.dumps(
                {
                    "captured_headers": {
                        **captured.headers,
                        "authorization": redact(captured.headers.get("authorization")),
                    },
                    "captured_header_order": captured.header_order,
                    "captured_body": captured.body,
                    "captured_response_status": captured.response_status,
                    "captured_response_summary": replay_module._response_summary(
                        captured.response_json or {}
                    ),
                    "comparisons": comparisons,
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return 0

    _print_captured_summary(captured)
    _print_comparisons(comparisons, verbose=args.verbose)
    return 0


if __name__ == "__main__":
    sys.exit(main())

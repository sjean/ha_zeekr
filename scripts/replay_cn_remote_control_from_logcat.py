#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import time

from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, Iterable, Optional

import requests


TARGET_URL = (
    "https://gric-zhf-api.geely.com/"
    "ms-remote-control/api/v1.0/remoteControl/control"
)
REQUEST_MARKER = f"--> POST {TARGET_URL}"

GEELY_MESSAGE_PATTERN = re.compile(r"GEELY_LOG(?:\(\d+\))?: (.*)$")
OKHTTP_MESSAGE_PATTERN = re.compile(r"okhttp\.OkHttpClient(?:\(\d+\))?: (.*)$")
HEADER_MESSAGE_PATTERN = re.compile(r"([A-Za-z0-9-]+): \[(.*)\]$")


@dataclass
class CapturedRequest:
    headers: Dict[str, str]
    body: str
    header_order: list[str] = field(default_factory=list)
    response_status: Optional[str] = None
    response_json: Optional[dict[str, Any]] = None


def _adb_cmd(serial: str | None, *args: str) -> list[str]:
    cmd = ["adb"]
    if serial:
        cmd.extend(["-s", serial])
    cmd.extend(args)
    return cmd


def _run(cmd: list[str]) -> str:
    return subprocess.check_output(cmd, text=True, errors="ignore")


def _extract_tag_message(line: str, pattern: re.Pattern[str]) -> Optional[str]:
    match = pattern.search(line)
    if not match:
        return None
    return match.group(1).strip()


def _strip_log_prefix(line: str) -> str:
    for pattern in (GEELY_MESSAGE_PATTERN, OKHTTP_MESSAGE_PATTERN):
        message = _extract_tag_message(line, pattern)
        if message is not None:
            return message
    return line.strip()


def _looks_like_request_body(payload: Any) -> bool:
    return (
        isinstance(payload, dict)
        and payload.get("serviceId") == "RHL"
        and isinstance(payload.get("setting"), dict)
    )


def _looks_like_response_payload(payload: Any) -> bool:
    return isinstance(payload, dict) and "code" in payload


def _extract_json_from_lines(
    lines: list[str],
    start_index: int,
) -> tuple[str, Any, int] | None:
    first_fragment = _strip_log_prefix(lines[start_index]).strip()
    if not first_fragment.startswith(("{", "[")):
        return None

    fragments = [first_fragment]
    for index in range(start_index, min(len(lines), start_index + 20)):
        if index > start_index:
            fragment = _strip_log_prefix(lines[index]).strip()
            if not fragment:
                break
            fragments.append(fragment)

        candidate = "\n".join(fragments)
        try:
            parsed = json.loads(candidate)
        except json.JSONDecodeError:
            continue
        return candidate, parsed, index + 1

    return None


def _parse_request_block(lines: list[str]) -> CapturedRequest | None:
    headers: Dict[str, str] = {}
    header_order: list[str] = []
    body = ""
    response_status: Optional[str] = None
    response_json: Optional[dict[str, Any]] = None

    index = 0
    while index < len(lines):
        geely_message = _extract_tag_message(lines[index], GEELY_MESSAGE_PATTERN)
        if geely_message:
            header_match = HEADER_MESSAGE_PATTERN.fullmatch(geely_message)
            if header_match:
                header_name = header_match.group(1).lower()
                headers[header_name] = header_match.group(2)
                header_order.append(header_name)
                index += 1
                continue

        if not body:
            json_candidate = _extract_json_from_lines(lines, index)
            if json_candidate is not None:
                candidate_text, candidate_payload, next_index = json_candidate
                if _looks_like_request_body(candidate_payload):
                    body = candidate_text
                    index = next_index
                    continue

        okhttp_message = _extract_tag_message(lines[index], OKHTTP_MESSAGE_PATTERN)
        if okhttp_message and TARGET_URL in okhttp_message and okhttp_message.startswith("<--"):
            response_status = okhttp_message
            json_candidate = _extract_json_from_lines(lines, index + 1)
            if json_candidate is not None:
                _, candidate_payload, _ = json_candidate
                if _looks_like_response_payload(candidate_payload):
                    response_json = candidate_payload

        index += 1

    if "x-signature" not in headers or not body:
        return None

    return CapturedRequest(
        headers=headers,
        body=body,
        header_order=header_order,
        response_status=response_status,
        response_json=response_json,
    )


def _split_request_blocks(lines: Iterable[str]) -> list[list[str]]:
    blocks: list[list[str]] = []
    current: list[str] | None = None

    for line in lines:
        geely_message = _extract_tag_message(line, GEELY_MESSAGE_PATTERN)
        if geely_message == REQUEST_MARKER:
            if current:
                blocks.append(current)
            current = [line]
            continue

        if current is not None:
            current.append(line)

    if current:
        blocks.append(current)

    return blocks


def _extract_latest_request(log_text: str) -> CapturedRequest:
    blocks = _split_request_blocks(log_text.splitlines())
    if not blocks:
        raise RuntimeError("No matching remoteControl/control request found in logcat output.")

    for block in reversed(blocks):
        parsed = _parse_request_block(block)
        if parsed is not None:
            return parsed

    raise RuntimeError("Captured logcat output did not contain a complete signed request block.")


def _wait_for_next_request(timeout: int, serial: str | None) -> CapturedRequest:
    subprocess.run(_adb_cmd(serial, "logcat", "-c"), check=True)
    proc = subprocess.Popen(
        _adb_cmd(serial, "logcat"),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="ignore",
        bufsize=1,
    )

    started = time.time()
    buffer: list[str] = []
    capture_active = False

    try:
        assert proc.stdout is not None
        for line in proc.stdout:
            if time.time() - started > timeout:
                raise TimeoutError("Timed out waiting for a new remote-control request.")

            geely_message = _extract_tag_message(line, GEELY_MESSAGE_PATTERN)
            if geely_message == REQUEST_MARKER:
                capture_active = True
                buffer = [line]
                continue

            if not capture_active:
                continue

            buffer.append(line)
            try:
                parsed = _extract_latest_request("".join(buffer))
            except RuntimeError:
                continue
            return parsed
    finally:
        proc.terminate()

    raise RuntimeError("Did not capture a complete remote-control request block.")


def _normalize_headers(headers: Dict[str, str]) -> Dict[str, str]:
    required = {
        "accept",
        "accept-language",
        "authorization",
        "content-type",
        "x-api-signature-nonce",
        "x-api-signature-version",
        "x-app-id",
        "x-app-version",
        "x-device-brand",
        "x-device-id",
        "x-device-model",
        "x-device-os-version",
        "x-platform",
        "x-sales-platform",
        "x-signature",
        "x-tenant-id",
        "x-timestamp",
        "x-tsp-platform",
        "x-vehicle-brand",
        "x-vehicle-identifier",
        "x-vehicle-series",
    }
    missing = sorted(header for header in required if header not in headers)
    if missing:
        missing_text = ", ".join(missing)
        raise RuntimeError(f"Captured request is missing required headers: {missing_text}")

    return {
        "Accept": headers["accept"],
        "Accept-Language": headers["accept-language"],
        "Authorization": headers["authorization"],
        "Content-Type": headers["content-type"],
        "X-API-SIGNATURE-NONCE": headers["x-api-signature-nonce"],
        "X-API-SIGNATURE-VERSION": headers["x-api-signature-version"],
        "X-APP-ID": headers["x-app-id"],
        "X-APP-VERSION": headers["x-app-version"],
        "X-DEVICE-BRAND": headers["x-device-brand"],
        "X-DEVICE-ID": headers["x-device-id"],
        "X-DEVICE-MODEL": headers["x-device-model"],
        "X-DEVICE-OS-VERSION": headers["x-device-os-version"],
        "X-PLATFORM": headers["x-platform"],
        "X-SALES-PLATFORM": headers["x-sales-platform"],
        "X-SIGNATURE": headers["x-signature"],
        "X-TENANT-ID": headers["x-tenant-id"],
        "X-TIMESTAMP": headers["x-timestamp"],
        "X-TSP-PLATFORM": headers["x-tsp-platform"],
        "X-VEHICLE-BRAND": headers["x-vehicle-brand"],
        "X-VEHICLE-IDENTIFIER": headers["x-vehicle-identifier"],
        "X-VEHICLE-SERIES": headers["x-vehicle-series"],
    }


def _response_summary(payload: dict[str, Any]) -> dict[str, Any]:
    data = payload.get("data") or {}
    return {
        "code": payload.get("code"),
        "msg": payload.get("msg"),
        "sessionId": data.get("sessionId"),
    }


def capture_request(
    *,
    watch: bool = False,
    timeout: int = 120,
    serial: str | None = None,
) -> CapturedRequest:
    if watch:
        return _wait_for_next_request(timeout, serial)
    return _extract_latest_request(_run(_adb_cmd(serial, "logcat", "-d")))


def captured_request_to_dict(captured: CapturedRequest) -> dict[str, Any]:
    return asdict(captured)


def captured_request_from_dict(payload: dict[str, Any]) -> CapturedRequest:
    if "request" in payload and isinstance(payload["request"], dict):
        payload = payload["request"]

    return CapturedRequest(
        headers=dict(payload.get("headers") or {}),
        body=str(payload.get("body") or ""),
        header_order=list(payload.get("header_order") or []),
        response_status=payload.get("response_status"),
        response_json=payload.get("response_json"),
    )


def load_captured_request_json(path: str | Path) -> CapturedRequest:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    return captured_request_from_dict(payload)


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Replay the latest mainland-China remote-control request captured "
            "from com.zeekrlife.mobile logcat output."
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
        "--extract-only",
        action="store_true",
        help="Print the captured request without replaying it.",
    )
    args = parser.parse_args()

    captured = capture_request(
        watch=args.watch,
        timeout=args.timeout,
        serial=args.serial,
    )

    print("Captured request headers:")
    print(json.dumps(captured.headers, ensure_ascii=False, indent=2))
    if captured.header_order:
        print("\nCaptured header order:")
        print(json.dumps(captured.header_order, ensure_ascii=False, indent=2))
    print("\nCaptured request body:")
    print(captured.body)

    if captured.response_status:
        print("\nCaptured app response status:")
        print(captured.response_status)

    if captured.response_json is not None:
        print("\nCaptured app response payload:")
        print(json.dumps(captured.response_json, ensure_ascii=False, indent=2))

    if args.extract_only:
        return 0

    response = requests.post(
        TARGET_URL,
        headers=_normalize_headers(captured.headers),
        data=captured.body,
        timeout=15,
    )

    print(f"\nReplay HTTP {response.status_code}")
    print(response.text)

    try:
        payload = response.json()
    except json.JSONDecodeError:
        return 0

    print("\nReplay summary:")
    print(json.dumps(_response_summary(payload), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())

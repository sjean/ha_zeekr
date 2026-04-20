#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import json
import sys
import types
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
PACKAGE_ROOT = ROOT / "custom_components" / "zeekr"

# Temporary fixed overrides captured from the mobile app.
# Clear these values after verification so the script goes back to normal prompts.
FIXED_CONTROL_OVERRIDES = {
    "authorization": (
        "eyJraWQiOiJmNDgzZmI2ZGM3MTc0ZTEwYmQ0ZWM4NTk2NWE3ZjI4ZCIsInR5cCI6IkpXVCIs"
        "ImFsZyI6IlJTMjU2In0.eyJzdWIiOiIxNTgyNzM2NTY3NjU2NTgzMTY4Iiwib3BlbklkIjoi"
        "MTU4MjczNjU2NzY1NjU4MzE2OCIsImlzcyI6Imh0dHBzOi8vZ3JpYy1taWQtaW5uZXIuZ2Vl"
        "bHkuY29tL21zLWF1dGgtc2VydmljZS9pbm5lci92MS4wL29hdXRoL2luZm8iLCJ0eXAiOiJC"
        "ZWFyZXIiLCJlbnYiOiJQUk9EIiwidXNlcklkIjoiMTAzMTMzMzIyIiwiZGV2aWNlSWQiOiI3"
        "NzEyOTJkYi1kMDliLTQ5MTctOTgzYS02ZTUyNjFhNjI2ZjUiLCJzaWQiOiI2ZWYyNjQzYi04"
        "OGUzLTQzNmYtYmZlOS03Nzc5ODgyYTEyNzEiLCJhdWQiOiJhdXRoX2NsaWVudF96ZWVrcl9w"
        "aG9uZSIsImFjciI6IjEiLCJuYmYiOjE3NzY0OTQ5OTMsImF6cCI6ImF1dGhfY2xpZW50X3pl"
        "ZWtyX3Bob25lIiwic2NvcGUiOiIiLCJleHAiOjE3NzcwOTk3OTMsInNlc3Npb25fc3RhdGUi"
        "OiI2ZWYyNjQzYi04OGUzLTQzNmYtYmZlOS03Nzc5ODgyYTEyNzEiLCJpYXQiOjE3NzY0OTQ5"
        "OTMsImJyYW5kIjoiWkVFS1IiLCJqdGkiOiJiMzYwMzUxYy0wNGEyLTRhYWQtOTVjYy1iMTMz"
        "M2EzMmUxMDEifQ.kgQZB_FCh-fkO3igxOktqIyygcv1ECAqsQ3pSt79q_POMBRhneeEoIAIe"
        "1DMcnJpHboXlVkrH1QLrcTiJPtK6XjckbHGdb1O2YMdOu4XMotdTdGR07cJAQ_paNNleFxWnG"
        "TM9fTlxoxmN2CByInLAFY6WElFQmydqZxYgfXhnDxhTfJROp-PJ_EEybUmOIJBpwjpkisc2Ms"
        "LveUgKvGUE1ekVTyHbFwTw4D4bH46R6n-pUPppRjUWyQZEbSrS741Mi1dx46Olj4Cd4vlCrzl"
        "90QDp1pbvlxYNQRqcLRkcE05otxrucT94e45JJYYSv8V5A3RRFiV21G_JHsAFL_-mg"
    ),
    "device_id": "771292db-d09b-4917-983a-6e5261a626f5",
    "vehicle_identifier": "hpH7FDmHeL+LAK3KvT6UTq3A5aW3sOjEv3u7Y3HFtto=",
    "vehicle_series": "REMxRQ==",
}


def load_zeekr_module(module_name: str):
    """Load a Zeekr module without importing Home Assistant runtime dependencies."""
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


load_zeekr_module("zeekr_storage")
load_zeekr_module("zeekr_config")
auth_module = load_zeekr_module("auth")
api_module = load_zeekr_module("zeekr_api")
remote_control_module = load_zeekr_module("remote_control_api")

ZeekrAuth = auth_module.ZeekrAuth
ZeekrAPI = api_module.ZeekrAPI
ZeekrRemoteControlAPI = remote_control_module.ZeekrRemoteControlAPI


def redact(value: str | None, head: int = 6, tail: int = 6) -> str:
    if not value:
        return "<empty>"
    if len(value) <= head + tail:
        return "*" * len(value)
    return f"{value[:head]}...{value[-tail:]}"


def prompt_required(label: str) -> str:
    value = input(label).strip()
    if not value:
        raise SystemExit(f"{label.strip()} is required.")
    return value


def prompt_yes_no(label: str, default: bool = False) -> bool:
    suffix = " [Y/n]: " if default else " [y/N]: "
    raw = input(f"{label}{suffix}").strip().lower()
    if not raw:
        return default
    return raw in {"y", "yes"}


def prompt_optional(label: str) -> str:
    return input(label).strip()


def prompt_override(
    label: str,
    current_value: str,
    *,
    redact_value: bool = False,
) -> str:
    display_value = redact(current_value) if redact_value else current_value
    raw = prompt_optional(f"{label} [{display_value}]: ")
    return raw or current_value


def sanitize_signature_text(text: str) -> str:
    if not text:
        return "<empty>"

    sanitized_lines = []
    for line in text.splitlines():
        if line.lower().startswith("authorization:"):
            _, _, value = line.partition(":")
            sanitized_lines.append(f"authorization:{redact(value.strip(), 10, 8)}")
            continue
        sanitized_lines.append(line)
    return "\n".join(sanitized_lines)


def debug_headers_for_display(headers: dict[str, Any]) -> dict[str, Any]:
    display_headers = dict(headers)
    authorization = display_headers.get("authorization")
    if isinstance(authorization, str):
        display_headers["authorization"] = redact(authorization, 10, 8)
    return display_headers


def print_signature_debug(debug: dict[str, Any]) -> None:
    signature_debug = debug.get("signature_debug") or {}

    print("\n--- Signature debug ---")
    print(f"Variant: {debug.get('variant_name', 'unknown')}")
    print(f"Path:    {debug.get('path', '<unknown>')}")
    print(f"Nonce:   {debug.get('nonce', '<unknown>')}")
    print(f"Time:    {debug.get('timestamp', '<unknown>')}")
    print(f"Headers: {debug.get('signed_headers_filter', '<unknown>')}")
    print(f"Body MD5 enabled:      {debug.get('include_body_md5')}")
    print(f"Body MD5 canonicalized:{debug.get('canonicalize_body_for_md5')}")

    print("\nRequest headers:")
    print(
        json.dumps(
            debug_headers_for_display(debug.get("request_headers", {})),
            ensure_ascii=False,
            indent=2,
        )
    )

    print("\nRequest body:")
    print(debug.get("request_body") or "<empty>")

    print("\nCanonical headers:")
    print(sanitize_signature_text(str(signature_debug.get("canonical_headers", ""))))

    print("\nBody used for MD5:")
    print(signature_debug.get("body_for_md5") or "<empty>")

    print(f"\nBody MD5: {signature_debug.get('body_md5') or '<empty>'}")
    print(f"Computed signature: {signature_debug.get('signature') or '<empty>'}")

    print("\nSignature base:")
    print(sanitize_signature_text(str(signature_debug.get("signature_base", ""))))

    if debug.get("response_json") is not None:
        print("\nGateway response:")
        print(json.dumps(debug["response_json"], ensure_ascii=False, indent=2))

    print("--- End signature debug ---")


def choose_vehicle(vehicles: list[dict[str, Any]]) -> dict[str, Any]:
    if len(vehicles) == 1:
        vehicle = vehicles[0]
        print(f"Using the only vehicle: {vehicle.get('vin', '<missing vin>')}")
        return vehicle

    print("\nAvailable vehicles:")
    for index, vehicle in enumerate(vehicles, start=1):
        vin = vehicle.get("vin", "<missing vin>")
        label = (
            vehicle.get("name")
            or vehicle.get("vehicleName")
            or vehicle.get("nickName")
            or vehicle.get("plateNo")
            or vin
        )
        print(f"{index}. {label} ({vin})")

    while True:
        raw = prompt_required("Choose vehicle number: ")
        if raw.isdigit():
            selected = int(raw)
            if 1 <= selected <= len(vehicles):
                return vehicles[selected - 1]
        print("Please enter a valid number from the list above.")


def prompt_series_code(vehicle: dict[str, Any]) -> str:
    detected = ZeekrRemoteControlAPI.extract_series_code(vehicle)
    if detected:
        manual = input(f"Vehicle series code [{detected}]: ").strip()
        return manual or detected

    print("\nCould not infer the vehicle series code from the vehicle list response.")
    print("Raw vehicle entry:")
    print(json.dumps(vehicle, ensure_ascii=False, indent=2))
    return prompt_required("Vehicle series code (for example DC1E): ")


def series_code_candidates(series_code: str) -> list[str]:
    candidates = [series_code]
    if "-" in series_code:
        base_series = series_code.split("-", 1)[0].strip()
        if base_series and base_series not in candidates:
            candidates.append(base_series)
    return candidates


def build_manual_control_overrides(
    current_authorization: str,
    current_device_id: str,
    current_vehicle_identifier: str,
    current_vehicle_series: str,
) -> dict[str, str]:
    print("\nEnter the exact values captured from the mobile app logs.")
    print("Press Enter to keep the current script-derived value for any field.\n")

    return {
        "authorization": prompt_override(
            "Authorization override",
            current_authorization,
            redact_value=True,
        ),
        "device_id": prompt_override(
            "Device ID override",
            current_device_id,
            redact_value=False,
        ),
        "vehicle_identifier": prompt_override(
            "Vehicle identifier override",
            current_vehicle_identifier,
            redact_value=True,
        ),
        "vehicle_series": prompt_override(
            "Vehicle series override",
            current_vehicle_series,
            redact_value=False,
        ),
    }


def get_fixed_control_overrides() -> dict[str, str] | None:
    required_keys = (
        "authorization",
        "device_id",
        "vehicle_identifier",
        "vehicle_series",
    )
    if all(FIXED_CONTROL_OVERRIDES.get(key) for key in required_keys):
        return dict(FIXED_CONTROL_OVERRIDES)
    return None


def main() -> int:
    print("Zeekr smoke test")
    print("This script performs a real login, fetches vehicles, and can trigger find-car.\n")

    mobile = prompt_required("Mobile number: ")
    signature_debug_enabled = prompt_yes_no(
        "Print signature debug details if gateway signing fails?",
        default=True,
    )
    auth = ZeekrAuth()

    if prompt_yes_no("Request a fresh SMS code first?", default=False):
        print("\n== Step 1: Request SMS code ==")
        success, message = auth.request_sms_code(mobile)
        if not success:
            print(f"SMS request failed: {message}")
            return 1
        print("SMS request succeeded.")

    sms_code = prompt_required("SMS code: ")

    print("\n== Step 2: Login with SMS code ==")
    login_success, toc_tokens = auth.login_with_sms(mobile, sms_code)
    if not login_success or not toc_tokens:
        print("SMS login failed.")
        return 1

    jwt_token = toc_tokens.get("jwtToken")
    if not jwt_token:
        print("SMS login did not return a JWT token.")
        return 1

    print(f"JWT token: {redact(jwt_token)}")
    print(f"Device ID:  {auth.device_id}")

    print("\n== Step 3: Exchange JWT for auth code ==")
    auth_code_success, auth_code = auth.get_auth_code(jwt_token)
    if not auth_code_success or not auth_code:
        print("Failed to retrieve auth code.")
        return 1

    print(f"Auth code: {redact(auth_code)}")

    print("\n== Step 4: Exchange auth code for secure tokens ==")
    secure_success, secure_tokens = auth.login_with_auth_code(auth_code)
    if not secure_success or not secure_tokens:
        print("Failed to retrieve secure tokens.")
        return 1

    print(f"Access token: {redact(secure_tokens.get('accessToken'))}")
    print(f"User ID:      {secure_tokens.get('userId')}")
    print(f"Client ID:    {secure_tokens.get('clientId')}")

    api = ZeekrAPI(
        access_token=secure_tokens["accessToken"],
        user_id=secure_tokens["userId"],
        client_id=secure_tokens["clientId"],
        device_id=secure_tokens["device_id"],
    )

    print("\n== Step 5: Fetch vehicles ==")
    vehicles_success, vehicles = api.get_vehicle_entries()
    if not vehicles_success or not vehicles:
        print("Failed to fetch vehicles or no vehicles were returned.")
        return 1

    selected_vehicle = choose_vehicle(vehicles)
    vin = selected_vehicle.get("vin")
    if not vin:
        print("Selected vehicle entry does not contain a VIN.")
        return 1

    print(f"Selected VIN: {vin}")

    print("\n== Step 6: Fetch vehicle status ==")
    status_success, status = api.get_vehicle_status(vin)
    if not status_success or not status:
        print(f"Failed to fetch status for {vin}")
        return 1

    basic = status.get("basicVehicleStatus", {})
    print(
        f"Vehicle status: engineStatus={basic.get('engineStatus', 'unknown')}, "
        f"updateTime={status.get('updateTime', 'unknown')}"
    )

    series_code = prompt_series_code(selected_vehicle)
    candidate_codes = series_code_candidates(series_code)
    metadata_builder = ZeekrRemoteControlAPI(
        device_id=secure_tokens["device_id"],
        access_token="",
        remote_control_vehicles={},
    )
    remote_metadata = metadata_builder.build_vehicle_metadata(vin, candidate_codes[0])
    control_device_id = secure_tokens["device_id"]
    control_authorization_override = ""
    manual_vehicle_metadata = None

    print("\nDerived remote-control metadata:")
    print(f"Series code:         {candidate_codes[0]}")
    print(f"Vehicle identifier:  {redact(remote_metadata['vehicle_identifier'])}")
    print(f"Vehicle series:      {remote_metadata['vehicle_series']}")
    if len(candidate_codes) > 1:
        print(f"Fallback series:     {candidate_codes[1:]}")

    fixed_overrides = get_fixed_control_overrides()
    if fixed_overrides is not None:
        overrides = fixed_overrides
        print("\nUsing fixed control overrides from script constants.")
    elif prompt_yes_no("Override control headers with exact values from app logs?", default=False):
        overrides = build_manual_control_overrides(
            secure_tokens["accessToken"],
            control_device_id,
            remote_metadata["vehicle_identifier"],
            remote_metadata["vehicle_series"],
        )
    else:
        overrides = None

    if overrides is not None:
        control_authorization_override = overrides["authorization"]
        control_device_id = overrides["device_id"]
        manual_vehicle_metadata = {
            "vehicle_identifier": overrides["vehicle_identifier"],
            "vehicle_series": overrides["vehicle_series"],
        }

        print("\nUsing manual control overrides:")
        print(f"Authorization:       {redact(control_authorization_override)}")
        print(f"Device ID:           {control_device_id}")
        print(
            "Vehicle identifier:  "
            f"{redact(manual_vehicle_metadata['vehicle_identifier'])}"
        )
        print(f"Vehicle series:      {manual_vehicle_metadata['vehicle_series']}")

    print("\n== Step 7: Exchange gateway token ==")
    if control_authorization_override and control_authorization_override != secure_tokens["accessToken"]:
        control_access_token = control_authorization_override
        print("Skipping gateway token exchange because a manual authorization override was provided.")
        print(f"Control token:       {redact(control_access_token)}")
    else:
        gateway_metadata = manual_vehicle_metadata or remote_metadata
        gateway_success, gateway_result = auth.exchange_gateway_token(
            auth_code,
            gateway_metadata["vehicle_identifier"],
            gateway_metadata["vehicle_series"],
            debug_callback=print_signature_debug if signature_debug_enabled else None,
        )
        if gateway_success and gateway_result:
            control_access_token = gateway_result["gatewayAccessToken"]
            print(f"Gateway token:       {redact(control_access_token)}")
            print(
                "Signature variant:   "
                f"{gateway_result.get('signatureVariant', 'unknown')}"
            )
        else:
            control_access_token = control_authorization_override or secure_tokens["accessToken"]
            print("Gateway token exchange failed, falling back to secure access token.")

    if not prompt_yes_no("Trigger the real find-car action now?", default=False):
        print("Skipping the remote-control action.")
        return 0

    remote_api = ZeekrRemoteControlAPI(
        device_id=control_device_id,
        access_token=control_access_token,
        remote_control_vehicles={},
        jwt_token=secure_tokens.get("jwtToken", ""),
    )

    print("\n== Step 8: Trigger find-car ==")
    if manual_vehicle_metadata is not None:
        remote_api.remote_control_vehicles[vin] = manual_vehicle_metadata
        print("Trying manual override metadata")
        success, session_id = remote_api.find_car(
            vin,
            debug_callback=print_signature_debug if signature_debug_enabled else None,
        )
        if success:
            print(f"Find-car request accepted. Session ID: {session_id}")
            print("\nSmoke test completed successfully.")
            return 0

        print(
            f"Find-car request failed for manual override metadata: "
            f"{json.dumps(remote_api.last_error_response or {}, ensure_ascii=False)}"
        )
        print("Find-car request failed.")
        return 1

    for current_series_code in candidate_codes:
        remote_metadata = remote_api.build_vehicle_metadata(vin, current_series_code)
        remote_api.remote_control_vehicles[vin] = remote_metadata
        print(f"Trying series code: {current_series_code}")
        success, session_id = remote_api.find_car(
            vin,
            debug_callback=print_signature_debug if signature_debug_enabled else None,
        )
        if success:
            print(f"Find-car request accepted. Session ID: {session_id}")
            print("\nSmoke test completed successfully.")
            return 0

        if remote_api.last_error_response:
            print(f"Gateway response: {json.dumps(remote_api.last_error_response, ensure_ascii=False)}")

    print("Find-car request failed.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())

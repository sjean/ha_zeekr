from __future__ import annotations

import importlib.util
import sys
import types

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PACKAGE_ROOT = ROOT / "custom_components" / "zeekr"
SCRIPT_PATH = ROOT / "scripts" / "compare_cn_remote_control_signature.py"


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


def load_script_module():
    module_name = "compare_cn_remote_control_signature"
    if module_name in sys.modules:
        return sys.modules[module_name]

    spec = importlib.util.spec_from_file_location(module_name, SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


load_zeekr_module("zeekr_storage")
load_zeekr_module("zeekr_config")
remote_control_module = load_zeekr_module("remote_control_api")
compare_module = load_script_module()

ZeekrRemoteControlAPI = remote_control_module.ZeekrRemoteControlAPI


def test_build_signature_comparisons_detects_matching_variant():
    headers = {
        "accept": "application/json; charset=UTF-8",
        "accept-language": "zh_CN",
        "authorization": "token-123",
        "content-type": "application/json; charset=UTF-8",
        "x-api-signature-nonce": "nonce-123",
        "x-api-signature-version": "2.1",
        "x-app-id": "GEELYCNCH001M0001",
        "x-app-version": "v1.0.0",
        "x-device-brand": "ONEPLUS",
        "x-device-id": "device-123",
        "x-device-model": "PLK110",
        "x-device-os-version": "Android 16 (API 36)",
        "x-platform": "Android",
        "x-sales-platform": "ZEEKR",
        "x-tenant-id": "ZEEKR",
        "x-timestamp": "1776495073747",
        "x-tsp-platform": "4",
        "x-vehicle-brand": "ZEEKR",
        "x-vehicle-identifier": "vehicle-identifier",
        "x-vehicle-series": "REMxRQ==",
    }
    body = (
        '{"command":"","serviceId":"RHL","setting":{"serviceParameters":'
        '[{"key":"rhl","value":"light-flash"}]}}'
    )

    client = ZeekrRemoteControlAPI(
        device_id=headers["x-device-id"],
        access_token=headers["authorization"],
    )
    variant = next(
        item
        for item in client._signature_variants()
        if item["name"] == "core_allowlist_raw_auth_canonical_body_md5"
    )
    debug = client._calculate_signature(
        "POST",
        compare_module.replay_module.TARGET_URL,
        headers["x-timestamp"],
        headers["x-api-signature-nonce"],
        body,
        headers=headers,
        signed_headers=variant["signed_headers"],
        include_body_md5=bool(variant["include_body_md5"]),
        canonicalize_body_for_md5=bool(variant["canonicalize_body_for_md5"]),
    )
    headers["x-signature"] = str(debug["signature"])

    captured = compare_module.CapturedRequest(headers=headers, body=body)
    comparisons = compare_module.build_signature_comparisons(captured)

    matched_variants = {
        item["variant"]: item["computed_signature"]
        for item in comparisons
        if item["matched"]
    }
    assert "core_allowlist_raw_auth_canonical_body_md5" in matched_variants
    assert matched_variants["core_allowlist_raw_auth_canonical_body_md5"] == headers["x-signature"]

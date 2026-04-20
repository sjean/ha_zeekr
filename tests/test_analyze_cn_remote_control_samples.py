from __future__ import annotations

import importlib.util
import json
import sys

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = ROOT / "scripts" / "analyze_cn_remote_control_samples.py"


def load_script_module():
    module_name = "analyze_cn_remote_control_samples"
    if module_name in sys.modules:
        return sys.modules[module_name]

    spec = importlib.util.spec_from_file_location(module_name, SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


analyze_module = load_script_module()


def _sample_payload(signature: str, nonce: str, timestamp: str) -> dict:
    return {
        "request": {
            "headers": {
                "authorization": "token-123",
                "x-signature": signature,
                "x-api-signature-nonce": nonce,
                "x-timestamp": timestamp,
                "x-device-id": "device-123",
                "x-vehicle-series": "REMxRQ==",
            },
            "body": '{"command":"","serviceId":"RHL"}',
            "header_order": [
                "authorization",
                "x-api-signature-nonce",
                "x-timestamp",
                "x-signature",
            ],
            "response_json": {"code": "0"},
        }
    }


def test_classify_header_values_and_patterns():
    samples = [
        _sample_payload("sig-1", "nonce-1", "1000"),
        _sample_payload("sig-2", "nonce-2", "1015"),
    ]

    classification = analyze_module.classify_header_values(samples)
    order_info = analyze_module.analyze_header_order(samples)
    nonce_report = analyze_module.analyze_nonce_and_timestamp(samples)

    assert classification["stable"]["authorization"] == "token-123"
    assert "x-signature" in classification["variable"]
    assert "x-api-signature-nonce" in classification["variable"]
    assert order_info["consistent"] is True
    assert order_info["common_order"] == [
        "authorization",
        "x-api-signature-nonce",
        "x-timestamp",
        "x-signature",
    ]
    assert nonce_report["unique_nonce_count"] == 2
    assert nonce_report["timestamp_deltas"]["min"] == 15

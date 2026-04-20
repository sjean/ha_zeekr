from __future__ import annotations

import importlib.util
import sys

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = ROOT / "scripts" / "replay_cn_remote_control_from_logcat.py"


def load_script_module():
    module_name = "replay_cn_remote_control_from_logcat"
    if module_name in sys.modules:
        return sys.modules[module_name]

    spec = importlib.util.spec_from_file_location(module_name, SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


replay_module = load_script_module()


def test_extract_latest_request_parses_headers_body_and_response():
    log_text = """
04-18 14:51:13.751 I/GEELY_LOG(24069): --> POST https://gric-zhf-api.geely.com/ms-remote-control/api/v1.0/remoteControl/control
04-18 14:51:13.752 I/GEELY_LOG(24069): accept: [application/json; charset=UTF-8]
04-18 14:51:13.752 I/GEELY_LOG(24069): accept-language: [zh_CN]
04-18 14:51:13.752 I/GEELY_LOG(24069): authorization: [token-123]
04-18 14:51:13.752 I/GEELY_LOG(24069): content-type: [application/json; charset=UTF-8]
04-18 14:51:13.752 I/GEELY_LOG(24069): x-api-signature-nonce: [nonce-123]
04-18 14:51:13.752 I/GEELY_LOG(24069): x-api-signature-version: [2.1]
04-18 14:51:13.752 I/GEELY_LOG(24069): x-app-id: [GEELYCNCH001M0001]
04-18 14:51:13.752 I/GEELY_LOG(24069): x-app-version: [v1.0.0]
04-18 14:51:13.752 I/GEELY_LOG(24069): x-device-brand: [ONEPLUS]
04-18 14:51:13.752 I/GEELY_LOG(24069): x-device-id: [device-123]
04-18 14:51:13.752 I/GEELY_LOG(24069): x-device-model: [PLK110]
04-18 14:51:13.752 I/GEELY_LOG(24069): x-device-os-version: [Android 16 (API 36)]
04-18 14:51:13.752 I/GEELY_LOG(24069): x-platform: [Android]
04-18 14:51:13.752 I/GEELY_LOG(24069): x-sales-platform: [ZEEKR]
04-18 14:51:13.752 I/GEELY_LOG(24069): x-signature: [signature-123]
04-18 14:51:13.752 I/GEELY_LOG(24069): x-tenant-id: [ZEEKR]
04-18 14:51:13.752 I/GEELY_LOG(24069): x-timestamp: [1776495073747]
04-18 14:51:13.752 I/GEELY_LOG(24069): x-tsp-platform: [4]
04-18 14:51:13.752 I/GEELY_LOG(24069): x-vehicle-brand: [ZEEKR]
04-18 14:51:13.752 I/GEELY_LOG(24069): x-vehicle-identifier: [vehicle-identifier]
04-18 14:51:13.752 I/GEELY_LOG(24069): x-vehicle-series: [REMxRQ==]
04-18 14:51:13.753 I/GEELY_LOG(24069): {"command":"","serviceId":"RHL","setting":{"serviceParameters":[{"key":"rhl","value":"light-flash"}]}}
04-18 14:51:13.860 I/okhttp.OkHttpClient(24069): <-- 200 https://gric-zhf-api.geely.com/ms-remote-control/api/v1.0/remoteControl/control (108ms)
04-18 14:51:13.860 I/okhttp.OkHttpClient(24069): {"code":"0","msg":"操作成功","data":{"sessionId":"PP010376000000019507467085979482"}}
""".strip()

    captured = replay_module._extract_latest_request(log_text)

    assert captured.headers["authorization"] == "token-123"
    assert captured.headers["x-vehicle-series"] == "REMxRQ=="
    assert captured.header_order[:3] == ["accept", "accept-language", "authorization"]
    assert '"serviceId":"RHL"' in captured.body
    assert captured.response_json == {
        "code": "0",
        "msg": "操作成功",
        "data": {"sessionId": "PP010376000000019507467085979482"},
    }


def test_normalize_headers_raises_when_required_values_are_missing():
    try:
        replay_module._normalize_headers({"authorization": "token-123"})
    except RuntimeError as exc:
        assert "x-signature" in str(exc)
    else:
        raise AssertionError("Expected _normalize_headers to reject incomplete headers.")


def test_captured_request_round_trip_preserves_header_order():
    captured = replay_module.CapturedRequest(
        headers={"authorization": "token-123", "x-signature": "sig-123"},
        body='{"serviceId":"RHL"}',
        header_order=["authorization", "x-signature"],
        response_status="<-- 200 sample",
        response_json={"code": "0"},
    )

    payload = replay_module.captured_request_to_dict(captured)
    restored = replay_module.captured_request_from_dict(payload)

    assert restored.headers == captured.headers
    assert restored.body == captured.body
    assert restored.header_order == captured.header_order
    assert restored.response_json == captured.response_json

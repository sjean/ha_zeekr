from __future__ import annotations

import importlib.util
import sys
import types
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PACKAGE_ROOT = ROOT / "custom_components" / "zeekr"


def load_zeekr_module(module_name: str):
    """Load a Zeekr module without importing Home Assistant dependencies."""
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


# Load dependency modules first so relative imports resolve cleanly.
load_zeekr_module("zeekr_storage")
load_zeekr_module("zeekr_config")
auth_module = load_zeekr_module("auth")
api_module = load_zeekr_module("zeekr_api")
remote_control_module = load_zeekr_module("remote_control_api")

ZeekrAuth = auth_module.ZeekrAuth
ZeekrAPI = api_module.ZeekrAPI
ZeekrRemoteControlAPI = remote_control_module.ZeekrRemoteControlAPI
EXTENDED_SIGNED_HEADERS = remote_control_module.EXTENDED_SIGNED_HEADERS


class FakeResponse:
    def __init__(self, payload: dict, status_code: int = 200):
        self._payload = payload
        self.status_code = status_code

    def json(self) -> dict:
        return self._payload


class FakeAuthSession:
    """Route auth requests to deterministic fake responses."""

    def __init__(self):
        self.calls = []

    def get(self, url, **kwargs):
        self.calls.append(("GET", url, kwargs))

        if url.endswith("/zeekrlife-app-user/v1/user/pub/sms/authCode"):
            return FakeResponse({"code": "000000"})

        if url.endswith("/zeekrlife-mp-auth2/v1/auth/accessCodeList"):
            assert kwargs["headers"]["Authorization"] == "jwt-token"
            return FakeResponse({"code": "000000", "data": {"YIKAT_NEW": "auth-code-123"}})

        raise AssertionError(f"Unexpected GET URL: {url}")

    def post(self, url, **kwargs):
        self.calls.append(("POST", url, kwargs))

        if url.endswith("/zeekrlife-app-user/v1/user/pub/login/mobile"):
            assert kwargs["json"]["smsCode"] == "1234"
            return FakeResponse({"code": "000000", "data": {"jwtToken": "jwt-token"}})

        if url.endswith("/ms-midground-user/api/v1.0/user/auth/get/token"):
            assert kwargs["data"] == '{"authCode":"auth-code-123","identityType":"1"}'
            assert "authorization" not in kwargs["headers"]
            return FakeResponse(
                {
                    "code": "0",
                    "data": {
                        "accessToken": "gateway-access-token",
                        "expiresIn": 3600,
                    },
                }
            )

        if "/auth/account/session/secure?" in url:
            return FakeResponse(
                {
                    "code": 1000,
                    "data": {
                        "accessToken": "access-token",
                        "refreshToken": "refresh-token",
                        "userId": "user-123",
                        "clientId": "client-456",
                    },
                }
            )

        raise AssertionError(f"Unexpected POST URL: {url}")


class FakeVehicleSession:
    """Route vehicle API requests to deterministic fake responses."""

    def __init__(self):
        self.calls = []

    def get(self, url, **kwargs):
        self.calls.append(("GET", url, kwargs))

        if "/device-platform/user/vehicle/secure?" in url:
            return FakeResponse(
                {
                    "code": "1000",
                    "data": {
                        "list": [
                            {"vin": "VIN123"},
                            {"vin": "VIN456"},
                        ]
                    },
                }
            )

        if "/remote-control/vehicle/status/VIN123?" in url:
            return FakeResponse(
                {
                    "code": "1000",
                    "data": {"vehicleStatus": {"basicVehicleStatus": {"engineStatus": "engine_running"}}},
                }
            )

        if "/remote-control/vehicle/status/VIN456?" in url:
            return FakeResponse(
                {
                    "code": "1000",
                    "data": {"vehicleStatus": {"basicVehicleStatus": {"engineStatus": "engine_off"}}},
                }
            )

        raise AssertionError(f"Unexpected GET URL: {url}")


def test_login_flow_returns_secure_tokens():
    auth = ZeekrAuth()
    auth.session = FakeAuthSession()

    sms_requested, sms_message = auth.request_sms_code("13812345678")
    assert sms_requested is True
    assert sms_message == "SMS code sent successfully"

    sms_login_success, toc_tokens = auth.login_with_sms("13812345678", "1234")
    assert sms_login_success is True
    assert toc_tokens == {
        "jwtToken": "jwt-token",
        "mobile": "13812345678",
        "device_id": auth.device_id,
    }

    auth_code_success, auth_code = auth.get_auth_code("jwt-token")
    assert auth_code_success is True
    assert auth_code == "auth-code-123"

    secure_login_success, secure_tokens = auth.login_with_auth_code(auth_code)
    assert secure_login_success is True
    assert secure_tokens == {
        "jwtToken": "jwt-token",
        "accessToken": "access-token",
        "refreshToken": "refresh-token",
        "userId": "user-123",
        "clientId": "client-456",
        "mobile": "13812345678",
        "device_id": auth.device_id,
    }

    gateway_success, gateway_data = auth.exchange_gateway_token(
        auth_code,
        "vehicle-id-encoded",
        "vehicle-series-encoded",
    )
    assert gateway_success is True
    assert gateway_data == {
        "gatewayAccessToken": "gateway-access-token",
        "raw": {
            "accessToken": "gateway-access-token",
            "expiresIn": 3600,
        },
        "signatureVariant": "all_headers_raw_auth_raw_body_md5",
    }


def test_get_all_vehicle_statuses_returns_vehicle_map():
    api = ZeekrAPI(
        access_token="access-token",
        user_id="user-123",
        client_id="client-456",
        device_id="device-789",
    )
    api.session = FakeVehicleSession()

    success, all_status = api.get_all_vehicles_status()

    assert success is True
    assert all_status == {
        "VIN123": {"basicVehicleStatus": {"engineStatus": "engine_running"}},
        "VIN456": {"basicVehicleStatus": {"engineStatus": "engine_off"}},
    }


class FakeRemoteControlSession:
    def __init__(self):
        self.calls = []

    def post(self, url, **kwargs):
        self.calls.append(("POST", url, kwargs))
        return FakeResponse(
            {
                "code": "0",
                "data": {"sessionId": "RC-SESSION-123"},
            }
        )


class FakeRetryRemoteControlSession:
    def __init__(self):
        self.calls = []

    def post(self, url, **kwargs):
        self.calls.append(("POST", url, kwargs))
        if len(self.calls) == 1:
            return FakeResponse(
                {
                    "code": "00A06",
                    "msg": "Signature authentication failed.",
                    "data": None,
                }
            )
        return FakeResponse(
            {
                "code": "0",
                "data": {"sessionId": "RC-SESSION-RETRY"},
            }
        )


def test_find_car_returns_session_id_with_injected_signature():
    api = ZeekrRemoteControlAPI(
        jwt_token="jwt-token",
        device_id="device-123",
        remote_control_vehicles={
            "VIN123": {
                "vehicle_identifier": "vehicle-id-encoded",
                "vehicle_series": "vehicle-series-encoded",
            }
        },
        signature_callback=lambda method, path, timestamp, nonce, body: "signed-value",
    )
    api.session = FakeRemoteControlSession()

    success, session_id = api.find_car("VIN123")

    assert success is True
    assert session_id == "RC-SESSION-123"

    method, url, kwargs = api.session.calls[0]
    assert method == "POST"
    assert url == "https://gric-zhf-api.geely.com/ms-remote-control/api/v1.0/remoteControl/control"
    assert kwargs["headers"]["authorization"] == "jwt-token"
    assert kwargs["headers"]["x-signature"] == "signed-value"
    assert kwargs["headers"]["x-vehicle-identifier"] == "vehicle-id-encoded"
    assert kwargs["headers"]["x-vehicle-series"] == "vehicle-series-encoded"
    assert kwargs["data"] == (
        '{"command":"","serviceId":"RHL","setting":{"serviceParameters":'
        '[{"key":"rhl","value":"light-flash"}]}}'
    )


def test_find_car_fails_without_vehicle_metadata():
    api = ZeekrRemoteControlAPI(
        jwt_token="jwt-token",
        device_id="device-123",
        remote_control_vehicles={},
        signature_callback=lambda method, path, timestamp, nonce, body: "signed-value",
    )

    success, session_id = api.find_car("VIN123")

    assert success is False
    assert session_id is None


def test_find_car_retries_after_signature_failure():
    api = ZeekrRemoteControlAPI(
        jwt_token="jwt-token",
        device_id="device-123",
        remote_control_vehicles={
            "VIN123": {
                "vehicle_identifier": "vehicle-id-encoded",
                "vehicle_series": "vehicle-series-encoded",
            }
        },
    )
    api.session = FakeRetryRemoteControlSession()

    success, session_id = api.find_car("VIN123")

    assert success is True
    assert session_id == "RC-SESSION-RETRY"
    assert len(api.session.calls) == 2


def test_remote_control_authorization_prefers_access_token():
    api = ZeekrRemoteControlAPI(
        device_id="device-123",
        access_token="access-token",
        jwt_token="jwt-token",
    )

    assert api._format_authorization() == "access-token"
    assert api._format_authorization(include_bearer=False) == "access-token"
    assert api._format_authorization(include_bearer=True) == "Bearer access-token"


def test_build_vehicle_metadata_from_vin_and_series_code():
    api = ZeekrRemoteControlAPI(
        jwt_token="jwt-token",
        device_id="device-123",
    )

    metadata = api.build_vehicle_metadata("VIN12345678901234", "DC1E")

    assert metadata == {
        "vehicle_identifier": "B0ERbkAibJq5dVWO7dpuQYJ94PIx+gxOeJElI5Vjo7E=",
        "vehicle_series": "REMxRQ==",
    }


def test_build_vehicle_series_accepts_once_encoded_value():
    api = ZeekrRemoteControlAPI(
        jwt_token="jwt-token",
        device_id="device-123",
    )

    assert api.build_vehicle_series("REMxRQ==") == "REMxRQ=="
    assert api.build_vehicle_series("UkVNeFJRPT0=") == "REMxRQ=="


def test_remote_control_signature_matches_android_probe_formula():
    api = ZeekrRemoteControlAPI(
        jwt_token="jwt-token",
        device_id="device-123",
    )
    vehicle_metadata = api.build_vehicle_metadata("VIN12345678901234", "DC1E")
    body = (
        '{"command":"","serviceId":"RHL","setting":{"serviceParameters":'
        '[{"key":"rhl","value":"light-flash"}]}}'
    )

    headers = api._get_headers(
        "/ms-remote-control/api/v1.0/remoteControl/control",
        "1710000000000",
        "12345678-1234-5678-9abc-1234567890ab",
        body,
        vehicle_metadata,
        signed_headers=EXTENDED_SIGNED_HEADERS,
        include_body_md5=True,
    )

    assert headers["authorization"] == "jwt-token"
    assert headers["x-signature"] == "jjP+aYI20FNz/U9eQ0pCYm5jQkTAKuPVQxyIm97CEYs="
    assert api.last_request_debug is not None
    assert api.last_signature_debug is not None
    assert api.last_signature_debug["body_md5"] == "K89mcaZVXZL0XV+VVQ2t3w=="
    assert (
        api.last_signature_debug["signature_base"]
        == "accept-language:zh_CN\n"
        "authorization:jwt-token\n"
        "content-type:application/json; charset=UTF-8\n"
        "x-api-signature-nonce:12345678-1234-5678-9abc-1234567890ab\n"
        "x-api-signature-version:2.1\n"
        "x-app-id:GEELYCNCH001M0001\n"
        "x-device-id:device-123\n"
        "x-platform:Android\n"
        "x-sales-platform:ZEEKR\n"
        "x-tenant-id:ZEEKR\n"
        "x-timestamp:1710000000000\n"
        "x-tsp-platform:4\n"
        "x-vehicle-brand:ZEEKR\n"
        "x-vehicle-identifier:B0ERbkAibJq5dVWO7dpuQYJ94PIx+gxOeJElI5Vjo7E=\n"
        "x-vehicle-series:REMxRQ==\n"
        "K89mcaZVXZL0XV+VVQ2t3w==\n"
        "POST\n"
        "/ms-remote-control/api/v1.0/remoteControl/control"
    )

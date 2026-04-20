"""Remote-control client for the new Geely gateway."""

from __future__ import annotations

import base64
import copy
import hashlib
import hmac
import json
import logging
import uuid

from datetime import datetime
from typing import Callable, Dict, Optional, Tuple
from urllib.parse import parse_qsl, urlparse

import requests

from .const import CONF_REMOTE_CONTROL_VEHICLES
from .zeekr_config import (
    BASE_URL_REMOTE_CONTROL,
    REMOTE_CONTROL_ACCEPT_LANGUAGE,
    REMOTE_CONTROL_APP_ID,
    REMOTE_CONTROL_APP_VERSION,
    REMOTE_CONTROL_DEVICE_BRAND,
    REMOTE_CONTROL_DEVICE_MODEL,
    REMOTE_CONTROL_DEVICE_OS_VERSION,
    REMOTE_CONTROL_HTTP_SECRET_KEY,
    REMOTE_CONTROL_PLATFORM,
    REMOTE_CONTROL_SALES_PLATFORM,
    REMOTE_CONTROL_SIGNATURE_VERSION,
    REMOTE_CONTROL_TENANT_ID,
    REMOTE_CONTROL_TSP_PLATFORM,
    REMOTE_CONTROL_VEHICLE_BRAND,
    REMOTE_CONTROL_VIN_IV,
    REMOTE_CONTROL_VIN_KEY,
    REQUEST_TIMEOUT,
)

_LOGGER = logging.getLogger(__name__)

try:
    from Crypto.Cipher import AES
    from Crypto.Util.Padding import pad
except ImportError:  # pragma: no cover - handled at runtime
    AES = None
    pad = None


SignatureCallback = Callable[[str, str, str, str, str], str]

CORE_SIGNED_HEADERS = frozenset(
    {
        "authorization",
        "accept-language",
        "content-type",
        "x-api-signature-nonce",
        "x-api-signature-version",
        "x-app-id",
        "x-device-id",
        "x-platform",
        "x-timestamp",
        "x-vehicle-identifier",
        "x-vehicle-series",
    }
)

EXTENDED_SIGNED_HEADERS = frozenset(
    CORE_SIGNED_HEADERS
    | {
        "x-sales-platform",
        "x-tenant-id",
        "x-tsp-platform",
        "x-vehicle-brand",
    }
)


class ZeekrRemoteControlAPI:
    """Client for the new Geely remote-control gateway."""

    def __init__(
        self,
        device_id: str,
        access_token: str = "",
        remote_control_vehicles: Optional[Dict[str, Dict[str, str]]] = None,
        signature_callback: Optional[SignatureCallback] = None,
        http_secret_key: str = REMOTE_CONTROL_HTTP_SECRET_KEY,
        vin_key: str = REMOTE_CONTROL_VIN_KEY,
        vin_iv: str = REMOTE_CONTROL_VIN_IV,
        jwt_token: str = "",
    ) -> None:
        self.access_token = access_token
        self.jwt_token = jwt_token
        self.device_id = device_id
        self.remote_control_vehicles = remote_control_vehicles or {}
        self.signature_callback = signature_callback
        self.http_secret_key = http_secret_key
        self.vin_key = vin_key
        self.vin_iv = vin_iv
        self.base_url = BASE_URL_REMOTE_CONTROL
        self.session = requests.Session()
        self.last_error_response: Optional[Dict] = None
        self.last_signature_debug: Optional[Dict[str, object]] = None
        self.last_request_debug: Optional[Dict[str, object]] = None

    def _serialize_body(self, payload: Dict) -> str:
        """Serialize JSON exactly as the mobile app does."""
        return json.dumps(payload, ensure_ascii=False, separators=(",", ":"))

    @staticmethod
    def _derive_signing_key(secret: str) -> str:
        """Mirror GLHttpApiSignKt.getKeySign(secret)."""
        if len(secret) <= 15:
            return secret
        return f"{secret[:6]}{secret[-10:]}"

    @staticmethod
    def _base64_encode(value: str) -> str:
        return base64.b64encode(value.encode("utf-8")).decode("utf-8")

    @staticmethod
    def _try_base64_text(value: str) -> Optional[str]:
        try:
            decoded = base64.b64decode(value, validate=True)
            text = decoded.decode("utf-8")
        except Exception:
            return None

        if not text:
            return None
        if any(ord(char) < 32 or ord(char) > 126 for char in text):
            return None
        return text

    def _aes_encrypt(self, plain_text: str) -> str:
        """Mirror AES/CBC/PKCS5Padding used in the Android gateway layer."""
        if AES is None or pad is None:  # pragma: no cover - import guard
            raise RuntimeError(
                "pycryptodome is required for remote-control VIN encryption."
            )

        cipher = AES.new(
            self.vin_key.encode("utf-8"),
            AES.MODE_CBC,
            iv=self.vin_iv.encode("utf-8"),
        )
        ciphertext = cipher.encrypt(pad(plain_text.encode("utf-8"), AES.block_size))
        return base64.b64encode(ciphertext).decode("utf-8")

    def build_vehicle_identifier(self, vin: str) -> str:
        """
        Build the final X-VEHICLE-IDENTIFIER header from the raw VIN.

        The real Android request places the once-encrypted Base64 value
        directly into the request header.
        """
        return self._aes_encrypt(vin)

    def build_vehicle_series(self, series_code: str) -> str:
        """
        Build the final X-VEHICLE-SERIES header.

        The real Android request sends the once-Base64-encoded series value
        directly. To keep the smoke test practical, this helper accepts any of:
        - raw series code, for example "DC1E"
        - once-encoded app value, for example "REMxRQ=="
        - double-encoded legacy value, for example "UkVNeFJRPT0="
        """
        decoded_once = self._try_base64_text(series_code)
        if decoded_once is None:
            return self._base64_encode(series_code)

        decoded_twice = self._try_base64_text(decoded_once)
        if decoded_twice is not None:
            return decoded_once

        return series_code

    def build_vehicle_metadata(self, vin: str, series_code: str) -> Dict[str, str]:
        """Build header-ready metadata for a vehicle."""
        return {
            "vehicle_identifier": self.build_vehicle_identifier(vin),
            "vehicle_series": self.build_vehicle_series(series_code),
        }

    @staticmethod
    def extract_series_code(vehicle: Dict[str, object]) -> Optional[str]:
        """
        Best-effort extraction of a raw series code from vehicle list payloads.

        The exact field name can vary, so the smoke test uses this helper and
        falls back to prompting if the response shape changes.
        """
        candidate_keys = (
            "seriesCode",
            "vehicleSeriesCode",
            "vehicleSeries",
            "series",
            "modelCode",
            "carTypeCode",
            "vehicleTypeCode",
        )
        for key in candidate_keys:
            value = vehicle.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
        return None

    @staticmethod
    def _canonicalize_json_body(body: str) -> str:
        if not body:
            return ""
        try:
            parsed = json.loads(body)
        except Exception:
            return body
        return json.dumps(parsed, sort_keys=True, separators=(",", ":"))

    def _body_for_md5(self, body: str, canonicalize: bool = True) -> str:
        return self._canonicalize_json_body(body) if canonicalize else body

    def _body_md5(self, body: str, canonicalize: bool = True) -> str:
        body_to_hash = self._body_for_md5(body, canonicalize=canonicalize)
        if not body_to_hash:
            return ""
        digest = hashlib.md5(body_to_hash.encode("utf-8")).digest()
        return base64.b64encode(digest).decode("utf-8")

    @staticmethod
    def _canonicalize_headers(
        headers: Dict[str, str],
        signed_headers: Optional[frozenset[str]] = None,
    ) -> str:
        lines = []
        for key, value in headers.items():
            lower_key = key.lower()
            if lower_key == "x-signature":
                continue
            if signed_headers is not None and lower_key not in signed_headers:
                continue
            lines.append(f"{lower_key}:{value}")
        lines.sort()
        return "".join(f"{line}\n" for line in lines)

    @staticmethod
    def _canonicalize_query(path: str) -> str:
        parsed = urlparse(path)
        if not parsed.query:
            return ""

        items = parse_qsl(parsed.query, keep_blank_values=True)
        items.sort()
        return "&".join(f"{key}={value}" for key, value in items)

    @staticmethod
    def _describe_signed_headers(
        headers: Dict[str, str],
        signed_headers: Optional[frozenset[str]],
    ) -> object:
        if signed_headers is None:
            return "<all headers>"

        included = []
        for key in headers:
            lower_key = key.lower()
            if lower_key == "x-signature":
                continue
            if lower_key in signed_headers:
                included.append(lower_key)
        return sorted(included)

    def _format_authorization(self, include_bearer: bool = False) -> str:
        token = self.access_token.strip() or self.jwt_token.strip()
        if not token:
            return ""
        if token.lower().startswith("bearer "):
            return token if include_bearer else token[7:]
        return f"Bearer {token}" if include_bearer else token

    def _calculate_signature(
        self,
        method: str,
        path: str,
        timestamp: str,
        nonce: str,
        body: str,
        headers: Optional[Dict[str, str]] = None,
        signed_headers: Optional[frozenset[str]] = None,
        include_body_md5: bool = True,
        canonicalize_body_for_md5: bool = True,
        always_include_query_newline: bool = False,
    ) -> Dict[str, object]:
        """
        Build the exact signature inputs for the 2.1 gateway.

        The mainland-China Android app signs lowercase sorted headers, sorted
        query params, the HTTP method, and the path using HMAC-SHA256, then
        Base64-encodes the digest. The exact body participation is still under
        investigation, so callers can toggle whether an MD5 is inserted.
        """
        del timestamp, nonce

        if headers is None:
            raise ValueError("headers are required to calculate the 2.1 signature")

        header_string = self._canonicalize_headers(headers, signed_headers=signed_headers)
        query_string = self._canonicalize_query(path)
        canonical_path = urlparse(path).path
        body_for_md5 = (
            self._body_for_md5(body, canonicalize=canonicalize_body_for_md5)
            if include_body_md5
            else ""
        )

        signature_base = header_string
        if query_string or always_include_query_newline:
            signature_base += f"{query_string}\n"
        body_md5 = self._body_md5(body, canonicalize=canonicalize_body_for_md5)
        if not include_body_md5:
            body_md5 = ""
        if body_md5:
            signature_base += f"{body_md5}\n"
        signature_base += f"{method.upper()}\n{canonical_path}"

        signing_key = self._derive_signing_key(self.http_secret_key)
        digest = hmac.new(
            signing_key.encode("utf-8"),
            signature_base.encode("utf-8"),
            hashlib.sha256,
        ).digest()
        signature = base64.b64encode(digest).decode("utf-8")
        return {
            "method": method.upper(),
            "path": canonical_path,
            "query": query_string,
            "signed_headers": self._describe_signed_headers(headers, signed_headers),
            "canonical_headers": header_string,
            "body": body,
            "body_for_md5": body_for_md5,
            "body_md5": body_md5,
            "always_include_query_newline": always_include_query_newline,
            "signature_base": signature_base,
            "signature": signature,
        }

    def _resolve_signature(
        self,
        method: str,
        path: str,
        timestamp: str,
        nonce: str,
        body: str,
        headers: Optional[Dict[str, str]] = None,
        signed_headers: Optional[frozenset[str]] = None,
        include_body_md5: bool = True,
        canonicalize_body_for_md5: bool = True,
        always_include_query_newline: bool = False,
    ) -> str:
        if self.signature_callback is not None:
            signature = self.signature_callback(method, path, timestamp, nonce, body)
            self.last_signature_debug = {
                "method": method.upper(),
                "path": urlparse(path).path,
                "query": self._canonicalize_query(path),
                "signed_headers": self._describe_signed_headers(headers or {}, signed_headers),
                "canonical_headers": self._canonicalize_headers(
                    headers or {},
                    signed_headers=signed_headers,
                ),
                "body": body,
                "body_for_md5": "",
                "body_md5": "",
                "always_include_query_newline": always_include_query_newline,
                "signature_base": "<provided by signature_callback>",
                "signature": signature,
            }
            return signature

        signature_debug = self._calculate_signature(
            method,
            path,
            timestamp,
            nonce,
            body,
            headers=headers,
            signed_headers=signed_headers,
            include_body_md5=include_body_md5,
            canonicalize_body_for_md5=canonicalize_body_for_md5,
            always_include_query_newline=always_include_query_newline,
        )
        self.last_signature_debug = signature_debug
        return str(signature_debug["signature"])

    def _get_vehicle_metadata(self, vin: str) -> Optional[Dict[str, str]]:
        metadata = self.remote_control_vehicles.get(vin)
        if not metadata:
            _LOGGER.warning("No remote-control metadata found for VIN %s", vin)
            return None

        if not metadata.get("vehicle_identifier") or not metadata.get("vehicle_series"):
            _LOGGER.warning("Remote-control metadata for VIN %s is incomplete", vin)
            return None

        return metadata

    def _get_headers(
        self,
        path: str,
        timestamp: str,
        nonce: str,
        body: str,
        vehicle_metadata: Dict[str, str],
        signed_headers: Optional[frozenset[str]] = None,
        include_body_md5: bool = True,
        canonicalize_body_for_md5: bool = True,
        include_bearer: bool = False,
        always_include_query_newline: bool = False,
    ) -> Dict[str, str]:
        authorization = self._format_authorization(include_bearer=include_bearer)
        headers = {
            "accept": "application/json; charset=UTF-8",
            "accept-language": REMOTE_CONTROL_ACCEPT_LANGUAGE,
            "content-type": "application/json; charset=UTF-8",
            "x-api-signature-nonce": nonce,
            "x-api-signature-version": REMOTE_CONTROL_SIGNATURE_VERSION,
            "x-app-id": REMOTE_CONTROL_APP_ID,
            "x-app-version": REMOTE_CONTROL_APP_VERSION,
            "x-device-brand": REMOTE_CONTROL_DEVICE_BRAND,
            "x-device-id": self.device_id,
            "x-device-model": REMOTE_CONTROL_DEVICE_MODEL,
            "x-device-os-version": REMOTE_CONTROL_DEVICE_OS_VERSION,
            "x-platform": REMOTE_CONTROL_PLATFORM,
            "x-sales-platform": REMOTE_CONTROL_SALES_PLATFORM,
            "x-tenant-id": REMOTE_CONTROL_TENANT_ID,
            "x-timestamp": timestamp,
            "x-tsp-platform": REMOTE_CONTROL_TSP_PLATFORM,
            "x-vehicle-brand": REMOTE_CONTROL_VEHICLE_BRAND,
        }
        if authorization:
            headers["authorization"] = authorization
        if vehicle_metadata.get("vehicle_identifier"):
            headers["x-vehicle-identifier"] = vehicle_metadata["vehicle_identifier"]
        if vehicle_metadata.get("vehicle_series"):
            headers["x-vehicle-series"] = vehicle_metadata["vehicle_series"]
            headers["x-signature"] = self._resolve_signature(
            "POST",
            path,
            timestamp,
            nonce,
            body,
            headers=headers,
            signed_headers=signed_headers,
            include_body_md5=include_body_md5,
            canonicalize_body_for_md5=canonicalize_body_for_md5,
            always_include_query_newline=always_include_query_newline,
        )
        self.last_request_debug = {
            "path": path,
            "timestamp": timestamp,
            "nonce": nonce,
            "request_body": body,
            "request_headers": copy.deepcopy(headers),
            "signed_headers_filter": self._describe_signed_headers(headers, signed_headers),
            "include_body_md5": include_body_md5,
            "canonicalize_body_for_md5": canonicalize_body_for_md5,
            "include_bearer": include_bearer,
            "always_include_query_newline": always_include_query_newline,
            "signature_debug": copy.deepcopy(self.last_signature_debug),
        }
        return headers

    @staticmethod
    def _signature_variants() -> list[dict[str, object]]:
        return [
            {
                "name": "all_headers_raw_auth_raw_body_md5",
                "signed_headers": None,
                "include_body_md5": True,
                "canonicalize_body_for_md5": False,
                "include_bearer": False,
            },
            {
                "name": "all_headers_raw_auth_canonical_body_md5",
                "signed_headers": None,
                "include_body_md5": True,
                "canonicalize_body_for_md5": True,
                "include_bearer": False,
            },
            {
                "name": "all_headers_raw_auth_without_body_md5",
                "signed_headers": None,
                "include_body_md5": False,
                "canonicalize_body_for_md5": True,
                "include_bearer": False,
                "always_include_query_newline": False,
            },
            {
                "name": "all_headers_raw_auth_without_body_md5_empty_query_line",
                "signed_headers": None,
                "include_body_md5": False,
                "canonicalize_body_for_md5": True,
                "include_bearer": False,
                "always_include_query_newline": True,
            },
            {
                "name": "extended_allowlist_raw_auth_raw_body_md5",
                "signed_headers": EXTENDED_SIGNED_HEADERS,
                "include_body_md5": True,
                "canonicalize_body_for_md5": False,
                "include_bearer": False,
                "always_include_query_newline": False,
            },
            {
                "name": "extended_allowlist_raw_auth_canonical_body_md5",
                "signed_headers": EXTENDED_SIGNED_HEADERS,
                "include_body_md5": True,
                "canonicalize_body_for_md5": True,
                "include_bearer": False,
                "always_include_query_newline": False,
            },
            {
                "name": "extended_allowlist_raw_auth_without_body_md5_empty_query_line",
                "signed_headers": EXTENDED_SIGNED_HEADERS,
                "include_body_md5": False,
                "canonicalize_body_for_md5": True,
                "include_bearer": False,
                "always_include_query_newline": True,
            },
            {
                "name": "core_allowlist_raw_auth_raw_body_md5",
                "signed_headers": CORE_SIGNED_HEADERS,
                "include_body_md5": True,
                "canonicalize_body_for_md5": False,
                "include_bearer": False,
                "always_include_query_newline": False,
            },
            {
                "name": "core_allowlist_raw_auth_canonical_body_md5",
                "signed_headers": CORE_SIGNED_HEADERS,
                "include_body_md5": True,
                "canonicalize_body_for_md5": True,
                "include_bearer": False,
                "always_include_query_newline": False,
            },
            {
                "name": "core_allowlist_raw_auth_without_body_md5_empty_query_line",
                "signed_headers": CORE_SIGNED_HEADERS,
                "include_body_md5": False,
                "canonicalize_body_for_md5": True,
                "include_bearer": False,
                "always_include_query_newline": True,
            },
        ]

    def find_car(
        self,
        vin: str,
        debug_callback: Optional[Callable[[Dict[str, object]], None]] = None,
    ) -> Tuple[bool, Optional[str]]:
        """Trigger the 'find car' action and return the task session ID."""
        vehicle_metadata = self._get_vehicle_metadata(vin)
        if vehicle_metadata is None:
            return False, None

        path = "/ms-remote-control/api/v1.0/remoteControl/control"
        url = f"{self.base_url}{path}"
        payload = {
            "command": "",
            "serviceId": "RHL",
            "setting": {
                "serviceParameters": [
                    {
                        "key": "rhl",
                        "value": "light-flash",
                    }
                ]
            },
        }
        body = self._serialize_body(payload)
        self.last_error_response = None

        for variant in self._signature_variants():
            timestamp = str(int(datetime.now().timestamp() * 1000))
            nonce = str(uuid.uuid4())
            try:
                response = self.session.post(
                    url,
                    data=body,
                    headers=self._get_headers(
                        path,
                        timestamp,
                        nonce,
                        body,
                        vehicle_metadata,
                        signed_headers=variant["signed_headers"],
                        include_body_md5=bool(variant["include_body_md5"]),
                        canonicalize_body_for_md5=bool(
                            variant["canonicalize_body_for_md5"]
                        ),
                        include_bearer=bool(variant["include_bearer"]),
                        always_include_query_newline=bool(
                            variant.get("always_include_query_newline", False)
                        ),
                    ),
                    timeout=REQUEST_TIMEOUT,
                )
                data = response.json()
            except requests.exceptions.RequestException as exc:
                _LOGGER.error("Remote-control request failed: %s", exc)
                return False, None

            if str(data.get("code")) == "0":
                session_id = data.get("data", {}).get("sessionId")
                _LOGGER.info(
                    "Find-car request accepted for VIN %s with %s, session=%s",
                    vin,
                    variant["name"],
                    session_id,
                )
                self.last_error_response = None
                return True, session_id

            self.last_error_response = data
            if self.last_request_debug is not None:
                self.last_request_debug["variant_name"] = str(variant["name"])
                self.last_request_debug["response_json"] = copy.deepcopy(data)
                if debug_callback is not None:
                    debug_callback(copy.deepcopy(self.last_request_debug))
            if str(data.get("code")) != "00A06":
                _LOGGER.error("Find-car request failed for VIN %s: %s", vin, data)
                return False, None

            _LOGGER.warning(
                "Find-car signature variant %s failed for VIN %s: %s",
                variant["name"],
                vin,
                data,
            )

        _LOGGER.error("Find-car request failed for VIN %s: %s", vin, self.last_error_response)
        return False, None

    @staticmethod
    def build_empty_vehicle_metadata() -> Dict[str, Dict[str, str]]:
        """Return the default structure stored in config entries."""
        return {}

    @classmethod
    def from_entry_data(cls, entry_data: Dict[str, str]) -> "ZeekrRemoteControlAPI":
        """Build a remote-control client from Home Assistant entry data."""
        return cls(
            access_token=entry_data.get("accessToken", ""),
            device_id=entry_data.get("device_id", ""),
            remote_control_vehicles=entry_data.get(CONF_REMOTE_CONTROL_VEHICLES, {}),
            jwt_token=entry_data.get("jwtToken", ""),
        )

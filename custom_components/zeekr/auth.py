# auth.py
"""Authentication for the Zeekr API."""
import hmac
import base64
import requests
import json
import uuid
import hashlib
import random
import copy
from typing import Callable, Optional, Dict, Tuple
from datetime import datetime
from .zeekr_config import (
    BASE_URL_TOC, X_CA_SECRET, X_CA_KEY, APP_VERSION,
    PHONE_MODEL, PHONE_VERSION, APP_TYPE, REQUEST_TIMEOUT,
    REGION_CODE, BASE_URL_SECURE, BASE_URL_REMOTE_CONTROL_AUTH, HMAC_SECRET
)
from .zeekr_storage import token_storage
from .remote_control_api import ZeekrRemoteControlAPI, EXTENDED_SIGNED_HEADERS


class ZeekrAuth:
    """Authentication client for Zeekr."""

    def __init__(self):
        self.device_id = str(uuid.uuid4())
        self.base_url = BASE_URL_TOC
        self.session = requests.Session()
        self.mobile = None  # Persist the mobile number
        self.jwt_token = None  # Persist the JWT token used by the remote-control gateway

    def _generate_signature(self, timestamp: str, nonce: int) -> str:
        """
        Generate the signature for a TOC API request.

        Args:
            timestamp: Current time in milliseconds
            nonce: Random number

        Returns:
            SHA1 signature hash
        """
        # Sort the signature components
        arr = [timestamp, str(nonce), X_CA_SECRET]
        arr.sort()

        # Join into a single string
        combined_str = ''.join(arr)

        # Build the SHA1 hash
        sha1_hash = hashlib.sha1(combined_str.encode()).hexdigest()
        return sha1_hash

    def _get_headers(self, timestamp: str, nonce: int) -> Dict[str, str]:
        """
        Build request headers.

        Args:
            timestamp: Current time in milliseconds
            nonce: Random number

        Returns:
            Dictionary of headers
        """
        return {
            'User-Agent': f'ZeekrLife/{APP_VERSION} (iPhone; iOS {PHONE_VERSION}; Scale/3.00){self.device_id}',
            'request-original': 'zeekr-app',
            'Accept-Language': 'zh-Hans-CN;q=1, en-CN;q=0.9',
            'Content-Type': 'application/json',
            'x_ca_secret': X_CA_SECRET,
            'Accept': '*/*',
            'riskToken': 'G4y5f5YrG1BEGxRBBEKF73higM/lOd6e',
            'Version': '2',
            'WorkspaceId': 'prod',
            'x_ca_key': X_CA_KEY,
            'app_type': APP_TYPE,
            'app_version': APP_VERSION,
            'phone_model': PHONE_MODEL,
            'phone_version': PHONE_VERSION,
            'x_gray_code': 'gray74',
            'x_ca_timestamp': timestamp,
            'x_ca_nonce': str(nonce),
            'x_ca_sign': self._generate_signature(timestamp, nonce),
            'app_code': 'toc_ios_zeekrapp',
            'device_id': self.device_id,
        }

    def request_sms_code(self, mobile: str) -> Tuple[bool, str]:
        """
        Request the SMS code used for sign-in.

        Args:
            mobile: Phone number in the format "13812345678"

        Returns:
            Tuple of (success, message)
        """
        print(f"\n📱 Requesting SMS code for {mobile}...")

        timestamp = str(int(datetime.now().timestamp() * 1000))
        nonce = int(random.random() * 1e8)

        url = f"{self.base_url}/zeekrlife-app-user/v1/user/pub/sms/authCode"
        params = {
            'mobile': mobile,
            'x_ca_time': timestamp,
            'regionCode': REGION_CODE,
        }

        try:
            response = self.session.get(
                url,
                params=params,
                headers=self._get_headers(timestamp, nonce),
                timeout=REQUEST_TIMEOUT
            )

            data = response.json()

            if data.get('code') == '000000':
                print("✅ SMS code sent!")
                return True, "SMS code sent successfully"
            else:
                error_msg = data.get('message', 'Unknown error')
                print(f"❌ Error: {error_msg}")
                return False, error_msg

        except requests.exceptions.RequestException as e:
            print(f"❌ Request error: {e}")
            return False, str(e)

    def login_with_sms(self, mobile: str, sms_code: str) -> Tuple[bool, Optional[Dict]]:
        """
        Log in with the SMS code (STEP 1).

        Args:
            mobile: Phone number
            sms_code: SMS code from the message

        Returns:
            Tuple of (success, token dictionary or None)
        """
        print(f"\n🔐 Attempting SMS-code login...")

        timestamp = str(int(datetime.now().timestamp() * 1000))
        nonce = int(random.random() * 1e8)

        url = f"{self.base_url}/zeekrlife-app-user/v1/user/pub/login/mobile"

        payload = {
            'mobile': mobile,
            'deviceId': self.device_id,
            'smsCode': sms_code,
            'channel': 2,
            'x_ca_time': timestamp,
            'deviceName': PHONE_MODEL,
            'skipSmsCode': '0',
            'regionCode': REGION_CODE,
            'ip': '192.168.1.1',
        }

        try:
            response = self.session.post(
                url,
                json=payload,
                headers=self._get_headers(timestamp, nonce),
                timeout=REQUEST_TIMEOUT
            )

            data = response.json()

            if data.get('code') == '000000':
                jwt_token = data.get('data', {}).get('jwtToken')
                tokens = {
                    'jwtToken': jwt_token,
                    'mobile': mobile,
                    'device_id': self.device_id,
                }
                self.mobile = mobile  # Persist the mobile number
                self.jwt_token = jwt_token
                print("✅ Authentication successful!")
                return True, tokens
            else:
                error_msg = data.get('message', 'Unknown error')
                print(f"❌ Authentication error: {error_msg}")
                return False, None

        except requests.exceptions.RequestException as e:
            print(f"❌ Request error: {e}")
            return False, None

    def get_auth_code(self, jwt_token: str) -> Tuple[bool, Optional[str]]:
        """
        Retrieve the Auth Code (YIKAT_NEW) using the JWT token (STEP 2).

        Args:
            jwt_token: JWT token from login_with_sms

        Returns:
            Tuple of (success, Auth Code or None)
        """
        print(f"\n🔑 Retrieving Auth Code...")

        timestamp = str(int(datetime.now().timestamp() * 1000))
        nonce = int(random.random() * 1e8)

        url = f"{self.base_url}/zeekrlife-mp-auth2/v1/auth/accessCodeList"
        params = {
            'envType': '3',
        }

        # Build headers with the JWT token
        headers = self._get_headers(timestamp, nonce)
        headers['Authorization'] = jwt_token

        try:
            response = self.session.get(
                url,
                params=params,
                headers=headers,
                timeout=REQUEST_TIMEOUT
            )

            data = response.json()

            if data.get('code') == '000000':
                auth_code = data.get('data', {}).get('YIKAT_NEW')
                if auth_code:
                    print(f"✅ Auth Code received: {auth_code[:20]}...")
                    return True, auth_code
                else:
                    print("❌ Auth Code not found in the response")
                    return False, None
            else:
                error_msg = data.get('message', 'Unknown error')
                print(f"❌ Failed to get Auth Code: {error_msg}")
                return False, None

        except requests.exceptions.RequestException as e:
            print(f"❌ Request error: {e}")
            return False, None

    def login_with_auth_code(self, auth_code: str) -> Tuple[bool, Optional[Dict]]:
        """
        Authenticate with the Auth Code (STEP 3).
        Retrieve accessToken, refreshToken, userId, and clientId.

        Args:
            auth_code: Auth Code returned by get_auth_code

        Returns:
            Tuple of (success, full token dictionary or None)
        """
        print(f"\n🔐 Authenticating with Auth Code...")

        import hmac
        import base64
        from urllib.parse import urlencode

        timestamp = str(int(datetime.now().timestamp() * 1000))
        nonce = str(uuid.uuid4()).upper()

        # Use BASE_URL_SECURE for this request
        url = f"{BASE_URL_SECURE}/auth/account/session/secure"

        params = {
            'identity_type': 'zeekr',
        }

        payload = {
            'authCode': auth_code,
        }

        # ========== CALCULATE THE SIGNATURE ==========
        # Sort query parameters
        query_string = urlencode(sorted(params.items()))

        # JSON payload
        body = json.dumps(payload)

        # MD5 hash of the body (Base64)
        body_md5 = base64.b64encode(
            hashlib.md5(body.encode()).digest()
        ).decode()

        # Build the string to sign
        string_to_sign = '\n'.join([
            'application/json;responseformat=3',
            f'x-api-signature-nonce:{nonce}',
            'x-api-signature-version:1.0',
            '',
            query_string,
            body_md5,
            timestamp,
            'POST',
            '/auth/account/session/secure',
        ])

        print(f"[DEBUG] String to sign:\n{string_to_sign}\n")

        # Sign using HMAC-SHA1
        signature = base64.b64encode(
            hmac.new(
                HMAC_SECRET.encode(),
                string_to_sign.encode(),
                hashlib.sha1
            ).digest()
        ).decode()

        print(f"[DEBUG] Signature: {signature}\n")

        # Build SECURE API headers with the signature
        headers = {
            'content-type': 'application/json',
            'x-api-signature-version': '1.0',
            'x-app-id': 'ZEEKRAPP',
            'user-agent': f'ZeekrLife/{APP_VERSION} (iPhone; iOS {PHONE_VERSION}; Scale/3.00)',
            'x-device-model': 'iPhone',
            'x-device-manufacture': 'Apple',
            'x-agent-type': 'iOS',
            'x-device-type': 'mobile',
            'platform': 'NON-CMA',
            'x-env-type': 'production',
            'accept-language': 'zh-Hans-CN;q=1, en-CN;q=0.9',
            'x-agent-version': PHONE_VERSION,
            'accept': 'application/json;responseformat=3',
            'x-device-brand': 'Apple',
            'x-operator-code': 'ZEEKR',
            'x-device-identifier': self.device_id,
            'x-timestamp': timestamp,
            'x-api-signature-nonce': nonce,
            'x-signature': signature,
        }

        try:
            # Build the URL with query parameters
            full_url = f"{url}?{query_string}"

            print(f"[DEBUG] Full URL: {full_url}")
            print(f"[DEBUG] Body: {body}")

            response = self.session.post(
                full_url,
                data=body,  # Use raw data instead of json for full payload control
                headers=headers,
                timeout=REQUEST_TIMEOUT
            )

            print(f"[DEBUG] Response status: {response.status_code}")

            data = response.json()
            print(f"[DEBUG] Response from auth/account/session/secure: {json.dumps(data, indent=2, ensure_ascii=False)}")

            if data.get('code') == 1000 or str(data.get('code')) == '1000':
                session_data = data.get('data', {})
                tokens = {
                    'jwtToken': self.jwt_token or '',
                    'accessToken': session_data.get('accessToken'),
                    'refreshToken': session_data.get('refreshToken'),
                    'userId': session_data.get('userId'),
                    'clientId': session_data.get('clientId'),
                    'mobile': self.mobile if self.mobile else '',
                    'device_id': self.device_id,
                }
                print("✅ Auth Code authentication successful!")
                return True, tokens
            else:
                error_msg = data.get('message', 'Unknown error')
                print(f"❌ Auth Code authentication failed: {error_msg}")
                return False, None

        except requests.exceptions.RequestException as e:
            print(f"❌ Request error: {e}")
            return False, None

    def exchange_gateway_token(
        self,
        auth_code: str,
        vehicle_identifier: str,
        vehicle_series: str,
        debug_callback: Optional[Callable[[Dict[str, object]], None]] = None,
    ) -> Tuple[bool, Optional[Dict]]:
        """
        Exchange an auth code for the Geely gateway token used by remote-control APIs.

        The official Android app calls:
        POST https://gric-api.geely.com/ms-midground-user/api/v1.0/user/auth/get/token
        with body {"authCode":"...","identityType":"1"} before issuing remote-control requests.
        """
        print("\n🔐 Exchanging auth code for remote-control gateway token...")

        path = "/ms-midground-user/api/v1.0/user/auth/get/token"
        url = f"{BASE_URL_REMOTE_CONTROL_AUTH}{path}"
        payload = {
            "authCode": auth_code,
            "identityType": "1",
        }
        body = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))

        signer = ZeekrRemoteControlAPI(
            device_id=self.device_id,
            access_token="",
            remote_control_vehicles={},
            jwt_token="",
        )
        vehicle_metadata = {
            "vehicle_identifier": vehicle_identifier,
            "vehicle_series": vehicle_series,
        }

        last_error = None
        for variant in signer._signature_variants():
            timestamp = str(int(datetime.now().timestamp() * 1000))
            nonce = str(uuid.uuid4())
            headers = signer._get_headers(
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
                include_bearer=False,
            )
            try:
                response = self.session.post(
                    url,
                    data=body,
                    headers=headers,
                    timeout=REQUEST_TIMEOUT,
                )
                data = response.json()
            except requests.exceptions.RequestException as e:
                print(f"❌ Gateway token request error: {e}")
                return False, None

            if str(data.get("code")) == "0":
                token_data = data.get("data", {})
                gateway_token = (
                    token_data.get("accessToken")
                    or token_data.get("token")
                    or token_data.get("authorization")
                )
                if not gateway_token:
                    print("❌ Gateway token response did not contain a usable token.")
                    return False, token_data

                result = {
                    "gatewayAccessToken": gateway_token,
                    "raw": token_data,
                    "signatureVariant": variant["name"],
                }
                print(
                    f"✅ Gateway token exchange succeeded with {variant['name']}!"
                )
                return True, result

            last_error = data
            if signer.last_request_debug is not None:
                signer.last_request_debug["variant_name"] = str(variant["name"])
                signer.last_request_debug["response_json"] = copy.deepcopy(data)
                if debug_callback is not None:
                    debug_callback(copy.deepcopy(signer.last_request_debug))
            if str(data.get("code")) != "00A06":
                print(f"❌ Gateway token exchange failed: {data}")
                return False, data

            print(
                "⚠️ Gateway token signature variant "
                f"{variant['name']} failed: {data}"
            )

        print(f"❌ Gateway token exchange failed after trying all variants: {last_error}")
        return False, last_error

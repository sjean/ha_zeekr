# zeekr_api.py
"""
Work with the Zeekr API to retrieve vehicle data
"""
import requests
import json
import uuid
import hmac
import hashlib
import base64
from typing import Optional, Dict, List, Tuple
from datetime import datetime
from urllib.parse import urlencode
from .zeekr_config import (
    BASE_URL_SECURE, HMAC_SECRET, APP_VERSION, PHONE_MODEL,
    PHONE_VERSION, REQUEST_TIMEOUT
)
from .zeekr_storage import token_storage


class ZeekrAPI:
    """Client for the Zeekr SECURE API."""

    def __init__(self, access_token: str, user_id: str, client_id: str, device_id: str):
        """
        Initialize the API client.

        Args:
            access_token: Access token for authentication
            user_id: User ID
            client_id: Client ID
            device_id: Device ID
        """
        self.access_token = access_token
        self.user_id = user_id
        self.client_id = client_id
        self.device_id = device_id
        self.base_url = BASE_URL_SECURE
        self.session = requests.Session()

    def _calculate_signature(self, method: str, path: str, timestamp: str,
                             nonce: str, body: str = '', query_string: str = '') -> str:
        """
        Calculate the signature for a SECURE API request.

        Args:
            method: HTTP method (GET, POST, PUT, etc.)
            path: Endpoint path (for example /remote-control/vehicle/status/VIN)
            timestamp: Current time in milliseconds
            nonce: Unique UUID
            body: Request body (JSON string)
            query_string: Sorted query parameters

        Returns:
            Base64-encoded HMAC-SHA1 signature
        """
        # Calculate the Base64-encoded MD5 body hash
        if body:
            body_md5 = base64.b64encode(
                hashlib.md5(body.encode()).digest()
            ).decode()
        else:
            body_md5 = base64.b64encode(
                hashlib.md5(b'').digest()
            ).decode()

        # Build the string to sign in the required order
        # This order is important!
        string_to_sign = '\n'.join([
            'application/json;responseformat=3',
            f'x-api-signature-nonce:{nonce}',
            'x-api-signature-version:1.0',
            '',
            query_string,
            body_md5,
            timestamp,
            method.upper(),
            path,
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

        return signature

    def _get_headers(self, method: str, path: str, timestamp: str,
                     nonce: str, body: str = '', query_string: str = '') -> Dict[str, str]:
        """
        Build headers for a SECURE API request.

        Args:
            method: HTTP method
            path: Endpoint path
            timestamp: Current time in milliseconds
            nonce: Unique UUID
            body: Request body
            query_string: Query parameters

        Returns:
            Dictionary of headers
        """
        signature = self._calculate_signature(
            method, path, timestamp, nonce, body, query_string
        )

        return {
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
            'authorization': self.access_token,
            'x-client-id': self.client_id,
            'x-timestamp': timestamp,
            'x-api-signature-nonce': nonce,
            'x-signature': signature,
        }

    def get_vehicle_entries(self) -> Tuple[bool, Optional[List[Dict]]]:
        """
        Fetch the raw vehicle list payload for the current user.

        Returns:
            Tuple of (success, vehicle entry list or None)
        """
        print("\n🚗 Fetching the vehicle list...")

        timestamp = str(int(datetime.now().timestamp() * 1000))
        nonce = str(uuid.uuid4()).upper()

        path = '/device-platform/user/vehicle/secure'
        params = {
            'id': self.user_id,
            'needSharedCar': '1'
        }

        query_string = urlencode(sorted(params.items()))
        url = f"{self.base_url}{path}?{query_string}"

        try:
            response = self.session.get(
                url,
                headers=self._get_headers('GET', path, timestamp, nonce, '', query_string),
                timeout=REQUEST_TIMEOUT
            )

            data = response.json()

            if data.get('code') == '1000':
                vehicles = data.get('data', {}).get('list', [])
                print(f"✅ Found {len(vehicles)} vehicles")
                return True, vehicles

            error_msg = data.get('message', 'Unknown error')
            print(f"❌ Failed to fetch vehicles: {error_msg}")
            return False, None

        except requests.exceptions.RequestException as e:
            print(f"❌ Request error: {e}")
            return False, None

    def get_vehicles(self) -> Tuple[bool, Optional[List[str]]]:
        """
        Fetch the list of vehicle VINs for the user.

        Returns:
            Tuple of (success, VIN list or None)
        """
        success, vehicles = self.get_vehicle_entries()
        if not success or vehicles is None:
            return False, None

        vins = [vehicle.get('vin') for vehicle in vehicles if vehicle.get('vin')]
        print(f"✅ Vehicle VINs: {vins}")
        return True, vins

    def get_vehicle_status(self, vin: str) -> Tuple[bool, Optional[Dict]]:
        """
        Fetch the status of a specific vehicle.

        Args:
            vin: Vehicle VIN

        Returns:
            Tuple of (success, status dictionary or None)
        """
        print(f"\n📊 Fetching status for vehicle {vin}...")

        timestamp = str(int(datetime.now().timestamp() * 1000))
        nonce = str(uuid.uuid4()).upper()

        path = f'/remote-control/vehicle/status/{vin}'
        params = {
            'latest': 'Local',
            'target': 'basic,more',
            'userId': self.user_id,
        }

        # Sort parameters and build the query string
        query_string = urlencode(sorted(params.items()))

        url = f"{self.base_url}{path}?{query_string}"

        try:
            response = self.session.get(
                url,
                headers=self._get_headers('GET', path, timestamp, nonce, '', query_string),
                timeout=REQUEST_TIMEOUT
            )

            data = response.json()

            if data.get('code') == '1000':
                vehicle_status = data.get('data', {}).get('vehicleStatus', {})
                print(f"✅ Status fetched for {vin}")
                return True, vehicle_status
            else:
                error_msg = data.get('message', 'Unknown error')
                print(f"❌ Failed to fetch status: {error_msg} (code: {data.get('code')})")
                return False, None

        except requests.exceptions.RequestException as e:
            print(f"❌ Request error: {e}")
            return False, None

    def get_all_vehicles_status(self) -> Tuple[bool, Optional[Dict[str, Dict]]]:
        """
        Fetch status for all user vehicles.

        Returns:
            Tuple of (success, {VIN: status} dictionary or None)
        """
        print("\n" + "=" * 50)
        print("🔄 FETCH STATUS FOR ALL VEHICLES")
        print("=" * 50)

        # First fetch the VIN list
        success, vehicles = self.get_vehicles()
        if not success or not vehicles:
            return False, None

        # Then fetch each vehicle status
        all_status = {}
        for vin in vehicles:
            success, status = self.get_vehicle_status(vin)
            if success and status:
                all_status[vin] = status

        return True, all_status if all_status else None

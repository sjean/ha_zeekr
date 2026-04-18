# custom_components/zeekr/coordinator.py
"""Data coordinator for the Zeekr integration."""

import logging
import sys
import os
import json
from datetime import timedelta, datetime
from typing import Dict, Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

# Ensure local package imports work
current_dir = os.path.dirname(__file__)
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

# Import after adjusting the path
from .const import DOMAIN, DEFAULT_SCAN_INTERVAL

_LOGGER = logging.getLogger(__name__)


class ZeekrDataCoordinator(DataUpdateCoordinator):
    """Class to manage fetching Zeekr data from API"""

    def __init__(self, hass: HomeAssistant, api_client, responses_dir: str = None):
        """Initialize the coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=DEFAULT_SCAN_INTERVAL),
        )

        self.api_client = api_client
        self.responses_dir = responses_dir
        self.last_response = None  # Keep the latest response

    async def _async_update_data(self) -> Dict[str, Any]:
        """Fetch data from Zeekr API."""
        try:
            _LOGGER.debug("Fetching Zeekr vehicle data")

            # Fetch the list of vehicles
            success, vehicles = await self.hass.async_add_executor_job(
                self.api_client.get_vehicles
            )

            if not success:
                raise UpdateFailed("Failed to fetch vehicle list")

            # Fetch the status for each vehicle
            vehicles_data = {}
            for vin in vehicles:
                success, status = await self.hass.async_add_executor_job(
                    self.api_client.get_vehicle_status, vin
                )

                if success and status:
                    vehicles_data[vin] = status

                    # Save the response asynchronously
                    await self._async_save_response_to_file(vin, status)
                else:
                    _LOGGER.warning(f"Failed to fetch status for {vin}")

            if not vehicles_data:
                raise UpdateFailed("No vehicle data received")

            _LOGGER.debug(f"Successfully fetched data for {len(vehicles_data)} vehicles")

            return vehicles_data

        except Exception as err:
            _LOGGER.error(f"Error fetching Zeekr data: {err}")
            raise UpdateFailed(f"Error communicating with Zeekr API: {err}")

    async def _async_save_response_to_file(self, vin: str, data: Dict) -> None:
        """
        Asynchronously save the server response to a JSON file.

        Uses the executor so the event loop is not blocked.

        Args:
            vin: Vehicle VIN
            data: Response payload from the server
        """
        if not self.responses_dir:
            return

        try:
            # Run the file write via the executor
            await self.hass.async_add_executor_job(
                self._save_response_sync,
                vin,
                data
            )

            self.last_response = data
            _LOGGER.debug(f"✅ Response auto-saved for {vin}")

        except Exception as e:
            _LOGGER.error(f"❌ Failed to save response: {e}", exc_info=True)

    def _save_response_sync(self, vin: str, data: Dict) -> None:
        """
        Synchronous helper for writing the file
        (runs in a separate thread via the executor)

        Args:
            vin: Vehicle VIN
            data: Response payload from the server
        """
        try:
            # Build a timestamped filename
            filename = f"zeekr_{vin}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            filepath = os.path.join(self.responses_dir, filename)

            # Wrap the response with metadata
            response_with_metadata = {
                "_metadata": {
                    "saved_at": datetime.now().isoformat(),
                    "vin": vin,
                    "auto_save": True
                },
                "data": data
            }

            # Save to file
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(response_with_metadata, f, ensure_ascii=False, indent=2)

            _LOGGER.debug(f"✅ Response saved: {filepath}")

        except Exception as e:
            _LOGGER.error(f"❌ Failed to save response: {e}", exc_info=True)
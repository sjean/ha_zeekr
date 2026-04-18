# custom_components/zeekr/button.py
"""Button platform for Zeekr integration"""

import logging
from typing import Any

from homeassistant.components.button import (
    ButtonEntity,
    ButtonDeviceClass,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import ConfigType
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import ZeekrDataCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
        hass: HomeAssistant,
        config_entry: ConfigType,
        async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Zeekr buttons"""

    coordinator: ZeekrDataCoordinator = hass.data[DOMAIN][config_entry.entry_id]

    entities = []

    # Always add the global refresh button
    entities.append(ZeekrRefreshButton(coordinator))

    # Add one refresh button for each vehicle
    for vin in coordinator.data.keys():
        if vin:  # Skip empty VIN values
            entities.append(ZeekrRefreshVehicleButton(coordinator, vin))

    # Add all entities in one batch
    async_add_entities(entities)
    _LOGGER.info(f"✅ Added {len(entities)} buttons")


class ZeekrRefreshButton(CoordinatorEntity, ButtonEntity):
    """Global refresh button for all vehicles"""

    _attr_name = "Refresh All Vehicles"
    _attr_icon = "mdi:refresh"
    _attr_device_class = ButtonDeviceClass.RESTART
    _attr_has_entity_name = False

    def __init__(self, coordinator: ZeekrDataCoordinator):
        """Initialize button"""
        super().__init__(coordinator)
        self.coordinator = coordinator

        # Unique ID
        self._attr_unique_id = f"{DOMAIN}_refresh_all"

        # This is a shared device, not tied to a specific vehicle
        self._attr_device_info = {
            "identifiers": {(DOMAIN, "global")},
            "name": "Zeekr",
            "manufacturer": "Zeekr",
            "model": "API",
        }

    async def async_press(self) -> None:
        """Handle a button press from the user."""
        _LOGGER.info("🔄 [REFRESH] Force-refreshing all vehicles...")

        try:
            await self.coordinator.async_refresh()
            _LOGGER.info("✅ [REFRESH] Refresh completed successfully!")
        except Exception as e:
            _LOGGER.error(f"❌ [REFRESH] Refresh failed: {e}")
            raise


class ZeekrRefreshVehicleButton(CoordinatorEntity, ButtonEntity):
    """Refresh button for individual vehicle"""

    _attr_icon = "mdi:refresh"
    _attr_device_class = ButtonDeviceClass.RESTART
    _attr_has_entity_name = True
    _attr_name = "Refresh"

    def __init__(self, coordinator: ZeekrDataCoordinator, vin: str):
        """Initialize button"""
        super().__init__(coordinator)
        self.coordinator = coordinator
        self.vin = vin

        # Unique ID
        self._attr_unique_id = f"{DOMAIN}_{vin}_refresh"

        # Tie this button to the specific vehicle device
        self._attr_device_info = {
            "identifiers": {(DOMAIN, vin)},
            "name": f"Zeekr {vin}",
            "manufacturer": "Zeekr",
            "model": "EV",
        }

    async def async_press(self) -> None:
        """Handle a button press from the user."""
        _LOGGER.info(f"🔄 [REFRESH] Force-refreshing {self.vin}...")

        try:
            await self.coordinator.async_refresh()
            _LOGGER.info(f"✅ [REFRESH] Refresh for {self.vin} completed!")
        except Exception as e:
            _LOGGER.error(f"❌ [REFRESH] Refresh failed for {self.vin}: {e}")
            raise

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from coordinator"""
        self.async_write_ha_state()

# custom_components/zeekr/device_tracker.py
"""Device tracker platform for Zeekr integration"""

import logging
from typing import Any, Dict

from homeassistant.components.device_tracker import (
    TrackerEntity,
    SourceType,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import ConfigType
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import ZeekrDataCoordinator
from .vehicle_parser import VehicleDataParser

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
        hass: HomeAssistant,
        config_entry: ConfigType,
        async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Zeekr device trackers"""

    coordinator: ZeekrDataCoordinator = hass.data[DOMAIN][config_entry.entry_id]

    entities = []

    # Create a device tracker for each vehicle
    for vin in coordinator.data.keys():  # updated
        entities.append(ZeekrDeviceTracker(coordinator, vin))

    async_add_entities(entities)


class ZeekrDeviceTracker(CoordinatorEntity, TrackerEntity):
    """Zeekr device tracker for vehicle location"""

    _attr_has_entity_name = True
    _attr_name = "位置"
    _attr_icon = "mdi:map-marker"
    _attr_source_type = SourceType.GPS

    def __init__(self, coordinator: ZeekrDataCoordinator, vin: str):
        """Initialize device tracker"""
        super().__init__(coordinator)
        self.vin = vin

        # Unique ID
        self._attr_unique_id = f"{DOMAIN}_{vin}_location"

        # Device information
        self._attr_device_info = {
            "identifiers": {(DOMAIN, vin)},
            "name": f"Zeekr {vin}",
            "manufacturer": "Zeekr",
            "model": "EV",
        }

    def _get_parser(self) -> VehicleDataParser:
        """Get parser for current vehicle data"""
        if self.vin not in self.coordinator.data:
            return None
        from .vehicle_parser import VehicleDataParser
        return VehicleDataParser(self.coordinator.data[self.vin])

    @property
    def latitude(self) -> float:
        """Return latitude"""
        parser = self._get_parser()
        if parser:
            position = parser.get_position_info()
            return position['latitude']
        return None

    @property
    def longitude(self) -> float:
        """Return longitude"""
        parser = self._get_parser()
        if parser:
            position = parser.get_position_info()
            return position['longitude']
        return None

    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        """Return additional attributes"""
        parser = self._get_parser()
        if parser:
            position = parser.get_position_info()
            return {
                "海拔": position['altitude'],
                "方向": position['direction'],
            }
        return {}

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from coordinator"""
        self.async_write_ha_state()

# custom_components/zeekr/binary_sensor.py
"""Binary sensor platform for Zeekr integration"""

import logging
from typing import Any, Dict

from homeassistant.components.binary_sensor import (
    BinarySensorEntity,
    BinarySensorDeviceClass,
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
    """Set up Zeekr binary sensors"""

    coordinator: ZeekrDataCoordinator = hass.data[DOMAIN][config_entry.entry_id]

    entities = []

    # Create binary sensors for each vehicle
    for vin in coordinator.data.keys():
        entities.extend([
            # ========== STANDARD SENSORS ==========
            ZeekrEngineStatusSensor(coordinator, vin),
            ZeekrDriverDoorSensor(coordinator, vin),
            ZeekrPassengerDoorSensor(coordinator, vin),
            ZeekrDriverRearDoorSensor(coordinator, vin),
            ZeekrPassengerRearDoorSensor(coordinator, vin),
            ZeekrTrunkSensor(coordinator, vin),
            ZeekrEngineHoodSensor(coordinator, vin),
            ZeekrDriverWindowSensor(coordinator, vin),
            ZeekrPassengerWindowSensor(coordinator, vin),
            ZeekrDriverRearWindowSensor(coordinator, vin),
            ZeekrPassengerRearWindowSensor(coordinator, vin),

            # ========== PANORAMIC ROOF (FIXED) ====================
            ZeekrFrontShadeOpenSensor(coordinator, vin),
            ZeekrRearShadeOpenSensor(coordinator, vin),
            ZeekrRoofTransparentSensor(coordinator, vin),

            # 📡 GPS
            ZeekrGpsActiveSensor(coordinator, vin),

            # 🚗 BRAKING
            ZeekrBrakingSensor(coordinator, vin),
            ZeekrEnergyRecoveryActiveSensor(coordinator, vin),
        ])

    async_add_entities(entities)
    _LOGGER.info(f"✅ Added {len(entities)} binary sensors total")


# ==================== BASE CLASS ====================

class ZeekrBaseBinarySensor(CoordinatorEntity, BinarySensorEntity):
    """Base class for Zeekr binary sensors"""

    def __init__(self, coordinator: ZeekrDataCoordinator, vin: str):
        """Initialize binary sensor"""
        super().__init__(coordinator)
        self.vin = vin
        self._attr_has_entity_name = True

        # Unique ID
        self._attr_unique_id = f"{DOMAIN}_{vin}_{self._get_sensor_type()}"

        # Device information
        self._attr_device_info = {
            "identifiers": {(DOMAIN, vin)},
            "name": f"Zeekr {vin}",
            "manufacturer": "Zeekr",
            "model": "EV",
        }

    def _get_sensor_type(self) -> str:
        """Override in subclasses"""
        return "binary_sensor"

    def _get_parser(self) -> VehicleDataParser:
        """Get parser for current vehicle data"""
        if self.vin not in self.coordinator.data:
            return None
        return VehicleDataParser(self.coordinator.data[self.vin])

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from coordinator"""
        self.async_write_ha_state()


# ==================== STANDARD SENSORS ====================

class ZeekrEngineStatusSensor(ZeekrBaseBinarySensor):
    """Engine status binary sensor"""

    _attr_name = "发动机"
    _attr_device_class = BinarySensorDeviceClass.RUNNING
    _attr_icon = "mdi:engine"

    def _get_sensor_type(self) -> str:
        return "engine"

    @property
    def is_on(self) -> bool:
        """Return True if engine is running"""
        parser = self._get_parser()
        if parser:
            status = parser.data.get('basicVehicleStatus', {}).get('engineStatus', '')
            return status == 'engine_running'
        return False


class ZeekrDriverDoorSensor(ZeekrBaseBinarySensor):
    """Driver door binary sensor"""

    _attr_name = "主驾车门"
    _attr_device_class = BinarySensorDeviceClass.DOOR
    _attr_icon = "mdi:door"

    def _get_sensor_type(self) -> str:
        return "driver_door"

    @property
    def is_on(self) -> bool:
        """Return True if door is open"""
        parser = self._get_parser()
        if parser:
            security = parser.get_security_info()
            return security['driver_door_open']
        return False


class ZeekrPassengerDoorSensor(ZeekrBaseBinarySensor):
    """Passenger door binary sensor"""

    _attr_name = "副驾车门"
    _attr_device_class = BinarySensorDeviceClass.DOOR
    _attr_icon = "mdi:door"

    def _get_sensor_type(self) -> str:
        return "passenger_door"

    @property
    def is_on(self) -> bool:
        """Return True if door is open"""
        parser = self._get_parser()
        if parser:
            security = parser.get_security_info()
            return security['passenger_door_open']
        return False


class ZeekrDriverRearDoorSensor(ZeekrBaseBinarySensor):
    """Driver rear door binary sensor"""

    _attr_name = "左后车门"
    _attr_device_class = BinarySensorDeviceClass.DOOR
    _attr_icon = "mdi:door"

    def _get_sensor_type(self) -> str:
        return "driver_rear_door"

    @property
    def is_on(self) -> bool:
        """Return True if door is open"""
        parser = self._get_parser()
        if parser:
            security = parser.get_security_info()
            return security['driver_rear_door_open']
        return False


class ZeekrPassengerRearDoorSensor(ZeekrBaseBinarySensor):
    """Passenger rear door binary sensor"""

    _attr_name = "右后车门"
    _attr_device_class = BinarySensorDeviceClass.DOOR
    _attr_icon = "mdi:door"

    def _get_sensor_type(self) -> str:
        return "passenger_rear_door"

    @property
    def is_on(self) -> bool:
        """Return True if door is open"""
        parser = self._get_parser()
        if parser:
            security = parser.get_security_info()
            return security['passenger_rear_door_open']
        return False


class ZeekrTrunkSensor(ZeekrBaseBinarySensor):
    """Trunk binary sensor"""

    _attr_name = "后备厢"
    _attr_device_class = BinarySensorDeviceClass.DOOR
    _attr_icon = "mdi:car-door"

    def _get_sensor_type(self) -> str:
        return "trunk"

    @property
    def is_on(self) -> bool:
        """Return True if trunk is open"""
        parser = self._get_parser()
        if parser:
            security = parser.get_security_info()
            return security['trunk_open']
        return False


class ZeekrEngineHoodSensor(ZeekrBaseBinarySensor):
    """Engine hood binary sensor"""

    _attr_name = "前舱盖"
    _attr_device_class = BinarySensorDeviceClass.DOOR
    _attr_icon = "mdi:car-door"

    def _get_sensor_type(self) -> str:
        return "engine_hood"

    @property
    def is_on(self) -> bool:
        """Return True if hood is open"""
        parser = self._get_parser()
        if parser:
            security = parser.get_security_info()
            return security['engine_hood_open']
        return False


class ZeekrDriverWindowSensor(ZeekrBaseBinarySensor):
    """Driver window binary sensor"""

    _attr_name = "左前车窗"
    _attr_device_class = BinarySensorDeviceClass.WINDOW
    _attr_icon = "mdi:window-closed"

    def _get_sensor_type(self) -> str:
        return "driver_window"

    @property
    def is_on(self) -> bool:
        """Return True if window is open"""
        parser = self._get_parser()
        if parser:
            windows = parser.get_windows_info()
            return windows['driver_window'] == '打开'
        return False


class ZeekrPassengerWindowSensor(ZeekrBaseBinarySensor):
    """Passenger window binary sensor"""

    _attr_name = "右前车窗"
    _attr_device_class = BinarySensorDeviceClass.WINDOW
    _attr_icon = "mdi:window-closed"

    def _get_sensor_type(self) -> str:
        return "passenger_window"

    @property
    def is_on(self) -> bool:
        """Return True if window is open"""
        parser = self._get_parser()
        if parser:
            windows = parser.get_windows_info()
            return windows['passenger_window'] == '打开'
        return False


class ZeekrDriverRearWindowSensor(ZeekrBaseBinarySensor):
    """Driver rear window binary sensor"""

    _attr_name = "左后车窗"
    _attr_device_class = BinarySensorDeviceClass.WINDOW
    _attr_icon = "mdi:window-closed"

    def _get_sensor_type(self) -> str:
        return "driver_rear_window"

    @property
    def is_on(self) -> bool:
        """Return True if window is open"""
        parser = self._get_parser()
        if parser:
            windows = parser.get_windows_info()
            return windows['driver_rear_window'] == '打开'
        return False


class ZeekrPassengerRearWindowSensor(ZeekrBaseBinarySensor):
    """Passenger rear window binary sensor"""

    _attr_name = "右后车窗"
    _attr_device_class = BinarySensorDeviceClass.WINDOW
    _attr_icon = "mdi:window-closed"

    def _get_sensor_type(self) -> str:
        return "passenger_rear_window"

    @property
    def is_on(self) -> bool:
        """Return True if window is open"""
        parser = self._get_parser()
        if parser:
            windows = parser.get_windows_info()
            return windows['passenger_rear_window'] == '打开'
        return False


# ==================== PANORAMIC ROOF (FIXED) ====================

class ZeekrFrontShadeOpenSensor(ZeekrBaseBinarySensor):
    """Is the front shade open?"""

    _attr_name = "前遮阳帘开启"
    _attr_icon = "mdi:window-shutter"
    _attr_device_class = BinarySensorDeviceClass.WINDOW

    def _get_sensor_type(self) -> str:
        return "front_shade_open"

    @property
    def is_on(self) -> bool:
        """Return True if front shade is open/transparent"""
        parser = self._get_parser()
        if parser:
            roof = parser.get_panoramic_roof_status()
            return roof['front_shade_open']
        return False


class ZeekrRearShadeOpenSensor(ZeekrBaseBinarySensor):
    """Is the rear shade open?"""

    _attr_name = "后遮阳帘开启"
    _attr_icon = "mdi:window-shutter"
    _attr_device_class = BinarySensorDeviceClass.WINDOW

    def _get_sensor_type(self) -> str:
        return "rear_shade_open"

    @property
    def is_on(self) -> bool:
        """Return True if rear shade is open/transparent"""
        parser = self._get_parser()
        if parser:
            roof = parser.get_panoramic_roof_status()
            return roof['rear_shade_open']
        return False


class ZeekrRoofTransparentSensor(ZeekrBaseBinarySensor):
    """Does the roof let light through? (shade more than 50% open)"""

    _attr_name = "天幕透光"
    _attr_icon = "mdi:window"
    _attr_device_class = BinarySensorDeviceClass.WINDOW

    def _get_sensor_type(self) -> str:
        return "roof_transparent"

    @property
    def is_on(self) -> bool:
        """Return True if roof is transparent (lots of light)"""
        parser = self._get_parser()
        if parser:
            roof = parser.get_panoramic_roof_status()
            return roof['is_transparent']
        return False

# ========== GPS AND NAVIGATION ====================

class ZeekrGpsActiveSensor(ZeekrBaseBinarySensor):
    """Is GPS active?"""

    _attr_name = "GPS 激活"
    _attr_icon = "mdi:satellite-variant"

    def _get_sensor_type(self) -> str:
        return "gps_active"

    @property
    def is_on(self) -> bool:
        """Return True if GPS is active"""
        parser = self._get_parser()
        if parser:
            gps = parser.get_gps_status()
            return gps['has_gps_signal']
        return False


# ========== BRAKING AND RECOVERY ====================

class ZeekrBrakingSensor(ZeekrBaseBinarySensor):
    """Is the vehicle braking? (energy recovery)"""

    _attr_name = "正在制动"
    _attr_icon = "mdi:brake-fluid"

    def _get_sensor_type(self) -> str:
        return "braking"

    @property
    def is_on(self) -> bool:
        """Return True if vehicle is braking"""
        parser = self._get_parser()
        if parser:
            brake = parser.get_brake_status()
            return brake['is_braking']
        return False


class ZeekrEnergyRecoveryActiveSensor(ZeekrBaseBinarySensor):
    """Is regenerative braking active?"""

    _attr_name = "能量回收激活"
    _attr_icon = "mdi:lightning-bolt"

    def _get_sensor_type(self) -> str:
        return "energy_recovery_active"

    @property
    def is_on(self) -> bool:
        """Return True if energy recovery is active"""
        parser = self._get_parser()
        if parser:
            recovery = parser.estimate_battery_recovery()
            return recovery['is_recovering']
        return False

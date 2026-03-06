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

    # Для каждого автомобиля создаем binary sensors
    for vin in coordinator.data.keys():
        entities.extend([
            # ========== СТАНДАРТНЫЕ ДАТЧИКИ ==========
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

            # ========== ПАНОРАМНАЯ КРЫША (ИСПРАВЛЕННАЯ) ====================
            ZeekrFrontShadeOpenSensor(coordinator, vin),
            ZeekrRearShadeOpenSensor(coordinator, vin),
            ZeekrRoofTransparentSensor(coordinator, vin),

            # 🔒 РЕМНИ БЕЗОПАСНОСТИ
            ZeekrSeatbeltDriverBinarySensor(coordinator, vin),
            ZeekrSeatbeltPassengerBinarySensor(coordinator, vin),

            # 📡 GPS
            ZeekrGpsActiveSensor(coordinator, vin),

            # 🚗 ТОРМОЖЕНИЕ
            ZeekrBrakingSensor(coordinator, vin),
            ZeekrEnergyRecoveryActiveSensor(coordinator, vin),
        ])

    async_add_entities(entities)
    _LOGGER.info(f"✅ Added {len(entities)} binary sensors total")


# ==================== БАЗОВЫЙ КЛАСС ====================

class ZeekrBaseBinarySensor(CoordinatorEntity, BinarySensorEntity):
    """Base class for Zeekr binary sensors"""

    def __init__(self, coordinator: ZeekrDataCoordinator, vin: str):
        """Initialize binary sensor"""
        super().__init__(coordinator)
        self.vin = vin
        self._attr_has_entity_name = True

        # Уникальный ID
        self._attr_unique_id = f"{DOMAIN}_{vin}_{self._get_sensor_type()}"

        # Информация об устройстве
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


# ==================== СТАНДАРТНЫЕ ДАТЧИКИ ====================

class ZeekrEngineStatusSensor(ZeekrBaseBinarySensor):
    """Engine status binary sensor"""

    _attr_name = "Engine"
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

    _attr_name = "Driver Door"
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

    _attr_name = "Passenger Door"
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

    _attr_name = "Driver Rear Door"
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

    _attr_name = "Passenger Rear Door"
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

    _attr_name = "Trunk"
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

    _attr_name = "Капот"
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

    _attr_name = "Окно ПЛ"
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
            return windows['driver_window'] == 'Открыто'
        return False


class ZeekrPassengerWindowSensor(ZeekrBaseBinarySensor):
    """Passenger window binary sensor"""

    _attr_name = "Окно ПП"
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
            return windows['passenger_window'] == 'Открыто'
        return False


class ZeekrDriverRearWindowSensor(ZeekrBaseBinarySensor):
    """Driver rear window binary sensor"""

    _attr_name = "Окно ЗЛ"
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
            return windows['driver_rear_window'] == 'Открыто'
        return False


class ZeekrPassengerRearWindowSensor(ZeekrBaseBinarySensor):
    """Passenger rear window binary sensor"""

    _attr_name = "Окно ЗП"
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
            return windows['passenger_rear_window'] == 'Открыто'
        return False


# ==================== ПАНОРАМНАЯ КРЫША (ИСПРАВЛЕННОЕ) ====================

class ZeekrFrontShadeOpenSensor(ZeekrBaseBinarySensor):
    """Передняя затемняющая шторка открыта?"""

    _attr_name = "Front Shade Open"
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
    """Задняя затемняющая шторка открыта?"""

    _attr_name = "Rear Shade Open"
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
    """Крыша пропускает свет? (шторка открыта более чем на 50%)"""

    _attr_name = "Roof Transparent"
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


# ========== РЕМНИ БЕЗОПАСНОСТИ ====================

class ZeekrSeatbeltDriverBinarySensor(ZeekrBaseBinarySensor):
    """Водитель пристегнут?"""

    _attr_name = "Seatbelt Driver"
    _attr_icon = "mdi:seatbelt"
    _attr_device_class = BinarySensorDeviceClass.SAFETY

    def _get_sensor_type(self) -> str:
        return "seatbelt_driver_binary"

    @property
    def is_on(self) -> bool:
        """Return True if driver is belted"""
        parser = self._get_parser()
        if parser:
            belts = parser.get_seatbelt_status()
            return belts['driver_belted'].startswith('✅')
        return False


class ZeekrSeatbeltPassengerBinarySensor(ZeekrBaseBinarySensor):
    """Пассажир пристегнут?"""

    _attr_name = "Seatbelt Passenger"
    _attr_icon = "mdi:seatbelt"
    _attr_device_class = BinarySensorDeviceClass.SAFETY

    def _get_sensor_type(self) -> str:
        return "seatbelt_passenger_binary"

    @property
    def is_on(self) -> bool:
        """Return True if passenger is belted"""
        parser = self._get_parser()
        if parser:
            belts = parser.get_seatbelt_status()
            return belts['passenger_belted'].startswith('✅')
        return False


# ========== GPS И НАВИГАЦИЯ ====================

class ZeekrGpsActiveSensor(ZeekrBaseBinarySensor):
    """GPS активен?"""

    _attr_name = "GPS Active"
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


# ========== ТОРМОЖЕНИЕ И ВОССТАНОВЛЕНИЕ ====================

class ZeekrBrakingSensor(ZeekrBaseBinarySensor):
    """Машина тормозит? (восстановление энергии)"""

    _attr_name = "Braking"
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
    """Рекуперативное торможение активно?"""

    _attr_name = "Energy Recovery Active"
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
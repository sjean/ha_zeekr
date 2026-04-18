# custom_components/zeekr/sensor.py
"""Sensor platform for Zeekr integration"""

import logging
from typing import Any, Dict
from datetime import datetime

from homeassistant.components.sensor import (
    SensorEntity,
    SensorDeviceClass,
    SensorStateClass,
)
from homeassistant.const import (
    PERCENTAGE,
    UnitOfLength,
    UnitOfTemperature,
    UnitOfSpeed,
    UnitOfPressure,
    EntityCategory,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import ConfigType
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, ICON_BATTERY, ICON_TEMPERATURE, ICON_CAR
from .coordinator import ZeekrDataCoordinator
from .vehicle_parser import VehicleDataParser

_LOGGER = logging.getLogger(__name__)


# ==================== BASE CLASS ====================

class ZeekrBaseSensor(CoordinatorEntity, SensorEntity):
    """Base class for Zeekr sensors"""

    def __init__(self, coordinator: ZeekrDataCoordinator, vin: str):
        """Initialize sensor"""
        super().__init__(coordinator)
        self.vin = vin
        self._attr_has_entity_name = True

        # Unique ID for each sensor
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
        return "sensor"

    def _get_parser(self) -> VehicleDataParser:
        """Get parser for current vehicle data"""
        if self.vin not in self.coordinator.data:
            return None
        return VehicleDataParser(self.coordinator.data[self.vin])

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from coordinator"""
        self.async_write_ha_state()


# ==================== GROUP 1: STATUS AND SECURITY ====================

class ZeekrLastUpdateTimeSensor(ZeekrBaseSensor):
    """Last update time - when the vehicle last connected to the server"""

    _attr_name = "Last Update"
    _attr_icon = "mdi:cloud-upload"

    def _get_sensor_type(self) -> str:
        return "last_update_time"

    @property
    def native_value(self) -> str:
        """Return last update time as formatted string"""
        parser = self._get_parser()
        if parser:
            timestamp = int(parser.data.get('updateTime', 0))
            if timestamp:
                update_datetime = datetime.fromtimestamp(timestamp / 1000)
                return update_datetime.strftime('%Y-%m-%d %H:%M:%S')
        return "N/A"

    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        """Return additional attributes"""
        parser = self._get_parser()
        if parser:
            timestamp = int(parser.data.get('updateTime', 0))
            if timestamp:
                update_datetime = datetime.fromtimestamp(timestamp / 1000)
                current_time = datetime.now()
                time_diff = current_time - update_datetime

                total_seconds = int(time_diff.total_seconds())
                minutes = total_seconds // 60
                hours = minutes // 60
                days = hours // 24

                if days > 0:
                    time_ago = f"{days} days ago"
                elif hours > 0:
                    time_ago = f"{hours} hours ago"
                elif minutes > 0:
                    time_ago = f"{minutes} minutes ago"
                else:
                    time_ago = "just now"

                return {
                    "How long ago": time_ago,
                    "Timestamp": timestamp,
                }
        return {}


class ZeekrBatterySensor(ZeekrBaseSensor):
    """🔋 Battery Charge"""

    _attr_name = "Battery Charge"
    _attr_native_unit_of_measurement = PERCENTAGE
    _attr_icon = ICON_BATTERY
    _attr_device_class = SensorDeviceClass.BATTERY
    _attr_state_class = SensorStateClass.MEASUREMENT

    def _get_sensor_type(self) -> str:
        return "battery"

    @property
    def native_value(self) -> int:
        """Return battery percentage"""
        parser = self._get_parser()
        if parser:
            battery = parser.get_battery_info()
            return battery['battery_percentage']
        return None

    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        """Return additional attributes"""
        parser = self._get_parser()
        if parser:
            battery = parser.get_battery_info()
            return {
                "Charge Status": battery['charge_status'],
                "Remaining Range": f"{battery['distance_to_empty']} km",
                "Average Consumption": f"{battery['avg_power_consumption']} kW",
            }
        return {}


class ZeekrTheftProtectionSensor(ZeekrBaseSensor):
    """AHBC theft-protection sensor"""

    _attr_name = "Security Mode"  # Display name in Home Assistant
    _attr_icon = "mdi:shield-check"  # Shield icon

    def _get_sensor_type(self) -> str:
        return "theft_protection_ahbc"

    @property
    def native_value(self) -> str:
        """Return status: enabled/disabled"""
        parser = self._get_parser()
        if parser:
            return parser.get_ahbc_status()
        return "Unavailable"


class ZeekrElectricParkBrakeStatusSensor(ZeekrBaseSensor):
    """Electronic parking brake status"""

    _attr_name = "Electronic Parking Brake"
    _attr_icon = "mdi:car-brake-parking"

    def _get_sensor_type(self) -> str:
        return "electric_park_brake"

    @property
    def native_value(self) -> str:
        """Return the parking brake status"""
        parser = self._get_parser()
        if parser:
            safety = parser.data.get('additionalVehicleStatus', {}).get('drivingSafetyStatus', {})
            status = int(safety.get('electricParkBrakeStatus', 0))

            status_map = {
                0: '❌ Off',
                1: '✅ Engaged (parking)',
                2: '⚠️ Error',
            }
            return status_map.get(status, 'Unknown')
        return None


# ==================== CORE SENSORS ====================

class ZeekrAuxBatteryPercentageSensor(ZeekrBaseSensor):
    """12V auxiliary battery"""

    _attr_name = "12V Battery"
    _attr_native_unit_of_measurement = PERCENTAGE
    _attr_icon = "mdi:battery-12v"
    _attr_device_class = SensorDeviceClass.BATTERY
    _attr_state_class = SensorStateClass.MEASUREMENT

    def _get_sensor_type(self) -> str:
        return "battery_12v_percentage"

    @property
    def native_value(self) -> float:
        """Return 12V battery percentage"""
        parser = self._get_parser()
        if parser:
            battery = parser.get_battery_info()
            return round(battery['aux_battery_percentage'], 1)
        return None


class ZeekrAuxBatteryVoltageSensor(ZeekrBaseSensor):
    """12V auxiliary battery voltage"""

    _attr_name = "12V Voltage"
    _attr_native_unit_of_measurement = "V"
    _attr_icon = "mdi:battery-12v"
    _attr_device_class = SensorDeviceClass.VOLTAGE
    _attr_state_class = SensorStateClass.MEASUREMENT

    def _get_sensor_type(self) -> str:
        return "battery_12v_voltage"

    @property
    def native_value(self) -> float:
        """Return 12V battery voltage"""
        parser = self._get_parser()
        if parser:
            battery = parser.get_battery_info()
            return round(battery['aux_battery_voltage'], 3)
        return None


class ZeekrDistanceToEmptySensor(ZeekrBaseSensor):
    """Range to empty"""

    _attr_name = "Remaining Range"
    _attr_native_unit_of_measurement = UnitOfLength.KILOMETERS
    _attr_icon = "mdi:road-variant"
    _attr_state_class = SensorStateClass.MEASUREMENT

    def _get_sensor_type(self) -> str:
        return "distance_to_empty"

    @property
    def native_value(self) -> int:
        """Return distance to empty"""
        parser = self._get_parser()
        if parser:
            battery = parser.get_battery_info()
            return battery['distance_to_empty']
        return None


class ZeekrInteriorTempSensor(ZeekrBaseSensor):
    """Interior temperature"""

    _attr_name = "Cabin Temperature"
    _attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS
    _attr_icon = ICON_TEMPERATURE
    _attr_device_class = SensorDeviceClass.TEMPERATURE
    _attr_state_class = SensorStateClass.MEASUREMENT

    def _get_sensor_type(self) -> str:
        return "interior_temp"

    @property
    def native_value(self) -> float:
        """Return interior temperature"""
        parser = self._get_parser()
        if parser:
            temp = parser.get_temperature_info()
            return temp['interior_temp']
        return None


class ZeekrExteriorTempSensor(ZeekrBaseSensor):
    """Exterior temperature"""

    _attr_name = "Exterior temperature"
    _attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS
    _attr_icon = ICON_TEMPERATURE
    _attr_device_class = SensorDeviceClass.TEMPERATURE
    _attr_state_class = SensorStateClass.MEASUREMENT

    def _get_sensor_type(self) -> str:
        return "exterior_temp"

    @property
    def native_value(self) -> float:
        """Return exterior temperature"""
        parser = self._get_parser()
        if parser:
            temp = parser.get_temperature_info()
            return temp['exterior_temp']
        return None


class ZeekrOdometerSensor(ZeekrBaseSensor):
    """Total travel distance"""

    _attr_name = "Odometer"
    _attr_native_unit_of_measurement = UnitOfLength.KILOMETERS
    _attr_icon = ICON_CAR
    _attr_state_class = SensorStateClass.TOTAL_INCREASING

    def _get_sensor_type(self) -> str:
        return "odometer"

    @property
    def native_value(self) -> float:
        """Return odometer value"""
        parser = self._get_parser()
        if parser:
            maintenance = parser.get_maintenance_info()
            return int(maintenance['odometer'])
        return None


class ZeekrCurrentSpeedSensor(ZeekrBaseSensor):
    """Current speed"""

    _attr_name = "Current Speed"
    _attr_native_unit_of_measurement = UnitOfSpeed.KILOMETERS_PER_HOUR
    _attr_icon = "mdi:speedometer"
    _attr_state_class = SensorStateClass.MEASUREMENT

    def _get_sensor_type(self) -> str:
        return "current_speed"

    @property
    def native_value(self) -> float:
        """Return current speed"""
        parser = self._get_parser()
        if parser:
            movement = parser.get_movement_info()
            return movement['speed']
        return None


class ZeekrAverageSpeedSensor(ZeekrBaseSensor):
    """Average trip speed"""

    _attr_name = "Average Speed"
    _attr_native_unit_of_measurement = UnitOfSpeed.KILOMETERS_PER_HOUR
    _attr_icon = "mdi:speedometer"
    _attr_state_class = SensorStateClass.MEASUREMENT

    def _get_sensor_type(self) -> str:
        return "average_speed"

    @property
    def native_value(self) -> int:
        """Return average speed"""
        parser = self._get_parser()
        if parser:
            movement = parser.get_movement_info()
            return movement['avg_speed']
        return None


class ZeekrDaysToServiceSensor(ZeekrBaseSensor):
    """Days until scheduled service"""

    _attr_name = "Days to Service"
    _attr_icon = "mdi:calendar-alert"
    _attr_state_class = SensorStateClass.MEASUREMENT

    def _get_sensor_type(self) -> str:
        return "days_to_service"

    @property
    def native_value(self) -> int:
        """Return days to service"""
        parser = self._get_parser()
        if parser:
            maintenance = parser.get_maintenance_info()
            return maintenance['days_to_service']
        return None


class ZeekrDistanceToServiceSensor(ZeekrBaseSensor):
    """Distance until scheduled service"""

    _attr_name = "Distance to Service"
    _attr_native_unit_of_measurement = UnitOfLength.KILOMETERS
    _attr_icon = "mdi:road-variant"
    _attr_state_class = SensorStateClass.MEASUREMENT

    def _get_sensor_type(self) -> str:
        return "distance_to_service"

    @property
    def native_value(self) -> int:
        """Return distance to service"""
        parser = self._get_parser()
        if parser:
            maintenance = parser.get_maintenance_info()
            return maintenance['distance_to_service']
        return None


class ZeekrTirePressureDriverSensor(ZeekrBaseSensor):
    """Front-left tire pressure"""

    _attr_name = "Front Left Tire Pressure"
    _attr_native_unit_of_measurement = UnitOfPressure.KPA
    _attr_icon = "mdi:tire"
    _attr_state_class = SensorStateClass.MEASUREMENT

    def _get_sensor_type(self) -> str:
        return "tire_pressure_driver"

    @property
    def native_value(self) -> float:
        """Return tire pressure"""
        parser = self._get_parser()
        if parser:
            tires = parser.get_tires_info()
            return round(tires['driver_tire'], 1)
        return None


class ZeekrTirePressurePassengerSensor(ZeekrBaseSensor):
    """Front-right tire pressure"""

    _attr_name = "Front Right Tire Pressure"
    _attr_native_unit_of_measurement = UnitOfPressure.KPA
    _attr_icon = "mdi:tire"
    _attr_state_class = SensorStateClass.MEASUREMENT

    def _get_sensor_type(self) -> str:
        return "tire_pressure_passenger"

    @property
    def native_value(self) -> float:
        """Return tire pressure"""
        parser = self._get_parser()
        if parser:
            tires = parser.get_tires_info()
            return round(tires['passenger_tire'], 1)
        return None


class ZeekrTirePressureDriverRearSensor(ZeekrBaseSensor):
    """Rear-left tire pressure"""

    _attr_name = "Rear Left Tire Pressure"
    _attr_native_unit_of_measurement = UnitOfPressure.KPA
    _attr_icon = "mdi:tire"
    _attr_state_class = SensorStateClass.MEASUREMENT

    def _get_sensor_type(self) -> str:
        return "tire_pressure_driver_rear"

    @property
    def native_value(self) -> float:
        """Return tire pressure"""
        parser = self._get_parser()
        if parser:
            tires = parser.get_tires_info()
            return round(tires['driver_rear_tire'], 1)
        return None


class ZeekrTirePressurePassengerRearSensor(ZeekrBaseSensor):
    """Rear-right tire pressure"""

    _attr_name = "Rear Right Tire Pressure"
    _attr_native_unit_of_measurement = UnitOfPressure.KPA
    _attr_icon = "mdi:tire"
    _attr_state_class = SensorStateClass.MEASUREMENT

    def _get_sensor_type(self) -> str:
        return "tire_pressure_passenger_rear"

    @property
    def native_value(self) -> float:
        """Return tire pressure"""
        parser = self._get_parser()
        if parser:
            tires = parser.get_tires_info()
            return round(tires['passenger_rear_tire'], 1)
        return None


class ZeekrInteriorPM25Sensor(ZeekrBaseSensor):
    """Interior PM2.5 particles"""

    _attr_name = "Interior PM2.5"
    _attr_native_unit_of_measurement = "μg/m³"
    _attr_icon = "mdi:air-filter"
    _attr_state_class = SensorStateClass.MEASUREMENT

    def _get_sensor_type(self) -> str:
        return "interior_pm25"

    @property
    def native_value(self) -> int:
        """Return PM2.5 level"""
        parser = self._get_parser()
        if parser:
            pollution = parser.get_pollution_info()
            return pollution['interior_pm25']
        return None


# ==================== EXTENDED SENSORS ====================
# 🔋 BATTERY

class ZeekrHVTempLevelSensor(ZeekrBaseSensor):
    """High-voltage battery temperature level"""

    _attr_name = "Battery Temperature"
    _attr_icon = "mdi:thermometer-alert"

    def _get_sensor_type(self) -> str:
        return "hv_temp_level"

    @property
    def native_value(self) -> str:
        """Return the temperature level text"""
        parser = self._get_parser()
        if parser:
            battery = parser.get_battery_info()
            return battery['hv_temp_level']
        return "Unknown"

    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        """Additional details"""
        parser = self._get_parser()
        if parser:
            battery = parser.get_battery_info()
            return {
                "Numeric value": battery['hv_temp_level_numeric'],
                "Values": "1=warm 🔥, 2=slightly cold ❄️, 3=cold 🥶, 4=very cold 🧊"
            }
        return {}


class ZeekrTimeToFullChargeSensor(ZeekrBaseSensor):
    """Time until full charge"""

    _attr_name = "Time to Full Charge"
    _attr_native_unit_of_measurement = "min"
    _attr_icon = "mdi:battery-charging"
    _attr_state_class = SensorStateClass.MEASUREMENT

    def _get_sensor_type(self) -> str:
        return "time_to_full_charge"

    @property
    def native_value(self) -> int:
        """Return charging time"""
        parser = self._get_parser()
        if parser:
            battery = parser.get_battery_info()
            value = battery['time_to_fully_charged']
            return None if value >= 2047 else value
        return None


# ==================== 🌡️ TIRE TEMPERATURES ====================

class ZeekrTireTempDriverSensor(ZeekrBaseSensor):
    """Front-left tire temperature"""

    _attr_name = "Front Left Tire Temperature"
    _attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS
    _attr_icon = "mdi:thermometer-lines"
    _attr_state_class = SensorStateClass.MEASUREMENT

    def _get_sensor_type(self) -> str:
        return "tire_temp_driver_front"

    @property
    def native_value(self) -> float:
        """Return temperature"""
        parser = self._get_parser()
        if parser:
            tires = parser.get_tires_info()
            return round(tires['driver_temp'], 1)
        return None


class ZeekrTireTempPassengerSensor(ZeekrBaseSensor):
    """Front-right tire temperature"""

    _attr_name = "Front Right Tire Temperature"
    _attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS
    _attr_icon = "mdi:thermometer-lines"
    _attr_state_class = SensorStateClass.MEASUREMENT

    def _get_sensor_type(self) -> str:
        return "tire_temp_passenger_front"

    @property
    def native_value(self) -> float:
        """Return temperature"""
        parser = self._get_parser()
        if parser:
            tires = parser.get_tires_info()
            return round(tires['passenger_temp'], 1)
        return None


class ZeekrTireTempDriverRearSensor(ZeekrBaseSensor):
    """Rear-left tire temperature"""

    _attr_name = "Rear Left Tire Temperature"
    _attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS
    _attr_icon = "mdi:thermometer-lines"
    _attr_state_class = SensorStateClass.MEASUREMENT

    def _get_sensor_type(self) -> str:
        return "tire_temp_driver_rear"

    @property
    def native_value(self) -> float:
        """Return temperature"""
        parser = self._get_parser()
        if parser:
            tires = parser.get_tires_info()
            return round(tires['driver_rear_temp'], 1)
        return None


class ZeekrTireTempPassengerRearSensor(ZeekrBaseSensor):
    """Rear-right tire temperature"""

    _attr_name = "Rear Right Tire Temperature"
    _attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS
    _attr_icon = "mdi:thermometer-lines"
    _attr_state_class = SensorStateClass.MEASUREMENT

    def _get_sensor_type(self) -> str:
        return "tire_temp_passenger_rear"

    @property
    def native_value(self) -> float:
        """Return temperature"""
        parser = self._get_parser()
        if parser:
            tires = parser.get_tires_info()
            return round(tires['passenger_rear_temp'], 1)
        return None


# ==================== 🚙 MOVEMENT (EXTENDED) ====================

class ZeekrTripMeter1Sensor(ZeekrBaseSensor):
    """Trip meter 1"""

    _attr_name = "Trip Meter 1"
    _attr_native_unit_of_measurement = UnitOfLength.KILOMETERS
    _attr_icon = "mdi:road-variant"
    _attr_state_class = SensorStateClass.TOTAL_INCREASING

    def _get_sensor_type(self) -> str:
        return "trip_meter_1"

    @property
    def native_value(self) -> float:
        """Return distance"""
        parser = self._get_parser()
        if parser:
            movement = parser.get_movement_info()
            return round(movement['trip_meter_1'], 1)
        return None


class ZeekrTripMeter2Sensor(ZeekrBaseSensor):
    """Trip meter 2"""

    _attr_name = "Trip Meter 2"
    _attr_native_unit_of_measurement = UnitOfLength.KILOMETERS
    _attr_icon = "mdi:road-variant"
    _attr_state_class = SensorStateClass.TOTAL_INCREASING

    def _get_sensor_type(self) -> str:
        return "trip_meter_2"

    @property
    def native_value(self) -> float:
        """Return distance"""
        parser = self._get_parser()
        if parser:
            movement = parser.get_movement_info()
            return round(movement['trip_meter_2'], 1)
        return None


# ==================== 🔧 MAINTENANCE (EXTENDED) ====================

class ZeekrEngineHoursToServiceSensor(ZeekrBaseSensor):
    """Engine hours until service"""

    _attr_name = "Hours to Service"
    _attr_native_unit_of_measurement = "h"
    _attr_icon = "mdi:wrench-clock"
    _attr_state_class = SensorStateClass.MEASUREMENT

    def _get_sensor_type(self) -> str:
        return "engine_hours_to_service"

    @property
    def native_value(self) -> int:
        """Return hours"""
        parser = self._get_parser()
        if parser:
            maintenance = parser.get_maintenance_info()
            return maintenance['engine_hours_to_service']
        return None


class ZeekrBrakeFluidLevelSensor(ZeekrBaseSensor):
    """Brake fluid level"""

    _attr_name = "Brake Fluid"
    _attr_icon = "mdi:water-opacity"

    def _get_sensor_type(self) -> str:
        return "brake_fluid_level"

    @property
    def native_value(self) -> str:
        """Return level"""
        parser = self._get_parser()
        if parser:
            maintenance = parser.get_maintenance_info()
            return maintenance['brake_fluid_level']
        return "Unknown"


class ZeekrWasherFluidLevelSensor(ZeekrBaseSensor):
    """Washer fluid level"""

    _attr_name = "Washer Fluid"
    _attr_icon = "mdi:water-opacity"

    def _get_sensor_type(self) -> str:
        return "washer_fluid_level"

    @property
    def native_value(self) -> str:
        """Return level"""
        parser = self._get_parser()
        if parser:
            maintenance = parser.get_maintenance_info()
            return maintenance['washer_fluid_level']
        return "Unknown"


class ZeekrEngineCoolantLevelSensor(ZeekrBaseSensor):
    """Coolant level"""

    _attr_name = "Coolant"
    _attr_icon = "mdi:water-opacity"

    def _get_sensor_type(self) -> str:
        return "engine_coolant_level"

    @property
    def native_value(self) -> str:
        """Return level"""
        parser = self._get_parser()
        if parser:
            maintenance = parser.get_maintenance_info()
            return maintenance['engine_coolant_level']
        return "Unknown"


# ==================== 💨 AIR QUALITY (EXTENDED) ====================

class ZeekrExteriorPM25LevelSensor(ZeekrBaseSensor):
    """Exterior PM2.5 level"""

    _attr_name = "Exterior PM2.5"
    _attr_icon = "mdi:air-filter"

    def _get_sensor_type(self) -> str:
        return "exterior_pm25_level"

    @property
    def native_value(self) -> str:
        """Return level"""
        parser = self._get_parser()
        if parser:
            pollution = parser.get_pollution_info()
            return pollution['interior_pm25_level']
        return None

# ==================== 🅿️ PARKING ====================

class ZeekrParkDurationSensor(ZeekrBaseSensor):
    """Parking duration"""

    _attr_name = "Parking Time"
    _attr_icon = "mdi:parking"

    def _get_sensor_type(self) -> str:
        return "park_duration"

    @property
    def native_value(self) -> str:
        """Return duration"""
        parser = self._get_parser()
        if parser:
            park = parser.get_park_info()
            return park['park_duration']
        return None

    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        """Additional attributes"""
        parser = self._get_parser()
        if parser:
            park = parser.get_park_info()
            return {
                'parked_since': park['parked_since'],
                'parked_seconds': park['total_seconds'],
                'parked': park['is_parked'],
            }
        return {}


# ==================== 🎯 CLIMATE (EXTENDED) ====================

class ZeekrSteeringWheelHeatingStatusSensor(ZeekrBaseSensor):
    """Steering wheel heating status"""

    _attr_name = "Steering Wheel Heating"
    _attr_icon = "mdi:heating"

    def _get_sensor_type(self) -> str:
        return "steering_wheel_heating"

    @property
    def native_value(self) -> str:
        """Return status"""
        parser = self._get_parser()
        if parser:
            climate = parser.get_climate_info()
            return climate['steering_wheel_heating']
        return None


class ZeekrDriverHeatingStatusSensor(ZeekrBaseSensor):
    """Driver seat heating status"""

    _attr_name = "Driver Heating"
    _attr_icon = "mdi:heating"

    def _get_sensor_type(self) -> str:
        return "driver_heating"

    @property
    def native_value(self) -> str:
        """Return status"""
        parser = self._get_parser()
        if parser:
            climate = parser.get_climate_info()
            return climate['driver_heating']
        return None


class ZeekrPassengerHeatingStatusSensor(ZeekrBaseSensor):
    """Passenger seat heating status"""

    _attr_name = "Passenger Heating"
    _attr_icon = "mdi:heating"

    def _get_sensor_type(self) -> str:
        return "passenger_heating"

    @property
    def native_value(self) -> str:
        """Return status"""
        parser = self._get_parser()
        if parser:
            climate = parser.get_climate_info()
            return climate['passenger_heating']
        return None


# ==================== 📍 COORDINATES ====================

class ZeekrLatitudeSensor(ZeekrBaseSensor):
    """Latitude (GPS coordinates)"""

    _attr_name = "Latitude"
    _attr_icon = "mdi:latitude"
    _attr_state_class = SensorStateClass.MEASUREMENT

    def _get_sensor_type(self) -> str:
        return "latitude"

    @property
    def native_value(self) -> float:
        """Return latitude"""
        parser = self._get_parser()
        if parser:
            position = parser.get_position_info()
            return round(position['latitude'], 6)
        return None


class ZeekrLongitudeSensor(ZeekrBaseSensor):
    """Longitude (GPS coordinates)"""

    _attr_name = "Longitude"
    _attr_icon = "mdi:longitude"
    _attr_state_class = SensorStateClass.MEASUREMENT

    def _get_sensor_type(self) -> str:
        return "longitude"

    @property
    def native_value(self) -> float:
        """Return longitude"""
        parser = self._get_parser()
        if parser:
            position = parser.get_position_info()
            return round(position['longitude'], 6)
        return None


class ZeekrAltitudeSensor(ZeekrBaseSensor):
    """Altitude above sea level"""

    _attr_name = "Altitude"
    _attr_native_unit_of_measurement = UnitOfLength.METERS
    _attr_icon = "mdi:elevation-rise"
    _attr_state_class = SensorStateClass.MEASUREMENT

    def _get_sensor_type(self) -> str:
        return "altitude"

    @property
    def native_value(self) -> int:
        """Return altitude"""
        parser = self._get_parser()
        if parser:
            position = parser.get_position_info()
            return position['altitude']
        return None


# ==================== 🔐 INFORMATION ====================

class ZeekrPropulsionTypeSensor(ZeekrBaseSensor):
    """Propulsion type"""

    _attr_name = "Propulsion Type"
    _attr_icon = "mdi:fuel-cell"

    def _get_sensor_type(self) -> str:
        return "propulsion_type"

    @property
    def native_value(self) -> str:
        """Return type"""
        parser = self._get_parser()
        if parser:
            return parser.get_propulsion_type()
        return None


# ==================== ⚡ CHARGING ====================

class ZeekrDCChargePowerSensor(ZeekrBaseSensor):
    """DC charging power (fast charging)"""

    _attr_name = "DC Charging Power"
    _attr_native_unit_of_measurement = "kW"
    _attr_icon = "mdi:lightning-bolt"
    _attr_device_class = SensorDeviceClass.POWER
    _attr_state_class = SensorStateClass.MEASUREMENT

    def _get_sensor_type(self) -> str:
        return "dc_charge_power"

    @property
    def native_value(self) -> float:
        """Return DC charging power"""
        parser = self._get_parser()
        if parser:
            charging = parser.get_charging_info()
            return charging['dc_power']
        return None


class ZeekrDCChargeVoltageExtendedSensor(ZeekrBaseSensor):
    """DC charging voltage (detailed)"""

    _attr_name = "DC Charging Voltage"
    _attr_native_unit_of_measurement = "V"
    _attr_icon = "mdi:flash"
    _attr_device_class = SensorDeviceClass.VOLTAGE
    _attr_state_class = SensorStateClass.MEASUREMENT

    def _get_sensor_type(self) -> str:
        return "dc_charge_voltage_detailed"

    @property
    def native_value(self) -> float:
        """Return charging voltage"""
        parser = self._get_parser()
        if parser:
            charging = parser.get_charging_info()
            return round(charging['dc_charge_pile_voltage'], 1)
        return None


class ZeekrDCChargeCurrentExtendedSensor(ZeekrBaseSensor):
    """DC charging current (detailed)"""

    _attr_name = "DC Charging Current"
    _attr_native_unit_of_measurement = "A"
    _attr_icon = "mdi:lightning-bolt"
    _attr_state_class = SensorStateClass.MEASUREMENT

    def _get_sensor_type(self) -> str:
        return "dc_charge_current_detailed"

    @property
    def native_value(self) -> float:
        """Return charging current"""
        parser = self._get_parser()
        if parser:
            charging = parser.get_charging_info()
            return round(charging['dc_charge_pile_current'], 1)
        return None


class ZeekrDCChargeStatusDetailedSensor(ZeekrBaseSensor):
    """DC charging status (detailed)"""

    _attr_name = "DC Charging Status"
    _attr_icon = "mdi:battery-charging-wireless"

    def _get_sensor_type(self) -> str:
        return "dc_charge_status_detailed"

    @property
    def native_value(self) -> str:
        """Return DC charging status"""
        parser = self._get_parser()
        if parser:
            charging = parser.get_charging_info()
            return charging['dc_charge_status']
        return None


class ZeekrDCDCStatusSensor(ZeekrBaseSensor):
    """DC/DC converter status (400V -> 12V)"""

    _attr_name = "DC/DC Converter"
    _attr_icon = "mdi:power-settings"

    def _get_sensor_type(self) -> str:
        return "dcdc_status"

    @property
    def native_value(self) -> str:
        """Return converter status"""
        parser = self._get_parser()
        if parser:
            charging = parser.get_charging_info()
            return charging['dc_dc_connect_status']
        return None

    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        """Additional attributes"""
        parser = self._get_parser()
        if parser:
            charging = parser.get_charging_info()
            return {
                "Activated": charging['dc_dc_activated'],
                "Purpose": "Converts 400V to 12V to power vehicle components"
            }
        return {}


# ==================== DISCHARGE (V2L, V2H) ====================

class ZeekrDischargePowerSensor(ZeekrBaseSensor):
    """Discharge power V2L/V2H (powering a home/device)"""

    _attr_name = "Discharge Power"
    _attr_native_unit_of_measurement = "kW"
    _attr_icon = "mdi:battery-arrow-up"
    _attr_device_class = SensorDeviceClass.POWER
    _attr_state_class = SensorStateClass.MEASUREMENT

    def _get_sensor_type(self) -> str:
        return "discharge_power"

    @property
    def native_value(self) -> float:
        """Return discharge power"""
        parser = self._get_parser()
        if parser:
            charging = parser.get_charging_info()
            return charging['discharge_power']
        return None


class ZeekrDischargeVoltageSensor(ZeekrBaseSensor):
    """Discharge voltage V2L/V2H"""

    _attr_name = "Discharge Voltage"
    _attr_native_unit_of_measurement = "V"
    _attr_icon = "mdi:flash"
    _attr_device_class = SensorDeviceClass.VOLTAGE
    _attr_state_class = SensorStateClass.MEASUREMENT

    def _get_sensor_type(self) -> str:
        return "discharge_voltage"

    @property
    def native_value(self) -> float:
        """Return discharge voltage"""
        parser = self._get_parser()
        if parser:
            charging = parser.get_charging_info()
            return round(charging['discharge_voltage'], 1)
        return None


class ZeekrDischargeCurrentSensor(ZeekrBaseSensor):
    """Discharge current V2L/V2H"""

    _attr_name = "Discharge Current"
    _attr_native_unit_of_measurement = "A"
    _attr_icon = "mdi:lightning-bolt"
    _attr_state_class = SensorStateClass.MEASUREMENT

    def _get_sensor_type(self) -> str:
        return "discharge_current"

    @property
    def native_value(self) -> float:
        """Return discharge current"""
        parser = self._get_parser()
        if parser:
            charging = parser.get_charging_info()
            return round(abs(charging['discharge_current']), 1)
        return None


class ZeekrChargerStateSensor(ZeekrBaseSensor):
    """Charger state"""

    _attr_name = "Charger State"
    _attr_icon = "mdi:power-plug"

    def _get_sensor_type(self) -> str:
        return "charger_state"

    @property
    def native_value(self) -> str:
        """Return the charger state"""
        parser = self._get_parser()
        if parser:
            charging = parser.get_charging_info()
            return charging['charger_state']
        return None

# ==================== MOVEMENT AND SPEED ====================


class ZeekrBrakeStatusSensor(ZeekrBaseSensor):
    """Brake / stop-light status"""

    _attr_name = "Brake Status"
    _attr_icon = "mdi:brake-fluid"

    def _get_sensor_type(self) -> str:
        return "brake_status"

    @property
    def native_value(self) -> str:
        """Return brake status"""
        parser = self._get_parser()
        if parser:
            brake = parser.get_brake_status()
            return brake['brake_status']
        return None

    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        """Additional details"""
        parser = self._get_parser()
        if parser:
            brake = parser.get_brake_status()
            return {
                'Braking': brake['is_braking'],
                'stop_lights': brake['stop_lights_on'],
            }
        return {}


class ZeekrEnergyRecoverySensor(ZeekrBaseSensor):
    """Energy recovery status"""

    _attr_name = "Energy Recovery"
    _attr_icon = "mdi:lightning-bolt"

    def _get_sensor_type(self) -> str:
        return "energy_recovery"

    @property
    def native_value(self) -> str:
        """Return the energy recovery status"""
        parser = self._get_parser()
        if parser:
            recovery = parser.estimate_battery_recovery()
            return recovery['recovery_status']
        return None

    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        """Additional details"""
        parser = self._get_parser()
        if parser:
            recovery = parser.estimate_battery_recovery()
            return {
                'recovering': recovery['is_recovering'],
                'Braking': recovery['is_braking'],
                'speed': recovery['speed'],
                'current_charge': recovery['current_charge'],
            }
        return {}


class ZeekrGearStatusSensor(ZeekrBaseSensor):
    """Gearbox status"""

    _attr_name = "Gearbox"
    _attr_icon = "mdi:transmission-tower"

    def _get_sensor_type(self) -> str:
        return "gear_status"

    @property
    def native_value(self) -> str:
        """Return gearbox status"""
        parser = self._get_parser()
        if parser:
            movement = parser.get_movement_info()
            return movement['gear_auto']
        return None

# ==================== GPS AND NAVIGATION ====================

class ZeekrGpsStatusSensor(ZeekrBaseSensor):
    """GPS signal status"""

    _attr_name = "GPS Status"
    _attr_icon = "mdi:satellite-variant"

    def _get_sensor_type(self) -> str:
        return "gps_status"

    @property
    def native_value(self) -> str:
        """Return GPS status"""
        parser = self._get_parser()
        if parser:
            gps = parser.get_gps_status()
            return gps['gps_status']
        return None

    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        """Additional details"""
        parser = self._get_parser()
        if parser:
            gps = parser.get_gps_status()
            return {
                'has_signal': gps['has_gps_signal'],
                'coordinates_trusted': gps['coordinates_trusted'],
                'location_upload_enabled': gps['location_upload_enabled'],
                'Latitude': gps['latitude'],
                'Longitude': gps['longitude'],
            }
        return {}


# ==================== LIGHTS ====================

class ZeekrLightsStatusSensor(ZeekrBaseSensor):
    """Overall light status"""

    _attr_name = "Lights Status"
    _attr_icon = "mdi:lightbulb-group"

    def _get_sensor_type(self) -> str:
        return "lights_status"

    @property
    def native_value(self) -> str:
        """Return light status"""
        parser = self._get_parser()
        if parser:
            lights = parser.get_lights_status()
            return lights['lights_status']
        return None

    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        """Additional details"""
        parser = self._get_parser()
        if parser:
            lights = parser.get_lights_status()
            return {
                'daytime_running_lights': lights['drl_active'],
                'high_beam': lights['hi_beam'],
                'low_beam': lights['lo_beam'],
                'stop_lights': lights['stop_lights'],
                'night_mode': lights['is_night_mode'],
            }
        return {}


# ==================== SETUP FUNCTION (AT THE END) ====================

async def async_setup_entry(
        hass: HomeAssistant,
        config_entry: ConfigType,
        async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Zeekr sensors"""

    coordinator: ZeekrDataCoordinator = hass.data[DOMAIN][config_entry.entry_id]

    entities = []

    # Create sensors for each vehicle
    for vin in coordinator.data.keys():
        entities.extend([
            # ==================== GROUP 1: STATUS AND SECURITY ====================
            ZeekrLastUpdateTimeSensor(coordinator, vin),
            ZeekrBatterySensor(coordinator, vin),
            ZeekrTheftProtectionSensor(coordinator, vin),
            ZeekrElectricParkBrakeStatusSensor(coordinator, vin),

            # ==================== CORE SENSORS ====================
            ZeekrAuxBatteryPercentageSensor(coordinator, vin),
            ZeekrAuxBatteryVoltageSensor(coordinator, vin),
            ZeekrDistanceToEmptySensor(coordinator, vin),
            ZeekrInteriorTempSensor(coordinator, vin),
            ZeekrExteriorTempSensor(coordinator, vin),
            ZeekrOdometerSensor(coordinator, vin),
            ZeekrCurrentSpeedSensor(coordinator, vin),
            ZeekrAverageSpeedSensor(coordinator, vin),
            ZeekrDaysToServiceSensor(coordinator, vin),
            ZeekrDistanceToServiceSensor(coordinator, vin),
            ZeekrTirePressureDriverSensor(coordinator, vin),
            ZeekrTirePressurePassengerSensor(coordinator, vin),
            ZeekrTirePressureDriverRearSensor(coordinator, vin),
            ZeekrTirePressurePassengerRearSensor(coordinator, vin),
            ZeekrInteriorPM25Sensor(coordinator, vin),

            # ==================== EXTENDED SENSORS ====================
            # 🔋 Battery (extended)
            ZeekrHVTempLevelSensor(coordinator, vin),
            ZeekrTimeToFullChargeSensor(coordinator, vin),

            # 🌡️ Tire temperatures
            ZeekrTireTempDriverSensor(coordinator, vin),
            ZeekrTireTempPassengerSensor(coordinator, vin),
            ZeekrTireTempDriverRearSensor(coordinator, vin),
            ZeekrTireTempPassengerRearSensor(coordinator, vin),

            # 🚙 Movement
            ZeekrTripMeter1Sensor(coordinator, vin),
            ZeekrTripMeter2Sensor(coordinator, vin),

            # 🔧 Maintenance
            ZeekrEngineHoursToServiceSensor(coordinator, vin),
            ZeekrBrakeFluidLevelSensor(coordinator, vin),
            ZeekrWasherFluidLevelSensor(coordinator, vin),
            ZeekrEngineCoolantLevelSensor(coordinator, vin),

            # 💨 Air quality
            ZeekrExteriorPM25LevelSensor(coordinator, vin),

            # 🅿️ Parking
            ZeekrParkDurationSensor(coordinator, vin),

            # 🎯 Climate
            ZeekrSteeringWheelHeatingStatusSensor(coordinator, vin),
            ZeekrDriverHeatingStatusSensor(coordinator, vin),
            ZeekrPassengerHeatingStatusSensor(coordinator, vin),

            # 📍 Coordinates
            ZeekrLatitudeSensor(coordinator, vin),
            ZeekrLongitudeSensor(coordinator, vin),
            ZeekrAltitudeSensor(coordinator, vin),

            # 🔐 Information
            ZeekrPropulsionTypeSensor(coordinator, vin),

            # ⚡ Charging
            ZeekrDCChargePowerSensor(coordinator, vin),
            ZeekrDCChargeVoltageExtendedSensor(coordinator, vin),
            ZeekrDCChargeCurrentExtendedSensor(coordinator, vin),
            ZeekrDCChargeStatusDetailedSensor(coordinator, vin),
            ZeekrDCDCStatusSensor(coordinator, vin),

            # ⚡ V2L/V2H DISCHARGE
            ZeekrDischargePowerSensor(coordinator, vin),
            ZeekrDischargeVoltageSensor(coordinator, vin),
            ZeekrDischargeCurrentSensor(coordinator, vin),
            ZeekrChargerStateSensor(coordinator, vin),

            # ========== PANORAMIC ROOF (FIXED) ====================

            # 🚗 MOVEMENT
            ZeekrBrakeStatusSensor(coordinator, vin),
            ZeekrEnergyRecoverySensor(coordinator, vin),
            ZeekrGearStatusSensor(coordinator, vin),

            # 📡 GPS
            ZeekrGpsStatusSensor(coordinator, vin),

            # 💡 LIGHTS
            ZeekrLightsStatusSensor(coordinator, vin),
        ])

    async_add_entities(entities)
    _LOGGER.info(f"✅ Added {len(entities)} sensors total for {len(coordinator.data)} vehicles")

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
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import ConfigType
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, ICON_BATTERY, ICON_TEMPERATURE, ICON_CAR
from .coordinator import ZeekrDataCoordinator
from .vehicle_parser import VehicleDataParser

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
        hass: HomeAssistant,
        config_entry: ConfigType,
        async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Zeekr sensors"""

    coordinator: ZeekrDataCoordinator = hass.data[DOMAIN][config_entry.entry_id]

    entities = []

    # Для каждого автомобиля создаем датчики
    for vin in coordinator.data.keys():
        entities.extend([
            # ========== ОСНОВНЫЕ ДАТЧИКИ ==========
            ZeekrBatterySensor(coordinator, vin),
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
            ZeekrLastUpdateTimeSensor(coordinator, vin),

            # ========== РАСШИРЕННЫЕ ДАТЧИКИ ==========
            # 🔋 Батарея (расширено)
            ZeekrStateOfChargeSensor(coordinator, vin),
            ZeekrStateOfHealthSensor(coordinator, vin),
            ZeekrHVTempLevelSensor(coordinator, vin),
            ZeekrTimeToFullChargeSensor(coordinator, vin),

            # 🌡️ Температура шин
            ZeekrTireTempDriverSensor(coordinator, vin),
            ZeekrTireTempPassengerSensor(coordinator, vin),
            ZeekrTireTempDriverRearSensor(coordinator, vin),
            ZeekrTireTempPassengerRearSensor(coordinator, vin),

            # 🚙 Движение
            ZeekrTripMeter1Sensor(coordinator, vin),
            ZeekrTripMeter2Sensor(coordinator, vin),

            # 🔧 Обслуживание
            ZeekrEngineHoursToServiceSensor(coordinator, vin),
            ZeekrBrakeFluidLevelSensor(coordinator, vin),
            ZeekrWasherFluidLevelSensor(coordinator, vin),
            ZeekrEngineCoolantLevelSensor(coordinator, vin),

            # 💨 Воздух
            ZeekrExteriorPM25LevelSensor(coordinator, vin),
            ZeekrRelativeHumiditySensor(coordinator, vin),

            # 🅿️ Парковка
            ZeekrParkDurationSensor(coordinator, vin),
            ZeekrElectricParkBrakeStatusSensor(coordinator, vin),

            # 🎯 Климат
            ZeekrSteeringWheelHeatingStatusSensor(coordinator, vin),
            ZeekrDriverHeatingStatusSensor(coordinator, vin),
            ZeekrPassengerHeatingStatusSensor(coordinator, vin),

            # 📍 Координаты
            ZeekrLatitudeSensor(coordinator, vin),
            ZeekrLongitudeSensor(coordinator, vin),
            ZeekrAltitudeSensor(coordinator, vin),

            # 🔐 Информация
            ZeekrPropulsionTypeSensor(coordinator, vin),

            # ⚡ Зарядка
            ZeekrDCChargePowerSensor(coordinator, vin),
            ZeekrDCChargeVoltageExtendedSensor(coordinator, vin),
            ZeekrDCChargeCurrentExtendedSensor(coordinator, vin),
            ZeekrDCChargeStatusDetailedSensor(coordinator, vin),
            ZeekrDCDCStatusSensor(coordinator, vin),

            # ⚡ РАЗРЯДКА V2L/V2H
            ZeekrDischargePowerSensor(coordinator, vin),
            ZeekrDischargeVoltageSensor(coordinator, vin),
            ZeekrDischargeCurrentSensor(coordinator, vin),
            ZeekrChargerStateSensor(coordinator, vin),

            # ========== ПАНОРАМНАЯ КРЫША (ИСПРАВЛЕННАЯ) ====================
            ZeekrFrontShadeSensor(coordinator, vin),
            ZeekrRearShadeSensor(coordinator, vin),
            ZeekrRoofStatusSensor(coordinator, vin),

            # 🚗 ДВИЖЕНИЕ
            ZeekrSpeedSensor(coordinator, vin),
            ZeekrBrakeStatusSensor(coordinator, vin),
            ZeekrEnergyRecoverySensor(coordinator, vin),
            ZeekrGearStatusSensor(coordinator, vin),

            # 🔒 РЕМНИ БЕЗОПАСНОСТИ
            ZeekrSeatbeltDriverSensor(coordinator, vin),
            ZeekrSeatbeltPassengerSensor(coordinator, vin),
            ZeekrSeatbeltStatusSensor(coordinator, vin),

            # 📡 GPS
            ZeekrGpsStatusSensor(coordinator, vin),

            # 💡 ОГНИ
            ZeekrLightsStatusSensor(coordinator, vin),

            # 🔒 ОХРАНА
            ZeekrTheftProtectionSensor(coordinator, vin),
        ])

    async_add_entities(entities)
    _LOGGER.info(f"✅ Added {len(entities)} sensors total for {len(coordinator.data)} vehicles")


# ==================== БАЗОВЫЙ КЛАСС ====================

class ZeekrBaseSensor(CoordinatorEntity, SensorEntity):
    """Base class for Zeekr sensors"""

    def __init__(self, coordinator: ZeekrDataCoordinator, vin: str):
        """Initialize sensor"""
        super().__init__(coordinator)
        self.vin = vin
        self._attr_has_entity_name = True

        # Уникальный ID для каждого датчика
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


# ==================== ОСНОВНЫЕ ДАТЧИКИ ====================

class ZeekrBatterySensor(ZeekrBaseSensor):
    """Battery charge level sensor - основная батарея EV"""

    _attr_name = "Battery"
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
                "charge_status": battery['charge_status'],
                "distance_to_empty": f"{battery['distance_to_empty']} км",
                "avg_power_consumption": f"{battery['avg_power_consumption']} кВт",
            }
        return {}


class ZeekrAuxBatteryPercentageSensor(ZeekrBaseSensor):
    """12V auxiliary battery percentage"""

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

    _attr_name = "12V Battery Voltage"
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
    """Distance to empty sensor"""

    _attr_name = "Distance to Empty"
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
    """Interior temperature sensor"""

    _attr_name = "Interior Temperature"
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
    """Exterior temperature sensor"""

    _attr_name = "Exterior Temperature"
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
    """Odometer sensor"""

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
    """Current speed sensor"""

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
    """Average speed sensor"""

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
    """Days to service sensor"""

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
    """Distance to service sensor"""

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
    """Tire pressure - driver front"""

    _attr_name = "Tire Pressure - Driver Front"
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
    """Tire pressure - passenger front"""

    _attr_name = "Tire Pressure - Passenger Front"
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
    """Tire pressure - driver rear"""

    _attr_name = "Tire Pressure - Driver Rear"
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
    """Tire pressure - passenger rear"""

    _attr_name = "Tire Pressure - Passenger Rear"
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
    """Interior PM2.5 sensor"""

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


class ZeekrLastUpdateTimeSensor(ZeekrBaseSensor):
    """Last update time sensor - when vehicle last connected to server"""

    _attr_name = "Last Update Time"
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
                    time_ago = f"{days} дней назад"
                elif hours > 0:
                    time_ago = f"{hours} часов назад"
                elif minutes > 0:
                    time_ago = f"{minutes} минут назад"
                else:
                    time_ago = "только что"

                return {
                    "time_ago": time_ago,
                    "timestamp": timestamp,
                }
        return {}


# ==================== РАСШИРЕННЫЕ ДАТЧИКИ ====================
# 🔋 БАТАРЕЯ (РАСШИРЕНО)

class ZeekrStateOfChargeSensor(ZeekrBaseSensor):
    """State of Charge - какой-то внутренний параметр батереи"""

    _attr_name = "State of Charge"
    _attr_icon = "mdi:battery-heart"
    _attr_state_class = SensorStateClass.MEASUREMENT

    def _get_sensor_type(self) -> str:
        return "state_of_charge"

    @property
    def native_value(self) -> float:
        """Вернуть SOC"""
        parser = self._get_parser()
        if parser:
            battery = parser.get_battery_info()
            return battery['soc']
        return None

    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        """Дополнительная информация"""
        return {
            "note": "Внутренний параметр батареи (не процент)"
        }


class ZeekrStateOfHealthSensor(ZeekrBaseSensor):
    """State of Health - какой-то внутренний параметр батереи"""

    _attr_name = "State of Health"
    _attr_icon = "mdi:battery-check"
    _attr_state_class = SensorStateClass.MEASUREMENT

    def _get_sensor_type(self) -> str:
        return "state_of_health"

    @property
    def native_value(self) -> float:
        """Вернуть SOH"""
        parser = self._get_parser()
        if parser:
            battery = parser.get_battery_info()
            return battery['soh']
        return None

    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        """Дополнительная информация"""
        return {
            "note": "Внутренний параметр батереи (не процент здоровья)"
        }


class ZeekrHVTempLevelSensor(ZeekrBaseSensor):
    """Уровень HV температуры батареи"""

    _attr_name = "HV Temperature Level"
    _attr_icon = "mdi:thermometer-alert"

    def _get_sensor_type(self) -> str:
        return "hv_temp_level"

    @property
    def native_value(self) -> str:
        """Вернуть уровень температуры (текст)"""
        parser = self._get_parser()
        if parser:
            battery = parser.get_battery_info()
            return battery['hv_temp_level']
        return "Неизвестно"

    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        """Дополнительная информация"""
        parser = self._get_parser()
        if parser:
            battery = parser.get_battery_info()
            return {
                "numeric_value": battery['hv_temp_level_numeric'],
                "description": "1=теплая 🔥, 2=немного холодная ❄️, 3=холодная 🥶, 4=сильно холодная 🧊"
            }
        return {}


class ZeekrTimeToFullChargeSensor(ZeekrBaseSensor):
    """Время до полной зарядки"""

    _attr_name = "Time to Full Charge"
    _attr_native_unit_of_measurement = "min"
    _attr_icon = "mdi:battery-charging"
    _attr_state_class = SensorStateClass.MEASUREMENT

    def _get_sensor_type(self) -> str:
        return "time_to_full_charge"

    @property
    def native_value(self) -> int:
        """Вернуть время зарядки"""
        parser = self._get_parser()
        if parser:
            battery = parser.get_battery_info()
            value = battery['time_to_fully_charged']
            return None if value >= 2047 else value
        return None


# ==================== 🌡️ ТЕМПЕРАТУРА ШИН ====================

class ZeekrTireTempDriverSensor(ZeekrBaseSensor):
    """Температура передней левой шины"""

    _attr_name = "Tire Temp - Driver Front"
    _attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS
    _attr_icon = "mdi:thermometer-lines"
    _attr_state_class = SensorStateClass.MEASUREMENT

    def _get_sensor_type(self) -> str:
        return "tire_temp_driver_front"

    @property
    def native_value(self) -> float:
        """Вернуть температуру"""
        parser = self._get_parser()
        if parser:
            tires = parser.get_tires_info()
            return round(tires['driver_temp'], 1)
        return None


class ZeekrTireTempPassengerSensor(ZeekrBaseSensor):
    """Температура передней правой шины"""

    _attr_name = "Tire Temp - Passenger Front"
    _attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS
    _attr_icon = "mdi:thermometer-lines"
    _attr_state_class = SensorStateClass.MEASUREMENT

    def _get_sensor_type(self) -> str:
        return "tire_temp_passenger_front"

    @property
    def native_value(self) -> float:
        """Вернуть температуру"""
        parser = self._get_parser()
        if parser:
            tires = parser.get_tires_info()
            return round(tires['passenger_temp'], 1)
        return None


class ZeekrTireTempDriverRearSensor(ZeekrBaseSensor):
    """Температура задней левой шины"""

    _attr_name = "Tire Temp - Driver Rear"
    _attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS
    _attr_icon = "mdi:thermometer-lines"
    _attr_state_class = SensorStateClass.MEASUREMENT

    def _get_sensor_type(self) -> str:
        return "tire_temp_driver_rear"

    @property
    def native_value(self) -> float:
        """Вернуть температуру"""
        parser = self._get_parser()
        if parser:
            tires = parser.get_tires_info()
            return round(tires['driver_rear_temp'], 1)
        return None


class ZeekrTireTempPassengerRearSensor(ZeekrBaseSensor):
    """Температура задней правой шины"""

    _attr_name = "Tire Temp - Passenger Rear"
    _attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS
    _attr_icon = "mdi:thermometer-lines"
    _attr_state_class = SensorStateClass.MEASUREMENT

    def _get_sensor_type(self) -> str:
        return "tire_temp_passenger_rear"

    @property
    def native_value(self) -> float:
        """Вернуть температуру"""
        parser = self._get_parser()
        if parser:
            tires = parser.get_tires_info()
            return round(tires['passenger_rear_temp'], 1)
        return None


# ==================== 🚙 ДВИЖЕНИЕ (РАСШИРЕНО) ====================

class ZeekrTripMeter1Sensor(ZeekrBaseSensor):
    """Одометр поездки 1"""

    _attr_name = "Trip Meter 1"
    _attr_native_unit_of_measurement = UnitOfLength.KILOMETERS
    _attr_icon = "mdi:road-variant"
    _attr_state_class = SensorStateClass.TOTAL_INCREASING

    def _get_sensor_type(self) -> str:
        return "trip_meter_1"

    @property
    def native_value(self) -> float:
        """Вернуть расстояние"""
        parser = self._get_parser()
        if parser:
            movement = parser.get_movement_info()
            return round(movement['trip_meter_1'], 1)
        return None


class ZeekrTripMeter2Sensor(ZeekrBaseSensor):
    """Одометр поездки 2"""

    _attr_name = "Trip Meter 2"
    _attr_native_unit_of_measurement = UnitOfLength.KILOMETERS
    _attr_icon = "mdi:road-variant"
    _attr_state_class = SensorStateClass.TOTAL_INCREASING

    def _get_sensor_type(self) -> str:
        return "trip_meter_2"

    @property
    def native_value(self) -> float:
        """Вернуть расстояние"""
        parser = self._get_parser()
        if parser:
            movement = parser.get_movement_info()
            return round(movement['trip_meter_2'], 1)
        return None


# ==================== 🔧 ОБСЛУЖИВАНИЕ (РАСШИРЕНО) ====================

class ZeekrEngineHoursToServiceSensor(ZeekrBaseSensor):
    """Часов до ТО"""

    _attr_name = "Engine Hours to Service"
    _attr_native_unit_of_measurement = "h"
    _attr_icon = "mdi:wrench-clock"
    _attr_state_class = SensorStateClass.MEASUREMENT

    def _get_sensor_type(self) -> str:
        return "engine_hours_to_service"

    @property
    def native_value(self) -> int:
        """Вернуть часы"""
        parser = self._get_parser()
        if parser:
            maintenance = parser.get_maintenance_info()
            return maintenance['engine_hours_to_service']
        return None


class ZeekrBrakeFluidLevelSensor(ZeekrBaseSensor):
    """Уровень тормозной жидкости"""

    _attr_name = "Brake Fluid Level"
    _attr_icon = "mdi:water-opacity"

    def _get_sensor_type(self) -> str:
        return "brake_fluid_level"

    @property
    def native_value(self) -> str:
        """Вернуть уровень"""
        parser = self._get_parser()
        if parser:
            maintenance = parser.get_maintenance_info()
            return maintenance['brake_fluid_level']
        return "Неизвестно"


class ZeekrWasherFluidLevelSensor(ZeekrBaseSensor):
    """Уровень жидкости омывателя"""

    _attr_name = "Washer Fluid Level"
    _attr_icon = "mdi:water-opacity"

    def _get_sensor_type(self) -> str:
        return "washer_fluid_level"

    @property
    def native_value(self) -> str:
        """Вернуть уровень"""
        parser = self._get_parser()
        if parser:
            maintenance = parser.get_maintenance_info()
            return maintenance['washer_fluid_level']
        return "Неизвестно"


class ZeekrEngineCoolantLevelSensor(ZeekrBaseSensor):
    """Уровень охлаждающей жидкости"""

    _attr_name = "Engine Coolant Level"
    _attr_icon = "mdi:water-opacity"

    def _get_sensor_type(self) -> str:
        return "engine_coolant_level"

    @property
    def native_value(self) -> str:
        """Вернуть уровень"""
        parser = self._get_parser()
        if parser:
            maintenance = parser.get_maintenance_info()
            return maintenance['engine_coolant_level']
        return "Неизвестно"


# ==================== 💨 ВОЗДУХ (РАСШИРЕНО) ====================

class ZeekrExteriorPM25LevelSensor(ZeekrBaseSensor):
    """Уровень PM2.5 снаружи"""

    _attr_name = "Exterior PM2.5 Level"
    _attr_icon = "mdi:air-filter"

    def _get_sensor_type(self) -> str:
        return "exterior_pm25_level"

    @property
    def native_value(self) -> str:
        """Вернуть уровень"""
        parser = self._get_parser()
        if parser:
            pollution = parser.get_pollution_info()
            return pollution['interior_pm25_level']
        return None


class ZeekrRelativeHumiditySensor(ZeekrBaseSensor):
    """Относительная влажность воздуха"""

    _attr_name = "Relative Humidity"
    _attr_native_unit_of_measurement = PERCENTAGE
    _attr_icon = "mdi:water-percent"
    _attr_state_class = SensorStateClass.MEASUREMENT

    def _get_sensor_type(self) -> str:
        return "relative_humidity"

    @property
    def native_value(self) -> int:
        """Вернуть влажность"""
        parser = self._get_parser()
        if parser:
            pollution = parser.get_pollution_info()
            return pollution['relative_humidity']
        return None


# ==================== 🅿️ ПАРКОВКА ====================

class ZeekrParkDurationSensor(ZeekrBaseSensor):
    """Длительность парковки"""

    _attr_name = "Park Duration"
    _attr_icon = "mdi:parking"

    def _get_sensor_type(self) -> str:
        return "park_duration"

    @property
    def native_value(self) -> str:
        """Вернуть длительность"""
        parser = self._get_parser()
        if parser:
            park = parser.get_park_info()
            return park['park_duration']
        return None

    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        """Дополнительные атрибуты"""
        parser = self._get_parser()
        if parser:
            park = parser.get_park_info()
            return {
                'parked_since': park['parked_since'],
                'total_seconds': park['total_seconds'],
                'is_parked': park['is_parked'],
            }
        return {}


class ZeekrElectricParkBrakeStatusSensor(ZeekrBaseSensor):
    """Статус электронного тормоза парковки"""

    _attr_name = "Electric Park Brake"
    _attr_icon = "mdi:hand-left"

    def _get_sensor_type(self) -> str:
        return "electric_park_brake"

    @property
    def native_value(self) -> str:
        """Вернуть статус тормоза парковки"""
        parser = self._get_parser()
        if parser:
            safety = parser.data.get('additionalVehicleStatus', {}).get('drivingSafetyStatus', {})
            status = int(safety.get('electricParkBrakeStatus', 0))

            status_map = {
                0: '❌ Выключен',
                1: '✅ ВКЛЮЧЕН (припаркован)',
                2: '⚠️ Ошибка',
            }
            return status_map.get(status, 'Неизвестно')
        return None


# ==================== 🎯 КЛИМАТ (РАСШИРЕНО) ====================

class ZeekrSteeringWheelHeatingStatusSensor(ZeekrBaseSensor):
    """Статус обогрева руля"""

    _attr_name = "Steering Wheel Heating"
    _attr_icon = "mdi:heating"

    def _get_sensor_type(self) -> str:
        return "steering_wheel_heating"

    @property
    def native_value(self) -> str:
        """Вернуть статус"""
        parser = self._get_parser()
        if parser:
            climate = parser.get_climate_info()
            return climate['steering_wheel_heating']
        return None


class ZeekrDriverHeatingStatusSensor(ZeekrBaseSensor):
    """Статус обогрева водителя"""

    _attr_name = "Driver Heating"
    _attr_icon = "mdi:heating"

    def _get_sensor_type(self) -> str:
        return "driver_heating"

    @property
    def native_value(self) -> str:
        """Вернуть статус"""
        parser = self._get_parser()
        if parser:
            climate = parser.get_climate_info()
            return climate['driver_heating']
        return None


class ZeekrPassengerHeatingStatusSensor(ZeekrBaseSensor):
    """Статус обогрева пассажира"""

    _attr_name = "Passenger Heating"
    _attr_icon = "mdi:heating"

    def _get_sensor_type(self) -> str:
        return "passenger_heating"

    @property
    def native_value(self) -> str:
        """Вернуть статус"""
        parser = self._get_parser()
        if parser:
            climate = parser.get_climate_info()
            return climate['passenger_heating']
        return None


# ==================== 📍 КООРДИНАТЫ ====================

class ZeekrLatitudeSensor(ZeekrBaseSensor):
    """Широта (для статистики и логирования)"""

    _attr_name = "Latitude"
    _attr_icon = "mdi:latitude"
    _attr_state_class = SensorStateClass.MEASUREMENT

    def _get_sensor_type(self) -> str:
        return "latitude"

    @property
    def native_value(self) -> float:
        """Вернуть широту"""
        parser = self._get_parser()
        if parser:
            position = parser.get_position_info()
            return round(position['latitude'], 6)
        return None


class ZeekrLongitudeSensor(ZeekrBaseSensor):
    """Долгота (для статистики и логирования)"""

    _attr_name = "Longitude"
    _attr_icon = "mdi:longitude"
    _attr_state_class = SensorStateClass.MEASUREMENT

    def _get_sensor_type(self) -> str:
        return "longitude"

    @property
    def native_value(self) -> float:
        """Вернуть долготу"""
        parser = self._get_parser()
        if parser:
            position = parser.get_position_info()
            return round(position['longitude'], 6)
        return None


class ZeekrAltitudeSensor(ZeekrBaseSensor):
    """Высота над уровнем моря"""

    _attr_name = "Altitude"
    _attr_native_unit_of_measurement = UnitOfLength.METERS
    _attr_icon = "mdi:elevation-rise"
    _attr_state_class = SensorStateClass.MEASUREMENT

    def _get_sensor_type(self) -> str:
        return "altitude"

    @property
    def native_value(self) -> int:
        """Вернуть высоту"""
        parser = self._get_parser()
        if parser:
            position = parser.get_position_info()
            return position['altitude']
        return None


# ==================== 🔐 ИНФОРМАЦИЯ ====================

class ZeekrPropulsionTypeSensor(ZeekrBaseSensor):
    """Тип пропульсии"""

    _attr_name = "Propulsion Type"
    _attr_icon = "mdi:fuel-cell"

    def _get_sensor_type(self) -> str:
        return "propulsion_type"

    @property
    def native_value(self) -> str:
        """Вернуть тип"""
        parser = self._get_parser()
        if parser:
            return parser.get_propulsion_type()
        return None


# ==================== ⚡ ЗАРЯДКА ====================

class ZeekrDCChargePowerSensor(ZeekrBaseSensor):
    """Мощность DC зарядки (кВт)"""

    _attr_name = "DC Charge Power"
    _attr_native_unit_of_measurement = "kW"
    _attr_icon = "mdi:lightning-bolt"
    _attr_device_class = SensorDeviceClass.POWER
    _attr_state_class = SensorStateClass.MEASUREMENT

    def _get_sensor_type(self) -> str:
        return "dc_charge_power"

    @property
    def native_value(self) -> float:
        """Вернуть мощность DC зарядки"""
        parser = self._get_parser()
        if parser:
            charging = parser.get_charging_info()
            return charging['dc_power']
        return None


class ZeekrDCChargeVoltageExtendedSensor(ZeekrBaseSensor):
    """Напряжение DC зарядки (детально)"""

    _attr_name = "DC Charge Voltage (Detailed)"
    _attr_native_unit_of_measurement = "V"
    _attr_icon = "mdi:flash"
    _attr_device_class = SensorDeviceClass.VOLTAGE
    _attr_state_class = SensorStateClass.MEASUREMENT

    def _get_sensor_type(self) -> str:
        return "dc_charge_voltage_detailed"

    @property
    def native_value(self) -> float:
        """Вернуть напряжение на зарядке"""
        parser = self._get_parser()
        if parser:
            charging = parser.get_charging_info()
            return round(charging['dc_charge_pile_voltage'], 1)
        return None


class ZeekrDCChargeCurrentExtendedSensor(ZeekrBaseSensor):
    """Ток DC зарядки (детально)"""

    _attr_name = "DC Charge Current (Detailed)"
    _attr_native_unit_of_measurement = "A"
    _attr_icon = "mdi:lightning-bolt"
    _attr_state_class = SensorStateClass.MEASUREMENT

    def _get_sensor_type(self) -> str:
        return "dc_charge_current_detailed"

    @property
    def native_value(self) -> float:
        """Вернуть ток зарядки"""
        parser = self._get_parser()
        if parser:
            charging = parser.get_charging_info()
            return round(charging['dc_charge_pile_current'], 1)
        return None


class ZeekrDCChargeStatusDetailedSensor(ZeekrBaseSensor):
    """Статус DC зарядки (детально)"""

    _attr_name = "DC Charge Status (Detailed)"
    _attr_icon = "mdi:battery-charging-wireless"

    def _get_sensor_type(self) -> str:
        return "dc_charge_status_detailed"

    @property
    def native_value(self) -> str:
        """Вернуть статус DC зарядки"""
        parser = self._get_parser()
        if parser:
            charging = parser.get_charging_info()
            return charging['dc_charge_status']
        return None


class ZeekrDCDCStatusSensor(ZeekrBaseSensor):
    """Статус DC/DC конвертера (400В → 12В)"""

    _attr_name = "DC/DC Converter Status"
    _attr_icon = "mdi:power-settings"

    def _get_sensor_type(self) -> str:
        return "dcdc_status"

    @property
    def native_value(self) -> str:
        """Вернуть статус конвертера"""
        parser = self._get_parser()
        if parser:
            charging = parser.get_charging_info()
            return charging['dc_dc_connect_status']
        return None

    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        """Дополнительные атрибуты"""
        parser = self._get_parser()
        if parser:
            charging = parser.get_charging_info()
            return {
                "activated": charging['dc_dc_activated'],
                "purpose": "Преобразует 400В в 12В для питания компонентов"
            }
        return {}


# ==================== РАЗРЯДКА (V2L, V2H) ====================

class ZeekrDischargePowerSensor(ZeekrBaseSensor):
    """Мощность разрядки V2L/V2H (кВт)"""

    _attr_name = "Discharge Power"
    _attr_native_unit_of_measurement = "kW"
    _attr_icon = "mdi:battery-arrow-up"
    _attr_device_class = SensorDeviceClass.POWER
    _attr_state_class = SensorStateClass.MEASUREMENT

    def _get_sensor_type(self) -> str:
        return "discharge_power"

    @property
    def native_value(self) -> float:
        """Вернуть мощность разрядки"""
        parser = self._get_parser()
        if parser:
            charging = parser.get_charging_info()
            return charging['discharge_power']
        return None


class ZeekrDischargeVoltageSensor(ZeekrBaseSensor):
    """Напряжение разрядки V2L/V2H (В)"""

    _attr_name = "Discharge Voltage"
    _attr_native_unit_of_measurement = "V"
    _attr_icon = "mdi:flash"
    _attr_device_class = SensorDeviceClass.VOLTAGE
    _attr_state_class = SensorStateClass.MEASUREMENT

    def _get_sensor_type(self) -> str:
        return "discharge_voltage"

    @property
    def native_value(self) -> float:
        """Вернуть напряжение разрядки"""
        parser = self._get_parser()
        if parser:
            charging = parser.get_charging_info()
            return round(charging['discharge_voltage'], 1)
        return None


class ZeekrDischargeCurrentSensor(ZeekrBaseSensor):
    """Ток разрядки V2L/V2H (А)"""

    _attr_name = "Discharge Current"
    _attr_native_unit_of_measurement = "A"
    _attr_icon = "mdi:lightning-bolt"
    _attr_state_class = SensorStateClass.MEASUREMENT

    def _get_sensor_type(self) -> str:
        return "discharge_current"

    @property
    def native_value(self) -> float:
        """Вернуть ток разрядки"""
        parser = self._get_parser()
        if parser:
            charging = parser.get_charging_info()
            return round(abs(charging['discharge_current']), 1)
        return None


class ZeekrChargerStateSensor(ZeekrBaseSensor):
    """Состояние зарядного устройства"""

    _attr_name = "Charger State"
    _attr_icon = "mdi:power-plug"

    def _get_sensor_type(self) -> str:
        return "charger_state"

    @property
    def native_value(self) -> str:
        """Вернуть состояние зарядного устройства"""
        parser = self._get_parser()
        if parser:
            charging = parser.get_charging_info()
            return charging['charger_state']
        return None


# ==================== ПАНОРАМНАЯ КРЫША (ИСПРАВЛЕННАЯ) ====================

class ZeekrFrontShadeSensor(ZeekrBaseSensor):
    """Передняя затемняющая шторка панорамной крыши"""

    _attr_name = "Front Shade Position"
    _attr_native_unit_of_measurement = "%"
    _attr_icon = "mdi:window-shutter"
    _attr_state_class = SensorStateClass.MEASUREMENT

    def _get_sensor_type(self) -> str:
        return "front_shade_position"

    @property
    def native_value(self) -> int:
        """Вернуть позицию передней шторки (0-101%)"""
        parser = self._get_parser()
        if parser:
            roof = parser.get_panoramic_roof_status()
            return roof['front_shade_position']
        return None

    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        """Дополнительная информация"""
        parser = self._get_parser()
        if parser:
            roof = parser.get_panoramic_roof_status()
            return {
                'status': roof['front_shade_status'],
                'is_open': roof['front_shade_open'],
                'is_transparent': roof['is_transparent'],
            }
        return {}


class ZeekrRearShadeSensor(ZeekrBaseSensor):
    """Задняя затемняющая шторка панорамной крыши"""

    _attr_name = "Rear Shade Position"
    _attr_native_unit_of_measurement = "%"
    _attr_icon = "mdi:window-shutter"
    _attr_state_class = SensorStateClass.MEASUREMENT

    def _get_sensor_type(self) -> str:
        return "rear_shade_position"

    @property
    def native_value(self) -> int:
        """Вернуть позицию задней шторки"""
        parser = self._get_parser()
        if parser:
            roof = parser.get_panoramic_roof_status()
            return roof['rear_shade_position']
        return None

    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        """Дополнительная информация"""
        parser = self._get_parser()
        if parser:
            roof = parser.get_panoramic_roof_status()
            return {
                'status': roof['rear_shade_status'],
                'is_open': roof['rear_shade_open'],
            }
        return {}


class ZeekrRoofStatusSensor(ZeekrBaseSensor):
    """Статус панорамной крыши - одно слово с процентом"""

    _attr_name = "Panoramic Roof Status"
    _attr_icon = "mdi:car-roof"

    def _get_sensor_type(self) -> str:
        return "roof_status"

    @property
    def native_value(self) -> str:
        """Вернуть простой статус крыши"""
        parser = self._get_parser()
        if parser:
            roof = parser.get_panoramic_roof_status()
            # Берем среднее значение между передней и задней шторкой
            avg_pos = (roof['front_shade_position'] + roof['rear_shade_position']) // 2

            if avg_pos >= 100:
                return f"Прозрачна - {avg_pos}%"
            elif avg_pos >= 75:
                return f"Прозрачна - {avg_pos}%"
            elif avg_pos >= 50:
                return f"Полупрозрачна - {avg_pos}%"
            elif avg_pos > 0:
                return f"Затемнена - {avg_pos}%"
            else:
                return f"Затемнена - 0%"
        return None

    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        """Дополнительная информация"""
        parser = self._get_parser()
        if parser:
            roof = parser.get_panoramic_roof_status()
            return {
                'roof_sealed': '✅ Герметична (не течет)',
                'front_pos': f"{roof['front_shade_position']}%",
                'rear_pos': f"{roof['rear_shade_position']}%",
                'front_status': roof['front_shade_status'],
                'rear_status': roof['rear_shade_status'],
            }
        return {}


# ==================== ДВИЖЕНИЕ И СКОРОСТЬ ====================

class ZeekrSpeedSensor(ZeekrBaseSensor):
    """Текущая скорость автомобиля"""

    _attr_name = "Speed"
    _attr_native_unit_of_measurement = UnitOfSpeed.KILOMETERS_PER_HOUR
    _attr_icon = "mdi:speedometer"
    _attr_state_class = SensorStateClass.MEASUREMENT

    def _get_sensor_type(self) -> str:
        return "speed"

    @property
    def native_value(self) -> float:
        """Вернуть текущую скорость"""
        parser = self._get_parser()
        if parser:
            movement = parser.get_movement_info()
            return movement['speed_numeric']
        return None


class ZeekrBrakeStatusSensor(ZeekrBaseSensor):
    """Статус тормозов / стоп-сигналы"""

    _attr_name = "Brake Status"
    _attr_icon = "mdi:brake-fluid"

    def _get_sensor_type(self) -> str:
        return "brake_status"

    @property
    def native_value(self) -> str:
        """Вернуть статус тормозов"""
        parser = self._get_parser()
        if parser:
            brake = parser.get_brake_status()
            return brake['brake_status']
        return None

    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        """Дополнительная информация"""
        parser = self._get_parser()
        if parser:
            brake = parser.get_brake_status()
            return {
                'is_braking': brake['is_braking'],
                'stop_lights_on': brake['stop_lights_on'],
            }
        return {}


class ZeekrEnergyRecoverySensor(ZeekrBaseSensor):
    """Статус рекуперативного торможения"""

    _attr_name = "Energy Recovery"
    _attr_icon = "mdi:lightning-bolt"

    def _get_sensor_type(self) -> str:
        return "energy_recovery"

    @property
    def native_value(self) -> str:
        """Вернуть статус восстановления энергии"""
        parser = self._get_parser()
        if parser:
            recovery = parser.estimate_battery_recovery()
            return recovery['recovery_status']
        return None

    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        """Дополнительная информация"""
        parser = self._get_parser()
        if parser:
            recovery = parser.estimate_battery_recovery()
            return {
                'is_recovering': recovery['is_recovering'],
                'is_braking': recovery['is_braking'],
                'speed': recovery['speed'],
                'current_charge': recovery['current_charge'],
            }
        return {}


class ZeekrGearStatusSensor(ZeekrBaseSensor):
    """Статус коробки передач"""

    _attr_name = "Gear Status"
    _attr_icon = "mdi:transmission-tower"

    def _get_sensor_type(self) -> str:
        return "gear_status"

    @property
    def native_value(self) -> str:
        """Вернуть статус коробки передач"""
        parser = self._get_parser()
        if parser:
            movement = parser.get_movement_info()
            return movement['gear_auto']
        return None


# ==================== РЕМНИ БЕЗОПАСНОСТИ ====================

class ZeekrSeatbeltDriverSensor(ZeekrBaseSensor):
    """Статус ремня безопасности водителя"""

    _attr_name = "Seatbelt Driver"
    _attr_icon = "mdi:seatbelt"

    def _get_sensor_type(self) -> str:
        return "seatbelt_driver"

    @property
    def native_value(self) -> str:
        """Вернуть статус ремня водителя"""
        parser = self._get_parser()
        if parser:
            belts = parser.get_seatbelt_status()
            return belts['driver_belted']
        return None

    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        """Дополнительная информация"""
        parser = self._get_parser()
        if parser:
            belts = parser.get_seatbelt_status()
            return {
                'is_belted': belts['driver_belted'].startswith('✅'),
                'safety_alert': belts['safety_alert'],
            }
        return {}


class ZeekrSeatbeltPassengerSensor(ZeekrBaseSensor):
    """Статус ремня безопасности пассажира"""

    _attr_name = "Seatbelt Passenger"
    _attr_icon = "mdi:seatbelt"

    def _get_sensor_type(self) -> str:
        return "seatbelt_passenger"

    @property
    def native_value(self) -> str:
        """Вернуть статус ремня пассажира"""
        parser = self._get_parser()
        if parser:
            belts = parser.get_seatbelt_status()
            return belts['passenger_belted']
        return None


class ZeekrSeatbeltStatusSensor(ZeekrBaseSensor):
    """Общий статус всех ремней безопасности"""

    _attr_name = "Seatbelt Status"
    _attr_icon = "mdi:seatbelt"

    def _get_sensor_type(self) -> str:
        return "seatbelt_status"

    @property
    def native_value(self) -> str:
        """Вернуть общий статус"""
        parser = self._get_parser()
        if parser:
            belts = parser.get_seatbelt_status()
            return belts['safety_alert']
        return None

    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        """Дополнительная информация"""
        parser = self._get_parser()
        if parser:
            belts = parser.get_seatbelt_status()
            return {
                'driver': belts['driver_belted'],
                'passenger': belts['passenger_belted'],
                'driver_rear': belts['driver_rear_belted'],
                'passenger_rear': belts['passenger_rear_belted'],
                'all_belted': belts['all_belted'],
            }
        return {}


# ==================== GPS И НАВИГАЦИЯ ====================

class ZeekrGpsStatusSensor(ZeekrBaseSensor):
    """Статус GPS сигнала"""

    _attr_name = "GPS Status"
    _attr_icon = "mdi:satellite-variant"

    def _get_sensor_type(self) -> str:
        return "gps_status"

    @property
    def native_value(self) -> str:
        """Вернуть статус GPS"""
        parser = self._get_parser()
        if parser:
            gps = parser.get_gps_status()
            return gps['gps_status']
        return None

    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        """Дополнительная информация"""
        parser = self._get_parser()
        if parser:
            gps = parser.get_gps_status()
            return {
                'has_signal': gps['has_gps_signal'],
                'coordinates_trusted': gps['coordinates_trusted'],
                'location_upload': gps['location_upload_enabled'],
                'latitude': gps['latitude'],
                'longitude': gps['longitude'],
            }
        return {}


# ==================== ОГНИ ====================

class ZeekrLightsStatusSensor(ZeekrBaseSensor):
    """Общий статус всех огней"""

    _attr_name = "Lights Status"
    _attr_icon = "mdi:lightbulb-group"

    def _get_sensor_type(self) -> str:
        return "lights_status"

    @property
    def native_value(self) -> str:
        """Вернуть статус огней"""
        parser = self._get_parser()
        if parser:
            lights = parser.get_lights_status()
            return lights['lights_status']
        return None

    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        """Дополнительная информация"""
        parser = self._get_parser()
        if parser:
            lights = parser.get_lights_status()
            return {
                'drl': lights['drl_active'],
                'hi_beam': lights['hi_beam'],
                'lo_beam': lights['lo_beam'],
                'stop_lights': lights['stop_lights'],
                'is_night_mode': lights['is_night_mode'],
            }
        return {}


# ==================== ОХРАНА И БЕЗОПАСНОСТЬ ====================

class ZeekrTheftProtectionSensor(ZeekrBaseSensor):
    """Статус защиты от кражи"""

    _attr_name = "Theft Protection"
    _attr_icon = "mdi:security"

    def _get_sensor_type(self) -> str:
        return "theft_protection"

    @property
    def native_value(self) -> str:
        """Вернуть статус защиты"""
        parser = self._get_parser()
        if parser:
            theft = parser.get_theft_and_security_status()
            return theft['theft_protection']
        return None

    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        """Дополнительная информация"""
        parser = self._get_parser()
        if parser:
            theft = parser.get_theft_and_security_status()
            return {
                'theft_activated': theft['theft_activated'],
                'engine_locked': theft['engine_locked'],
                'activation_time': theft['activation_time'],
            }
        return {}
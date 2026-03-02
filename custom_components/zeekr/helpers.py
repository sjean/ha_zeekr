# custom_components/zeekr/helpers.py
"""
Вспомогательные функции для создания групп и автоматической организации датчиков
"""
import logging
from typing import Dict, List
from homeassistant.core import HomeAssistant
from homeassistant.const import ATTR_ENTITY_ID

_LOGGER = logging.getLogger(__name__)

# ==================== ОПРЕДЕЛЕНИЕ ГРУПП ====================

SENSOR_GROUPS = {
    "🔋 Батарея": {
        "icon": "mdi:battery",
        "sensors": [
            "battery",
            "battery_12v_percentage",
            "battery_12v_voltage",
            "distance_to_empty",
            "state_of_charge",
            "state_of_health",
            "hv_temp_level",
            "time_to_full_charge",
        ],
    },
    "🌡️ Температура": {
        "icon": "mdi:thermometer",
        "sensors": [
            "interior_temp",
            "exterior_temp",
            "hv_temp_level",
            "tire_temp_driver_front",
            "tire_temp_passenger_front",
            "tire_temp_driver_rear",
            "tire_temp_passenger_rear",
        ],
    },
    "🛞 Шины": {
        "icon": "mdi:tire",
        "sensors": [
            "tire_pressure_driver",
            "tire_pressure_passenger",
            "tire_pressure_driver_rear",
            "tire_pressure_passenger_rear",
            "tire_temp_driver_front",
            "tire_temp_passenger_front",
            "tire_temp_driver_rear",
            "tire_temp_passenger_rear",
        ],
    },
    "🚙 Движение": {
        "icon": "mdi:speedometer",
        "sensors": [
            "current_speed",
            "average_speed",
            "speed",
            "brake_status",
            "gear_status",
            "energy_recovery",
            "trip_meter_1",
            "trip_meter_2",
        ],
    },
    "🔧 Обслуживание": {
        "icon": "mdi:wrench",
        "sensors": [
            "odometer",
            "days_to_service",
            "distance_to_service",
            "engine_hours_to_service",
            "brake_fluid_level",
            "washer_fluid_level",
            "engine_coolant_level",
        ],
    },
    "⚡ Зарядка": {
        "icon": "mdi:battery-charging",
        "sensors": [
            "dc_charge_power",
            "dc_charge_voltage_detailed",
            "dc_charge_current_detailed",
            "dc_charge_status_detailed",
            "dcdc_status",
            "time_to_full_charge",
        ],
    },
    "⚡ Разрядка (V2L/V2H)": {
        "icon": "mdi:battery-arrow-up",
        "sensors": [
            "discharge_power",
            "discharge_voltage",
            "discharge_current",
            "charger_state",
        ],
    },
    "☀️ Панорамная крыша": {
        "icon": "mdi:car-roof",
        "sensors": [
            "front_shade_position",
            "rear_shade_position",
            "roof_status",
        ],
        "binary_sensors": [
            "front_shade_open",
            "rear_shade_open",
            "roof_transparent",
        ],
    },
    "🔒 Безопасность": {
        "icon": "mdi:security",
        "binary_sensors": [
            "driver_door",
            "passenger_door",
            "driver_rear_door",
            "passenger_rear_door",
            "trunk",
            "engine_hood",
            "engine",
        ],
        "sensors": [
            "theft_protection",
            "electric_park_brake",
        ],
    },
    "📍 Местоположение": {
        "icon": "mdi:map-marker",
        "device_trackers": [
            "location",
        ],
        "sensors": [
            "latitude",
            "longitude",
            "altitude",
        ],
        "binary_sensors": [
            "gps_active",
        ],
    },
    "💨 Качество воздуха": {
        "icon": "mdi:air-filter",
        "sensors": [
            "interior_pm25",
            "exterior_pm25_level",
            "relative_humidity",
        ],
    },
    "🅿️ Парковка": {
        "icon": "mdi:parking",
        "sensors": [
            "park_duration",
        ],
    },
    "🎯 Климат": {
        "icon": "mdi:thermometer",
        "sensors": [
            "interior_temp",
            "exterior_temp",
            "steering_wheel_heating",
            "driver_heating",
            "passenger_heating",
        ],
    },
    "🔐 Ремни безопасности": {
        "icon": "mdi:seatbelt",
        "binary_sensors": [
            "seatbelt_driver",
            "seatbelt_passenger",
        ],
        "sensors": [
            "seatbelt_driver",
            "seatbelt_passenger",
            "seatbelt_status",
        ],
    },
    "💡 Огни": {
        "icon": "mdi:lightbulb-group",
        "sensors": [
            "lights_status",
            "brake_status",
        ],
    },
    "🚗 Статус": {
        "icon": "mdi:car",
        "sensors": [
            "last_update_time",
            "battery",
            "theft_protection",
            "electric_park_brake",
        ],
    },
}


async def async_create_groups(hass: HomeAssistant, vin: str) -> bool:
    """
    ⭐ АСИНХРОННО СОЗДАЕТ ГРУППЫ В HOME ASSISTANT

    Все группы создаются программно (не в YAML файлах!)

    Args:
        hass: Home Assistant instance
        vin: VIN номер автомобиля

    Returns:
        True если успешно, False если ошибка
    """
    _LOGGER.info(f"📊 Начинаю создание групп для {vin}...")

    try:
        vin_lower = vin.lower()
        groups_created = 0

        for group_name, group_config in SENSOR_GROUPS.items():
            # Собираем все entity_id для этой группы
            entities = []

            # Обычные датчики
            for sensor in group_config.get("sensors", []):
                entity_id = f"sensor.zeekr_{vin_lower}_{sensor}"
                entities.append(entity_id)

            # Бинарные датчики
            for binary_sensor in group_config.get("binary_sensors", []):
                entity_id = f"binary_sensor.zeekr_{vin_lower}_{binary_sensor}"
                entities.append(entity_id)

            # Device trackers
            for device_tracker in group_config.get("device_trackers", []):
                entity_id = f"device_tracker.zeekr_{vin_lower}_{device_tracker}"
                entities.append(entity_id)

            if not entities:
                _LOGGER.debug(f"⏭️  Группа '{group_name}' не содержит сущностей, пропускаю")
                continue

            # Создаём группу с уникальным ID
            group_id = f"zeekr_{vin_lower}_{group_name.lower().replace(' ', '_').replace('🔋', 'battery').replace('🌡️', 'temp').replace('🛞', 'tires').replace('🚙', 'move').replace('🔧', 'service').replace('⚡', 'charge').replace('☀️', 'roof').replace('🔒', 'security').replace('📍', 'location').replace('💨', 'air').replace('🅿️', 'park').replace('🎯', 'climate').replace('🔐', 'belts').replace('💡', 'lights').replace('🚗', 'status')}"

            service_data = {
                "object_id": group_id,
                "name": group_name,
                "icon": group_config.get("icon", "mdi:folder"),
                "entities": entities,
            }

            _LOGGER.debug(f"🔨 Создаю группу: {group_name} с {len(entities)} сущностями")

            # Вызываем сервис Home Assistant для создания группы
            await hass.services.async_call(
                "group",
                "create",
                service_data,
                blocking=True,
            )

            groups_created += 1
            _LOGGER.info(f"✅ Создана группа: {group_name}")

        _LOGGER.info(f"🎉 Успешно создано {groups_created} групп для {vin}")
        return True

    except Exception as e:
        _LOGGER.error(f"❌ Ошибка при создании групп: {e}", exc_info=True)
        return False


def get_entity_category(sensor_type: str) -> str:
    """
    Возвращает категорию сущности для правильной группировки в UI

    Args:
        sensor_type: тип датчика (например 'battery', 'temperature')

    Returns:
        Категория для entity_category атрибута
    """
    # Основные показатели - без категории (None)
    main_entities = {
        "battery",  # Основной заряд батареи
        "interior_temp",
        "exterior_temp",
        "current_speed",
        "odometer",
        "last_update_time",
    }

    # Диагностические данные
    diagnostic_entities = {
        "battery_12v_percentage",
        "battery_12v_voltage",
        "distance_to_empty",
        "state_of_charge",
        "state_of_health",
        "hv_temp_level",
        "tire_pressure_driver",
        "tire_pressure_passenger",
        "tire_pressure_driver_rear",
        "tire_pressure_passenger_rear",
        "days_to_service",
        "distance_to_service",
        "engine_hours_to_service",
    }

    if sensor_type in main_entities:
        return None  # Основные
    elif sensor_type in diagnostic_entities:
        return "diagnostic"  # Диагностика
    else:
        return "diagnostic"  # По умолчанию диагностика
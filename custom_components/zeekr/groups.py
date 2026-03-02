# custom_components/zeekr/groups.py
"""
Динамическое создание групп датчиков Zeekr
Автоматически записывает в configuration.yaml

⭐ ВАЖНО: Все операции с файлами АСИНХРОННЫЕ!
"""

import logging
import os
from typing import Dict, List
from homeassistant.core import HomeAssistant

_LOGGER = logging.getLogger(__name__)

# Определения групп
SENSOR_GROUPS = {
    "🔋 Батарея": [
        "battery",
        "battery_12v_percentage",
        "battery_12v_voltage",
        "distance_to_empty",
        "state_of_charge",
        "state_of_health",
        "hv_temp_level",
        "time_to_full_charge",
    ],

    "🌡️ Температура": [
        "interior_temp",
        "exterior_temp",
        "hv_temp_level",
        "tire_temp_driver_front",
        "tire_temp_passenger_front",
        "tire_temp_driver_rear",
        "tire_temp_passenger_rear",
    ],

    "🛞 Шины": [
        "tire_pressure_driver",
        "tire_pressure_passenger",
        "tire_pressure_driver_rear",
        "tire_pressure_passenger_rear",
        "tire_temp_driver_front",
        "tire_temp_passenger_front",
        "tire_temp_driver_rear",
        "tire_temp_passenger_rear",
    ],

    "🚙 Движение": [
        "current_speed",
        "average_speed",
        "speed",
        "brake_status",
        "gear_status",
        "energy_recovery",
        "trip_meter_1",
        "trip_meter_2",
    ],

    "🔧 Обслуживание": [
        "odometer",
        "days_to_service",
        "distance_to_service",
        "engine_hours_to_service",
        "brake_fluid_level",
        "washer_fluid_level",
        "engine_coolant_level",
    ],

    "⚡ Зарядка": [
        "dc_charge_power",
        "dc_charge_voltage_detailed",
        "dc_charge_current_detailed",
        "dc_charge_status_detailed",
        "dcdc_status",
        "time_to_full_charge",
    ],

    "⚡ Разрядка": [
        "discharge_power",
        "discharge_voltage",
        "discharge_current",
        "charger_state",
    ],

    "☀️ Панорамная Крыша": [
        "front_shade_position",
        "rear_shade_position",
        "roof_status",
    ],

    "🔒 Безопасность": [
        "seatbelt_driver",
        "seatbelt_passenger",
        "seatbelt_status",
    ],

    "📍 Местоположение": [
        "latitude",
        "longitude",
        "altitude",
        "gps_status",
    ],

    "💡 Огни": [
        "lights_status",
    ],

    "💨 Воздух": [
        "pm25_interior",
        "exterior_pm25_level",
        "relative_humidity",
    ],

    "🅿️ Парковка": [
        "park_duration",
    ],

    "🎯 Климат": [
        "interior_temp",
        "exterior_temp",
        "steering_wheel_heating",
        "driver_heating",
        "passenger_heating",
    ],

    "🚗 Статус": [
        "last_update_time",
        "battery",
        "theft_protection",
        "electric_park_brake",
    ],
}


async def async_setup_groups(hass: HomeAssistant, vin: str) -> bool:
    """
    ⭐ АСИНХРОННО создаёт группы в configuration.yaml

    Осторожно работает с файлом чтобы сохранить !include теги и комментарии
    Использует executor чтобы не блокировать event loop!

    Args:
        hass: Home Assistant инстанс
        vin: VIN автомобиля

    Returns:
        True если успешно, False если ошибка
    """
    try:
        config_path = hass.config.path("configuration.yaml")

        _LOGGER.info(f"📝 Начинаю создание групп для {vin}...")

        # ⭐ АСИНХРОННЫЙ вызов синхронной функции в отдельном потоке
        result = await hass.async_add_executor_job(
            _setup_groups_sync,
            config_path,
            vin
        )

        return result

    except Exception as e:
        _LOGGER.error(f"❌ Ошибка при создании групп: {e}", exc_info=True)
        return False


def _setup_groups_sync(config_path: str, vin: str) -> bool:
    """
    ⭐ СИНХРОННАЯ функция для работы с файлами
    Выполняется в отдельном потоке через executor

    Args:
        config_path: Путь к configuration.yaml
        vin: VIN автомобиля

    Returns:
        True если успешно, False если ошибка
    """
    try:
        _LOGGER.debug(f"🔍 Загружаю текущую конфигурацию из {config_path}...")

        # 1️⃣ Читаем файл как текст (сохраняем комментарии и !include)
        with open(config_path, 'r', encoding='utf-8') as f:
            original_lines = f.readlines()

        if not original_lines:
            _LOGGER.error("❌ Файл configuration.yaml пуст!")
            return False

        # 2️⃣ Ищем секцию group в файле
        group_section_start = None
        group_section_end = None

        for i, line in enumerate(original_lines):
            if line.strip() == 'group:' or line.startswith('group:'):
                group_section_start = i
                _LOGGER.debug(f"✅ Найдена секция 'group' на строке {i + 1}")
                break

        # 3️⃣ Генерируем новые группы
        vin_lower = vin.lower()
        new_group_lines = []
        groups_added = 0

        group_id = 1
        for group_name, sensors in SENSOR_GROUPS.items():
            group_key = f"zeekr_{vin_lower}_group_{group_id}"

            # Проверяем не добавлена ли уже эта группа
            is_existing = any(group_key in line for line in original_lines)

            if is_existing:
                _LOGGER.debug(f"⏭️  Группа {group_key} уже существует, пропускаю")
                group_id += 1
                continue

            # Создаём строки YAML для группы
            new_group_lines.append(f"  {group_key}:\n")
            new_group_lines.append(f"    name: \"{group_name}\"\n")
            new_group_lines.append(f"    entities:\n")

            for sensor in sensors:
                new_group_lines.append(f"      - sensor.zeekr_{vin_lower}_{sensor}\n")

            new_group_lines.append("\n")

            _LOGGER.info(f"✅ Добавлена группа: {group_name} ({len(sensors)} датчиков)")
            groups_added += 1
            group_id += 1

        # 4️⃣ Если нет ни одной новой группы - выходим
        if groups_added == 0:
            _LOGGER.info("ℹ️  Все группы уже добавлены, обновления не требуются")
            return True

        # 5️⃣ Записываем обновленный файл
        if group_section_start is not None:
            # Группа существует - добавляем в конец секции
            _LOGGER.debug("🔄 Обновляю существующую секцию 'group'")

            # Находим конец секции group
            for i in range(group_section_start + 1, len(original_lines)):
                line = original_lines[i]
                # Конец секции - это строка которая не начинается с пробела и не пуста
                if line.strip() and not line.startswith(' ') and not line.startswith('\t'):
                    group_section_end = i
                    break

            if group_section_end is None:
                group_section_end = len(original_lines)

            # Вставляем новые группы перед концом секции
            updated_lines = (
                    original_lines[:group_section_end] +
                    new_group_lines +
                    original_lines[group_section_end:]
            )

        else:
            # Группа не существует - добавляем в конец файла
            _LOGGER.info("➕ Добавляю новую секцию 'group' в конец файла")

            updated_lines = (
                    original_lines +
                    ["\n", "# ==================== ZEEKR GROUPS ====================\n", "group:\n"] +
                    new_group_lines
            )

        # 6️⃣ Записываем обновленный файл
        _LOGGER.debug("💾 Сохраняю конфигурацию...")

        with open(config_path, 'w', encoding='utf-8') as f:
            f.writelines(updated_lines)

        _LOGGER.info(f"🎉 Успешно добавлено {groups_added} групп в configuration.yaml")
        _LOGGER.info("⚠️  ПЕРЕЗАГРУЗИ Home Assistant чтобы применить изменения!")

        return True

    except FileNotFoundError:
        _LOGGER.error(f"❌ Файл не найден: {config_path}")
        return False
    except Exception as e:
        _LOGGER.error(f"❌ Ошибка при сохранении групп: {e}", exc_info=True)
        return False


def get_group_entities_for_vin(vin: str, group_name: str) -> List[str]:
    """
    Получает список entity_id для группы и VIN

    Args:
        vin: VIN автомобиля
        group_name: Название группы

    Returns:
        Список полных entity_id
    """
    if group_name not in SENSOR_GROUPS:
        return []

    entities = []
    vin_lower = vin.lower()

    for sensor_type in SENSOR_GROUPS[group_name]:
        entity_id = f"sensor.zeekr_{vin_lower}_{sensor_type}"
        entities.append(entity_id)

    return entities
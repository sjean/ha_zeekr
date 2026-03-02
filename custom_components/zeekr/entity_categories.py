# custom_components/zeekr/entity_categories.py
"""
Определения категорий для датчиков Zeekr

🎯 КАТЕГОРИИ:
- None: Основные показатели (видны на главном экране)
- DIAGNOSTIC: Диагностические данные (скрыты в "Диагностика")
- CONFIG: Параметры конфигурации (скрыты в "Конфигурация")
- SYSTEM: Системная информация (скрыты в "Система")
"""

from homeassistant.const import EntityCategory
from typing import Dict, Optional

# ==================== ОСНОВНЫЕ ПОКАЗАТЕЛИ ====================
# 🎯 Видны на главном экране и в карточках
MAIN_CATEGORY_SENSORS = {
    "battery",  # 🔋 Заряд батареи (%)
    "interior_temp",  # 🌡️ Температура салона
    "exterior_temp",  # 🌡️ Температура снаружи
    "current_speed",  # 🚗 Текущая скорость
    "speed",  # 🚗 Скорость (альтернатива)
    "distance_to_empty",  # 🛣️ Запас хода
    "odometer",  # 📍 Одометр
    "average_speed",  # 📊 Средняя скорость
}

# ==================== ДИАГНОСТИЧЕСКИЕ ДАННЫЕ ====================
# ⚙️ Скрыты в "Диагностика" (для специалистов)
DIAGNOSTIC_CATEGORY_SENSORS = {
    # 🔋 БАТАРЕЯ (расширено)
    "battery_12v_percentage",  # 12V батарея %
    "battery_12v_voltage",  # 12V напряжение
    "state_of_charge",  # SOC параметр
    "state_of_health",  # SOH параметр
    "hv_temp_level",  # Температура батареи уровень
    "time_to_full_charge",  # Время зарядки

    # 🛞 ШИНЫ
    "tire_pressure_driver",  # Шина ПЛ давление
    "tire_pressure_passenger",  # Шина ПП давление
    "tire_pressure_driver_rear",  # Шина ЗЛ давление
    "tire_pressure_passenger_rear",  # Шина ЗП давление
    "tire_temp_driver_front",  # Шина ПЛ температура
    "tire_temp_passenger_front",  # Шина ПП температура
    "tire_temp_driver_rear",  # Шина ЗЛ температура
    "tire_temp_passenger_rear",  # Шина ЗП температура

    # 🔧 ОБСЛУЖИВАНИЕ
    "days_to_service",  # Дней до ТО
    "distance_to_service",  # Км до ТО
    "engine_hours_to_service",  # Часов до ТО
    "brake_fluid_level",  # Тормозная жидкость
    "washer_fluid_level",  # Омыватель
    "engine_coolant_level",  # Охлаждающая жидкость

    # 💨 ВОЗДУХ
    "interior_pm25",  # PM2.5 салона
    "exterior_pm25_level",  # PM2.5 снаружи
    "relative_humidity",  # Влажность воздуха

    # 🎯 КЛИМАТ
    "steering_wheel_heating",  # Обогрев руля
    "driver_heating",  # Обогрев водителя
    "passenger_heating",  # Обогрев пассажира

    # 🅿️ ПАРКОВКА
    "park_duration",  # Время парковки

    # 🚙 ДВИЖЕНИЕ (расширено)
    "trip_meter_1",  # Счётчик 1
    "trip_meter_2",  # Счётчик 2
    "brake_status",  # Статус тормозов
    "energy_recovery",  # Рекуперация энергии
    "gear_status",  # Коробка передач

    # ☀️ ПАНОРАМНАЯ КРЫША
    "front_shade_position",  # Передняя шторка %
    "rear_shade_position",  # Задняя шторка %
    "roof_status",  # Статус крыши

    # ⚡ ЗАРЯДКА
    "dc_charge_power",  # Мощность DC зарядки
    "dc_charge_voltage_detailed",  # Напряжение DC зарядки
    "dc_charge_current_detailed",  # Ток DC зарядки
    "dc_charge_status_detailed",  # Статус DC зарядки
    "dcdc_status",  # DC/DC конвертер

    # ⚡ РАЗРЯДКА V2L/V2H
    "discharge_power",  # Мощность разрядки
    "discharge_voltage",  # Напряжение разрядки
    "discharge_current",  # Ток разрядки
    "charger_state",  # Состояние зарядки

    # 📡 GPS И НАВИГАЦИЯ
    "gps_status",  # GPS статус
    "latitude",  # Широта
    "longitude",  # Долгота
    "altitude",  # Высота

    # 🔒 РЕМНИ БЕЗОПАСНОСТИ
    "seatbelt_driver",  # Ремень водителя
    "seatbelt_passenger",  # Ремень пассажира
    "seatbelt_status",  # Статус ремней

    # 💡 ОГНИ
    "lights_status",  # Статус огней

    # 🔐 ИНФОРМАЦИЯ
    "propulsion_type",  # Тип пропульсии

    # 📊 СТАТУС И ОХРАНА
    "last_update_time",  # Последнее обновление
    "theft_protection",  # Охрана от кражи
    "electric_park_brake",  # Электронный ручной тормоз
}

# ==================== КОНФИГУРАЦИОННЫЕ ДАННЫЕ ====================
# ⚙️ Скрыты в "Конфигурация" (редко используются)
CONFIG_CATEGORY_SENSORS = {
    # (пока нет - можно добавить в будущем)
}

# ==================== СИСТЕМНАЯ ИНФОРМАЦИЯ ====================
# 🖥️ Скрыты в "Система" (служебная информация)
SYSTEM_CATEGORY_SENSORS = {
    # (пока нет - можно добавить в будущем)
}


def get_entity_category(sensor_type: str) -> Optional[EntityCategory]:
    """
    Получает категорию для датчика по типу

    Args:
        sensor_type (str): Тип датчика (например 'battery', 'interior_temp')

    Returns:
        EntityCategory | None:
            - None: Основной показатель (видно везде)
            - EntityCategory.DIAGNOSTIC: Диагностика
            - EntityCategory.CONFIG: Конфигурация
            - EntityCategory.SYSTEM: Система

    Example:
        >>> get_entity_category('battery')
        None
        >>> get_entity_category('tire_pressure_driver')
        <EntityCategory.DIAGNOSTIC: 'diagnostic'>
    """
    # Проверяем основные показатели
    if sensor_type in MAIN_CATEGORY_SENSORS:
        return None

    # Проверяем диагностику
    elif sensor_type in DIAGNOSTIC_CATEGORY_SENSORS:
        return EntityCategory.DIAGNOSTIC

    # Проверяем конфигурацию
    elif sensor_type in CONFIG_CATEGORY_SENSORS:
        return EntityCategory.CONFIG

    # Проверяем систему
    elif sensor_type in SYSTEM_CATEGORY_SENSORS:
        return EntityCategory.SYSTEM

    # По умолчанию - диагностика (безопасный вариант)
    else:
        return EntityCategory.DIAGNOSTIC


def get_all_sensor_categories() -> Dict[str, str]:
    """
    Возвращает словарь со всеми датчиками и их категориями

    Returns:
        Dict[str, str]: {sensor_type: category_name}

    Example:
        >>> categories = get_all_sensor_categories()
        >>> categories['battery']
        'main'
        >>> categories['tire_pressure_driver']
        'diagnostic'
    """
    result = {}

    # Добавляем основные
    for sensor in MAIN_CATEGORY_SENSORS:
        result[sensor] = "main"

    # Добавляем диагностику
    for sensor in DIAGNOSTIC_CATEGORY_SENSORS:
        result[sensor] = "diagnostic"

    # Добавляем конфигурацию
    for sensor in CONFIG_CATEGORY_SENSORS:
        result[sensor] = "config"

    # Добавляем систему
    for sensor in SYSTEM_CATEGORY_SENSORS:
        result[sensor] = "system"

    return result


def print_categories_info():
    """
    Выводит информацию о категориях в логи (для отладки)

    Usage:
        >>> from .entity_categories import print_categories_info
        >>> print_categories_info()
    """
    import logging
    logger = logging.getLogger(__name__)

    logger.info("=" * 80)
    logger.info("📊 КАТЕГОРИИ ДАТЧИКОВ ZEEKR")
    logger.info("=" * 80)

    logger.info(f"🎯 ОСНОВНЫЕ ПОКАЗАТЕЛИ: {len(MAIN_CATEGORY_SENSORS)} датчиков")
    for sensor in sorted(MAIN_CATEGORY_SENSORS):
        logger.info(f"  ✅ {sensor}")

    logger.info(f"\n⚙️ ДИАГНОСТИКА: {len(DIAGNOSTIC_CATEGORY_SENSORS)} датчиков")
    for sensor in sorted(DIAGNOSTIC_CATEGORY_SENSORS):
        logger.info(f"  🔧 {sensor}")

    logger.info(f"\n⚙️ КОНФИГУРАЦИЯ: {len(CONFIG_CATEGORY_SENSORS)} датчиков")
    for sensor in sorted(CONFIG_CATEGORY_SENSORS):
        logger.info(f"  ⚙️ {sensor}")

    logger.info(f"\n🖥️ СИСТЕМА: {len(SYSTEM_CATEGORY_SENSORS)} датчиков")
    for sensor in sorted(SYSTEM_CATEGORY_SENSORS):
        logger.info(f"  🖥️ {sensor}")

    logger.info("=" * 80)


# ==================== ИНФОРМАЦИЯ О РАСПРЕДЕЛЕНИИ ====================
"""
📊 ИТОГОВАЯ СТАТИСТИКА:

🎯 ОСНОВНЫЕ ПОКАЗАТЕЛИ (8 датчиков):
   - Видны на главном экране
   - Видны в карточках устройства
   - Видны в автоматизациях
   ✅ battery
   ✅ interior_temp
   ✅ exterior_temp
   ✅ current_speed
   ✅ speed
   ✅ distance_to_empty
   ✅ odometer
   ✅ average_speed

⚙️ ДИАГНОСТИЧЕСКИЕ ДАННЫЕ (56 датчиков):
   - Скрыты в "Диагностика" на вкладке "Устройство"
   - Видны в автоматизациях
   - Нужны для анализа и отладки

   🔋 БАТАРЕЯ (расширено): 6 датчиков
   🛞 ШИНЫ: 8 датчиков
   🔧 ОБСЛУЖИВАНИЕ: 6 датчиков
   💨 ВОЗДУХ: 3 датчика
   🎯 КЛИМАТ: 3 датчика
   🅿️ ПАРКОВКА: 1 датчик
   🚙 ДВИЖЕНИЕ: 5 датчиков
   ☀️ КРЫША: 3 датчика
   ⚡ ЗАРЯДКА: 5 датчиков
   ⚡ РАЗРЯДКА: 4 датчика
   📡 GPS: 4 датчика
   🔒 РЕМНИ: 3 датчика
   💡 ОГНИ: 1 датчик
   🔐 ИНФОРМАЦИЯ: 1 датчик
   📊 СТАТУС: 3 датчика

⚙️ КОНФИГУРАЦИОННЫЕ ДАННЫЕ (0 датчиков):
   - Зарезервировано для будущего использования

🖥️ СИСТЕМНАЯ ИНФОРМАЦИЯ (0 датчиков):
   - Зарезервировано для будущего использования

ВСЕГО: 64 датчика
"""
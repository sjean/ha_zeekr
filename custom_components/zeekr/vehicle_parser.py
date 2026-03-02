# custom_components/zeekr/vehicle_parser.py

"""
Парсер данных автомобиля - извлечение и форматирование информации
ОБНОВЛЕНО: Правильная интерпретация панорамной крыши (затемняющей шторки)
"""
from typing import Dict, Any, Optional
from datetime import datetime


class VehicleDataParser:
    """Парсер для извлечения всей информации о статусе автомобиля"""

    def _calculate_dc_power(self, voltage: float, current: float) -> float:
        """
        Рассчитывает мощность DC зарядки
        Формула: Мощность (кВт) = Напряжение (В) × Ток (А) / 1000
        """
        if voltage and current:
            power_kw = (voltage * abs(current)) / 1000
            return round(power_kw, 1)
        return 0.0

    def _calculate_discharge_power(self, voltage: float, current: float) -> float:
        """Рассчитывает мощность разрядки (V2L, V2H)"""
        if voltage and current:
            power_kw = (voltage * abs(current)) / 1000
            return round(power_kw, 1)
        return 0.0

    def _parse_dc_charge_status(self, status_code: str) -> str:
        """Парсит статус DC зарядки"""
        status_map = {
            '0': '❌ Не активна',
            '1': '⚡ Активна (подключена)',
            '2': '🔋 Зарядка в процессе',
            '3': '✅ Зарядка завершена',
            '4': '⏸️ Приостановлена',
        }
        return status_map.get(str(status_code), f'❓ Неизвестно ({status_code})')

    def _parse_dc_dc_status(self, status_code: str) -> str:
        """Парсит статус DC/DC конвертера (преобразует 400В в 12В)"""
        status_map = {
            '0': '❌ Отключен',
            '1': '🔄 Переход',
            '2': '⚠️ Ошибка',
            '3': '✅ Включен и работает',
        }
        return status_map.get(str(status_code), f'❓ Неизвестно ({status_code})')

    def _parse_charger_state(self, state_code: str) -> str:
        """Парсит состояние зарядного устройства"""
        state_map = {
            '0': '❌ Отключено',
            '1': '🔌 Подключено (ожидание)',
            '2': '⚡ Предзарядка',
            '3': '🔋 Основная зарядка',
            '4': '🔄 Уравнивание',
            '5': '✅ Завершено',
            '15': '⚙️ Готово',
        }
        return state_map.get(str(state_code), f'⏳ Состояние {state_code}')

    def __init__(self, raw_data: Dict[str, Any]):
        """Инициализация парсера"""
        self.data = raw_data

    # ==================== БАЗОВАЯ ИНФОРМАЦИЯ ====================

    def get_vin(self) -> str:
        """Получает VIN номер автомобиля"""
        return self.data.get('configuration', {}).get('vin', 'N/A')

    def get_engine_status(self) -> str:
        """Получает статус двигателя"""
        status = self.data.get('basicVehicleStatus', {}).get('engineStatus', 'unknown')
        return '✅ Работает' if status == 'engine_running' else '❌ Выключен'

    def get_last_update_time(self) -> str:
        """Получает время последнего обновления"""
        timestamp = int(self.data.get('updateTime', 0))
        if timestamp:
            dt = datetime.fromtimestamp(timestamp / 1000)
            return dt.strftime('%Y-%m-%d %H:%M:%S')
        return 'N/A'

    def get_propulsion_type(self) -> str:
        """Получает тип пропульсии (электро, гибрид и т.д.)"""
        propulsion_map = {
            '0': 'Бензин',
            '1': 'Дизель',
            '2': 'Гибрид',
            '3': 'Plug-in гибрид',
            '4': 'Электро',
        }
        prop_type = self.data.get('configuration', {}).get('propulsionType', '0')
        return propulsion_map.get(str(prop_type), 'Неизвестно')

    def get_is_moving(self) -> bool:
        """Определяет едет ли автомобиль прямо сейчас"""
        basic = self.data.get('basicVehicleStatus', {})
        speed = float(basic.get('speed', 0))
        speed_valid = basic.get('speedValidity', 'false') == 'true'
        return speed > 0 and speed_valid

    def get_theft_and_security_status(self) -> Dict[str, Any]:
        """Получает информацию об охране и защите от кражи"""
        theft = self.data.get('theftNotification', {})
        eg = self.data.get('eg', {}).get('blocked', {})

        activated = int(theft.get('activated', 0))

        status_map = {
            0: '❌ Отключена',
            1: '⚠️ Активируется',
            2: '🔒 Включена (ожидание)',
            3: '🔒 АКТИВНА И РАБОТАЕТ 🚨',
        }

        return {
            'theft_protection': status_map.get(activated, 'Неизвестно'),
            'theft_activated': activated == 3,
            'engine_locked': bool(int(eg.get('status', 0))),
            'activation_time': int(theft.get('time', 0)),
        }

    # ==================== БАТАРЕЯ И ЗАРЯД ====================

    def get_battery_info(self) -> Dict[str, Any]:
        """Получает информацию о батерее"""
        ev_status = self.data.get('additionalVehicleStatus', {}).get('electricVehicleStatus', {})
        main_battery = self.data.get('additionalVehicleStatus', {}).get('maintenanceStatus', {}).get(
            'mainBatteryStatus', {})

        return {
            # 🎯 ОСНОВНАЯ БАТАРЕЯ (%)
            'battery_percentage': int(float(ev_status.get('chargeLevel', 0))),
            'distance_to_empty': int(float(ev_status.get('distanceToEmptyOnBatteryOnly', 0))),
            'charge_status': self._parse_charge_status(ev_status.get('chargeSts', '0')),
            'avg_power_consumption': float(ev_status.get('averPowerConsumption', 0)),
            'time_to_fully_charged': int(float(ev_status.get('timeToFullyCharged', 0))),

            # 🎯 12V БАТАРЕЯ (вспомогательная)
            'aux_battery_percentage': float(main_battery.get('chargeLevel', 0)),
            'aux_battery_voltage': float(main_battery.get('voltage', 0)),

            # Неизвестные параметры
            'soc': float(ev_status.get('stateOfCharge', 0)),
            'soh': float(ev_status.get('stateOfHealth', 0)),

            # Температура батареи
            'hv_temp_level': self._parse_hv_temp_level(ev_status.get('hvTempLevel', '0')),
            'hv_temp_level_numeric': int(ev_status.get('hvTempLevel', 0)),
        }

    def _parse_hv_temp_level(self, level_code: str) -> str:
        """Переводит уровень температуры батареи"""
        temp_map = {
            '0': 'Неизвестно',
            '1': 'Теплая 🔥',
            '2': 'Немного холодная ❄️',
            '3': 'Холодная 🥶',
            '4': 'Сильно холодная 🧊',
        }
        return temp_map.get(str(level_code), 'Неизвестно')

    def _parse_charge_status(self, status_code: str) -> str:
        """Переводит код статуса заряда на русский"""
        status_map = {
            '0': 'Не подключено',
            '1': 'Подключено (ожидание)',
            '2': 'Предзарядка',
            '3': 'Зарядка завершена',
            '4': 'Зарядка завершена',
            '5': 'Приостановлено',
        }
        return status_map.get(str(status_code), 'Неизвестно')

    # ==================== ТЕМПЕРАТУРА ====================

    def get_temperature_info(self) -> Dict[str, Any]:
        """Получает информацию о температуре"""
        climate = self.data.get('additionalVehicleStatus', {}).get('climateStatus', {})

        return {
            'interior_temp': float(climate.get('interiorTemp', 0)),
            'exterior_temp': float(climate.get('exteriorTemp', 0)),
            'cabin_temp_reduction_status': bool(climate.get('cabinTempReductionStatus', 0)),
            'climate_over_heat_proactive': bool(climate.get('climateOverHeatProActive', 'false') == 'true'),
        }

    # ==================== ПОЛОЖЕНИЕ И КООРДИНАТЫ ====================

    def get_position_info(self) -> Dict[str, Any]:
        """Получает информацию о положении автомобиля"""
        position = self.data.get('basicVehicleStatus', {}).get('position', {})

        latitude_raw = position.get('latitude', '')
        longitude_raw = position.get('longitude', '')

        if latitude_raw and longitude_raw:
            latitude = int(latitude_raw) / 1e7
            longitude = int(longitude_raw) / 1e7
        else:
            latitude = 0.0
            longitude = 0.0

        return {
            'latitude': latitude,
            'longitude': longitude,
            'altitude': int(position.get('altitude', 0)) if position.get('altitude') else 0,
            'direction': int(position.get('direction', 0)) if position.get('direction') else 0,
            'can_be_trusted': bool(position.get('posCanBeTrusted', 'false') == 'true'),
        }

    def get_gps_status(self) -> Dict[str, Any]:
        """Получает статус GPS"""
        position = self.data.get('basicVehicleStatus', {}).get('position', {})

        has_gps = bool(position.get('latitude') and position.get('longitude'))

        return {
            'has_gps_signal': has_gps,
            'gps_status': '✅ GPS активен' if has_gps else '❌ GPS потерян',
            'coordinates_trusted': position.get('posCanBeTrusted') == 'true',
            'location_upload_enabled': position.get('carLocatorStatUploadEn') == 'true',
            'latitude': float(position.get('latitude', 0)) / 1e7 if position.get('latitude') else None,
            'longitude': float(position.get('longitude', 0)) / 1e7 if position.get('longitude') else None,
            'altitude': int(position.get('altitude', 0)) if position.get('altitude') else None,
        }

    # ==================== ДВЕРИ И БЕЗОПАСНОСТЬ ====================

    def get_security_info(self) -> Dict[str, Any]:
        """Получает информацию о безопасности"""
        safety = self.data.get('additionalVehicleStatus', {}).get('drivingSafetyStatus', {})

        return {
            'driver_door_open': bool(int(safety.get('doorOpenStatusDriver', 0))),
            'passenger_door_open': bool(int(safety.get('doorOpenStatusPassenger', 0))),
            'driver_rear_door_open': bool(int(safety.get('doorOpenStatusDriverRear', 0))),
            'passenger_rear_door_open': bool(int(safety.get('doorOpenStatusPassengerRear', 0))),
            'trunk_open': bool(int(safety.get('trunkOpenStatus', 0))),
            'engine_hood_open': bool(int(safety.get('engineHoodOpenStatus', 0))),
            'central_lock': self._parse_lock_status(safety.get('centralLockingStatus', '0')),
            'driver_lock': self._parse_lock_status(safety.get('doorLockStatusDriver', '0')),
            'passenger_lock': self._parse_lock_status(safety.get('doorLockStatusPassenger', '0')),
            'driver_rear_lock': self._parse_lock_status(safety.get('doorLockStatusDriverRear', '0')),
            'passenger_rear_lock': self._parse_lock_status(safety.get('doorLockStatusPassengerRear', '0')),
            'trunk_lock': self._parse_lock_status(safety.get('trunkLockStatus', '0')),
            'electric_park_brake': self._parse_park_brake(safety.get('electricParkBrakeStatus', '0')),
            'srs_crash_status': bool(int(safety.get('srsCrashStatus', 0))),
            'alarm_status': safety.get('vehicleAlarm', {}).get('alrmSt', '0'),
        }

    def _parse_lock_status(self, status_code: str) -> str:
        """Переводит код статуса замка"""
        status_map = {
            '0': 'Неизвестно',
            '1': 'Заблокировано',
            '2': 'Разблокировано',
        }
        return status_map.get(str(status_code), 'Неизвестно')

    def _parse_park_brake(self, status_code: str) -> str:
        """Переводит статус электронного тормоза парковки"""
        status_map = {
            '0': 'Выключено',
            '1': 'Включено',
            '2': 'Ошибка',
        }
        return status_map.get(str(status_code), 'Неизвестно')

    def get_seatbelt_status(self) -> Dict[str, Any]:
        """Получает статус ремней безопасности (КРИТИЧНО!)"""
        safety = self.data.get('additionalVehicleStatus', {}).get('drivingSafetyStatus', {})

        driver_belted = bool(safety.get('seatBeltStatusDriver', False))
        passenger_belted = bool(safety.get('seatBeltStatusPassenger', False))
        driver_rear_belted = bool(safety.get('seatBeltStatusDriverRear', False))
        passenger_rear_belted = bool(safety.get('seatBeltStatusPassengerRear', False))

        all_belted = driver_belted and passenger_belted and driver_rear_belted and passenger_rear_belted

        return {
            'driver_belted': '✅ Пристегнут' if driver_belted else '❌ НЕ пристегнут',
            'passenger_belted': '✅ Пристегнут' if passenger_belted else '❌ НЕ пристегнут',
            'driver_rear_belted': '✅ Пристегнут' if driver_rear_belted else '❌ НЕ пристегнут',
            'passenger_rear_belted': '✅ Пристегнут' if passenger_rear_belted else '❌ НЕ пристегнут',
            'all_belted': all_belted,
            'safety_alert': '🚨 ОПАСНО: Не пристегнуты!' if not all_belted else '✅ Все в безопасности',
        }

    # ==================== ОКНА ====================

    def get_windows_info(self) -> Dict[str, Any]:
        """Получает информацию об окнах"""
        climate = self.data.get('additionalVehicleStatus', {}).get('climateStatus', {})

        return {
            'driver_window': self._parse_window_status(climate.get('winStatusDriver', '2')),
            'passenger_window': self._parse_window_status(climate.get('winStatusPassenger', '2')),
            'driver_rear_window': self._parse_window_status(climate.get('winStatusDriverRear', '2')),
            'passenger_rear_window': self._parse_window_status(climate.get('winStatusPassengerRear', '2')),
            'window_close_reminder': self._parse_window_reminder(climate.get('winCloseReminder', '0')),
            'defrost': bool(climate.get('defrost', 'false') == 'true'),
        }

    def _parse_window_status(self, status_code: str) -> str:
        """Переводит код статуса окна"""
        status_map = {
            '0': 'Открыто',
            '1': 'Открывается',
            '2': 'Закрыто',
            '3': 'Закрывается',
        }
        return status_map.get(str(status_code), 'Неизвестно')

    def _parse_window_reminder(self, code: str) -> str:
        """Парсит напоминание о закрытии окна"""
        map_reminder = {
            '0': 'Нет напоминания',
            '1': 'Окна приоткрыты',
            '2': 'Окна открыты',
            '3': 'Нужно закрыть окна',
        }
        return map_reminder.get(str(code), 'Неизвестно')

    # ==================== ПАНОРАМНАЯ КРЫША (ПОЛНОСТЬЮ ИСПРАВЛЕНО) ====================

    def get_panoramic_roof_status(self) -> Dict[str, Any]:
        """
        Получает статус панорамной крыши с затемняющей шторкой

        ⭐ ПАНОРАМНАЯ КРЫША ГЕРМЕТИЧНА И НЕ ОТКРЫВАЕТСЯ!
        ⭐ ТОЛЬКО ЗАТЕМНЯЮЩАЯ ШТОРКА МОЖЕТ ОТКРЫВАТЬСЯ/ЗАКРЫВАТЬСЯ

        Шторка контролирует пропускание света:
        - 0% = полностью затемнена (не видно небо)
        - 50% = средний свет
        - 101% = полностью прозрачна (максимум света, видно небо)
        """
        climate = self.data.get('additionalVehicleStatus', {}).get('climateStatus', {})

        # === ПЕРЕДНЯЯ ЗАТЕМНЯЮЩАЯ ШТОРКА ===
        sunroof_open = bool(int(climate.get('sunroofOpenStatus', 0)))  # Шторка открыта ли?
        sunroof_pos = int(climate.get('sunroofPos', 0))  # Позиция 0-101%

        # === ЗАДНЯЯ ЗАТЕМНЯЮЩАЯ ШТОРКА ===
        rear_curtain_open = bool(int(climate.get('curtainOpenStatus', 0)))  # Шторка открыта ли?
        rear_curtain_pos = int(climate.get('curtainPos', 0))  # Позиция 0-101%

        return {
            # === САМА КРЫША (ГЕРМЕТИЧНА!) ===
            'roof_sealed': True,  # ✅ Крыша ВСЕГДА герметична и не протекает!

            # === ПЕРЕДНЯЯ ЗАТЕМНЯЮЩАЯ ШТОРКА ===
            'front_shade_open': sunroof_open,  # Шторка открыта?
            'front_shade_status': self._parse_sunroof_shade(sunroof_open, sunroof_pos),  # Описание
            'front_shade_position': sunroof_pos,  # 0-101% (0=темно, 101=прозрачно)

            # === ЗАДНЯЯ ЗАТЕМНЯЮЩАЯ ШТОРКА ===
            'rear_shade_open': rear_curtain_open,  # Шторка открыта?
            'rear_shade_status': self._parse_sunroof_shade(rear_curtain_open, rear_curtain_pos),  # Описание
            'rear_shade_position': rear_curtain_pos,  # 0-101% (0=темно, 101=прозрачно)

            # === ОСВЕЩЕНИЕ В САЛОНЕ ===
            'is_transparent': (sunroof_pos > 50 or rear_curtain_pos > 50),  # Много света?
            'is_darkened': (sunroof_pos <= 50 and rear_curtain_pos <= 50),  # Темно?

            'description': self._get_roof_description(sunroof_open, sunroof_pos, rear_curtain_open, rear_curtain_pos),
        }

    def _parse_sunroof_shade(self, is_open: bool, position: int) -> str:
        """
        Парсит статус затемняющей шторки панорамной крыши

        Args:
            is_open: Шторка открыта ли?
            position: Позиция шторки 0-101%

        Returns:
            Текстовое описание состояния
        """
        if position >= 100:
            return '☀️ ПОЛНОСТЬЮ ПРОЗРАЧНА (максимум света, видно небо)'
        elif position >= 75:
            return '🌞 Прозрачна на 75% (много света)'
        elif position >= 50:
            return '🌤️ Прозрачна на 50% (средний свет)'
        elif position >= 25:
            return '🌥️ Прозрачна на 25% (немного света)'
        elif position > 0:
            return '⚫ Закрывается (слабый свет)'
        else:
            return '🌙 ПОЛНОСТЬЮ ЗАТЕМНЕНА (не видно небо)'

    def _get_roof_description(self, front_open: bool, front_pos: int, rear_open: bool, rear_pos: int) -> str:
        """
        Возвращает описание состояния панорамной крыши

        Args:
            front_open: Передняя шторка открыта?
            front_pos: Позиция передней шторки
            rear_open: Задняя шторка открыта?
            rear_pos: Позиция задней шторки

        Returns:
            Полное описание
        """
        front_status = self._parse_sunroof_shade(front_open, front_pos)
        rear_status = self._parse_sunroof_shade(rear_open, rear_pos)

        return f"Передняя: {front_status} | Задняя: {rear_status}"

    # ==================== КЛИМАТ ====================

    def get_climate_info(self) -> Dict[str, Any]:
        """Получает информацию о климате"""
        climate = self.data.get('additionalVehicleStatus', {}).get('climateStatus', {})

        return {
            'interior_temp': float(climate.get('interiorTemp', 0)),
            'exterior_temp': float(climate.get('exteriorTemp', 0)),
            'steering_wheel_heating': self._parse_heating_status(climate.get('steerWhlHeatingSts', '0')),
            'driver_heating': self._parse_heating_status(climate.get('drvHeatSts', '0')),
            'passenger_heating': self._parse_heating_status(climate.get('passHeatingSts', '0')),

            # === ПАНОРАМНАЯ КРЫША И ЗАТЕМНЯЮЩИЕ ШТОРКИ ===
            'panoramic_roof_sealed': True,  # Крыша герметична
            'front_shade_open': bool(int(climate.get('sunroofOpenStatus', 0))),
            'front_shade_position': int(climate.get('sunroofPos', 0)),
            'rear_shade_open': bool(int(climate.get('curtainOpenStatus', 0))),  # ← ИСПРАВЛЕНО!
            'rear_shade_position': int(climate.get('curtainPos', 0)),  # ← ИСПРАВЛЕНО!

            # === ВЕНТИЛЯЦИЯ ===
            'air_blower_active': climate.get('airBlowerActive', 'false') == 'true',
            'defrost': climate.get('defrost', 'false') == 'true',
        }

    def _parse_heating_status(self, status_code: str) -> str:
        """Парсит статус обогрева"""
        status_map = {
            '0': 'Выключено',
            '1': 'Уровень 1',
            '2': 'Уровень 2',
            '3': 'Уровень 3',
        }
        return status_map.get(str(status_code), 'Неизвестно')

    # ==================== ШИНЫ ====================

    def get_tires_info(self) -> Dict[str, Any]:
        """Получает информацию о давлении в шинах"""
        maintenance = self.data.get('additionalVehicleStatus', {}).get('maintenanceStatus', {})

        return {
            'driver_tire': float(maintenance.get('tyreStatusDriver', 0)),
            'passenger_tire': float(maintenance.get('tyreStatusPassenger', 0)),
            'driver_rear_tire': float(maintenance.get('tyreStatusDriverRear', 0)),
            'passenger_rear_tire': float(maintenance.get('tyreStatusPassengerRear', 0)),
            'driver_temp': float(maintenance.get('tyreTempDriver', 0)),
            'passenger_temp': float(maintenance.get('tyreTempPassenger', 0)),
            'driver_rear_temp': float(maintenance.get('tyreTempDriverRear', 0)),
            'passenger_rear_temp': float(maintenance.get('tyreTempPassengerRear', 0)),
        }

    # ==================== ОДОМЕТР И ТО ====================

    def get_maintenance_info(self) -> Dict[str, Any]:
        """Получает информацию о техническом обслуживании"""
        maintenance = self.data.get('additionalVehicleStatus', {}).get('maintenanceStatus', {})

        return {
            'odometer': float(maintenance.get('odometer', 0)),
            'days_to_service': int(maintenance.get('daysToService', 0)),
            'distance_to_service': int(maintenance.get('distanceToService', 0)),
            'engine_hours_to_service': int(maintenance.get('engineHrsToService', 0)),
            'service_warning_status': bool(int(maintenance.get('serviceWarningStatus', 0))),
            'brake_fluid_level': self._parse_fluid_level(maintenance.get('brakeFluidLevelStatus', '0')),
            'washer_fluid_level': self._parse_washer_fluid_level(maintenance.get('washerFluidLevelStatus', '0')),
            'engine_coolant_level': self._parse_fluid_level(maintenance.get('engineCoolantLevelStatus', '0')),
        }

    def _parse_fluid_level(self, level_code: str) -> str:
        """
        Парсит уровень жидкостей (тормоз, охлаждающая)
        """
        level_map = {
            '0': 'Полный 🟢',
            '1': 'Хороший 🟢',
            '2': 'Нормально 🟢',
            '3': 'Полный 🟢',
        }
        return level_map.get(str(level_code), f'Уровень {level_code}')

    def _parse_washer_fluid_level(self, level_code: str) -> str:
        """
        Парсит уровень жидкости омывателя
        (может быть инверсная логика у Zeekr)
        """
        level_map = {
            '0': 'Полный ✅ 💧',
            '1': 'Хороший 🟢 💧',
            '2': 'Нижний 🟡 💧',
            '3': 'Критичный 🔴 💧',
        }
        return level_map.get(str(level_code), f'Уровень {level_code}')

    # ==================== СКОРОСТЬ И ДВИЖЕНИЕ ====================

    def get_movement_info(self) -> Dict[str, Any]:
        """Получает информацию о движении"""
        basic = self.data.get('basicVehicleStatus', {})
        running = self.data.get('additionalVehicleStatus', {}).get('runningStatus', {})
        driving = self.data.get('additionalVehicleStatus', {}).get('drivingBehaviourStatus', {})

        return {
            # ===== СКОРОСТЬ =====
            'speed': float(basic.get('speed', 0)),
            'speed_valid': self._parse_speed_validity(basic.get('speedValidity', 'false')),
            'avg_speed': int(float(running.get('avgSpeed', 0))),
            'speed_numeric': float(basic.get('speed', 0)),

            # ===== КОРОБКА ПЕРЕДАЧ =====
            'gear_auto': self._parse_gear_status(str(int(driving.get('gearAutoStatus', 0)))),
            'gear_auto_numeric': int(driving.get('gearAutoStatus', 0)),
            'engine_rpm': float(driving.get('engineSpeed', 0)),

            # ===== ДВИГАТЕЛЬ =====
            'engine_status': 'engine_running' if basic.get('engineStatus') == 'engine_running' else 'engine_off',

            # ===== НАПРАВЛЕНИЕ =====
            'direction': int(basic.get('direction', 0)) if basic.get('direction') else 0,

            # ===== ОДОМЕТРЫ =====
            'trip_meter_1': float(running.get('tripMeter1', 0)),
            'trip_meter_2': float(running.get('tripMeter2', 0)),

            # ===== ОГНИ =====
            'drl_active': bool(int(running.get('drl', 0))),
            'hi_beam_active': bool(int(running.get('hiBeam', 0))),
            'lo_beam_active': bool(int(running.get('loBeam', 0))),
        }

    def _parse_speed_validity(self, validity: str) -> str:
        """Парсит достоверность скорости"""
        return '✅ Достоверна' if validity == 'true' else '⚠️ Недостоверна'

    def _parse_gear_status(self, gear_code: str) -> str:
        """Парсит статус коробки передач"""
        gear_map = {
            '0': '❌ Выключена',
            '1': '✅ Автоматическая включена',
            '2': '🔧 Мануальная включена',
            '3': '⏸️ Режим удержания / Нейтраль',
        }
        return gear_map.get(str(gear_code), 'Неизвестно')

    # ==================== ТОРМОЗА ====================

    def get_brake_status(self) -> Dict[str, Any]:
        """Получает информацию о тормозах"""
        running = self.data.get('additionalVehicleStatus', {}).get('runningStatus', {})

        stop_lights = bool(int(running.get('stopLi', 0)))

        return {
            'is_braking': stop_lights,
            'brake_status': self._parse_stop_light_status(running.get('stopLi', '0')),
            'stop_lights_on': stop_lights,
        }

    def _parse_stop_light_status(self, status: str) -> str:
        """Парсит статус стоп-сигналов"""
        status_map = {
            '0': '✅ Выключены (едет или свободно)',
            '1': '🔴 ВКЛЮЧЕНЫ - ТОРМОЗИТ',
        }
        return status_map.get(str(status), 'Неизвестно')

    # ==================== ОГНИ ====================

    def get_lights_status(self) -> Dict[str, Any]:
        """Получает полный статус всех огней"""
        running = self.data.get('additionalVehicleStatus', {}).get('runningStatus', {})

        return {
            'drl_active': bool(int(running.get('drl', 0))),
            'hi_beam': bool(int(running.get('hiBeam', 0))),
            'lo_beam': bool(int(running.get('loBeam', 0))),
            'front_fog': bool(int(running.get('frntFog', 0))),
            'rear_fog': bool(int(running.get('reFog', 0))),
            'stop_lights': bool(int(running.get('stopLi', 0))),
            'reverse_lights': bool(int(running.get('reverseLi', 0))),
            'corner_lights': bool(int(running.get('cornrgLi', 0))),

            'lights_status': self._get_lights_summary(running),
            'is_night_mode': not bool(int(running.get('drl', 0))) and not bool(int(running.get('hiBeam', 0))),
        }

    def _get_lights_summary(self, running: Dict) -> str:
        """Возвращает текстовое описание огней"""
        drl = bool(int(running.get('drl', 0)))
        lo_beam = bool(int(running.get('loBeam', 0)))
        hi_beam = bool(int(running.get('hiBeam', 0)))
        stop = bool(int(running.get('stopLi', 0)))

        if stop:
            return '🔴 ТОРМОЗИТ'
        elif hi_beam:
            return '🔆 Дальний свет'
        elif lo_beam:
            return '💡 Ближний свет'
        elif drl:
            return '☀️ Дневные огни'
        else:
            return '⚫ Огни выключены (день или припаркован)'

    # ==================== ЗАГРЯЗНЕНИЕ ====================

    def get_pollution_info(self) -> Dict[str, Any]:
        """Получает информацию о качестве воздуха"""
        pollution = self.data.get('additionalVehicleStatus', {}).get('pollutionStatus', {})

        return {
            'interior_pm25': int(float(pollution.get('interiorPM25', 0))),
            'interior_pm25_level': self._parse_pm25_level(pollution.get('interiorPM25Level', '0')),
            'exterior_pm25_level': self._parse_pm25_level(pollution.get('exteriorPM25Level', '0')),
            'relative_humidity': int(float(pollution.get('relHumSts', 0))),
        }

    def _parse_pm25_level(self, level_code: str) -> str:
        """Переводит уровень PM2.5"""
        level_map = {
            '0': 'Отличный 🟢',
            '1': 'Хороший 🟢',
            '2': 'Умеренный 🟡',
            '3': 'Плохой 🟠',
            '4': 'Очень плохой 🔴',
            '5': 'Критичный 🚨',
        }
        return level_map.get(str(level_code), 'Неизвестно')

    def get_air_quality_alert(self) -> Dict[str, Any]:
        """Проверяет качество воздуха (ВНИМАНИЕ!)"""
        pollution = self.data.get('additionalVehicleStatus', {}).get('pollutionStatus', {})

        interior_pm25 = int(pollution.get('interiorPM25', 0))
        interior_level = int(pollution.get('interiorPM25Level', 0))
        humidity = int(pollution.get('relHumSts', 0))

        alerts = []

        if interior_pm25 > 300:
            alerts.append(f"🚨 КРИТИЧНОЕ: PM2.5 = {interior_pm25} мкг/м³ (норма < 35)")
        elif interior_pm25 > 100:
            alerts.append(f"⚠️ ОЧЕНЬ ПЛОХО: PM2.5 = {interior_pm25} мкг/м³")

        if interior_level == 5:
            alerts.append("🔴 Уровень загрязнения: ОЧЕНЬ ПЛОХО")

        if humidity > 100:
            alerts.append(f"⚠️ Ошибка датчика влажности: {humidity}% (невозможно!)")

        return {
            'alerts': alerts,
            'interior_pm25': interior_pm25,
            'interior_level': interior_level,
            'humidity': humidity,
            'has_alerts': len(alerts) > 0,
        }

    # ==================== ВРЕМЯ ПАРКОВКИ ====================

    def get_park_info(self) -> Dict[str, Any]:
        """Получает информацию о парковке"""
        # ✅ НОВАЯ ЗАЩИТА ОТ ПУСТЫХ СТРОК
        park_time_str = self.data.get('parkTime', {}).get('status', '')

        if not park_time_str or park_time_str == '':
            return {
                'is_parked': False,
                'parked_since': None,
                'park_duration': 'Не припаркован',
                'total_seconds': 0,
            }
        try:
            park_time_ms = int(park_time_str)
        except (ValueError, TypeError):
            # Если преобразование не удалось, возвращаем "не припаркован"
            return {
                'is_parked': False,
                'parked_since': None,
                'park_duration': 'Не припаркован',
                'total_seconds': 0,
            }

        if park_time_ms == 0:
            return {
                'is_parked': False,
                'parked_since': None,
                'park_duration': 'Не припаркован',
                'total_seconds': 0,
            }

        park_datetime = datetime.fromtimestamp(park_time_ms / 1000)
        current_time = datetime.now()
        park_duration = current_time - park_datetime

        total_seconds = int(park_duration.total_seconds())
        days = total_seconds // 86400
        hours = (total_seconds % 86400) // 3600
        minutes = (total_seconds % 3600) // 60

        if days > 0:
            duration_str = f"{days}д {hours}ч {minutes}м"
        elif hours > 0:
            duration_str = f"{hours}ч {minutes}м"
        else:
            duration_str = f"{minutes}м"

        return {
            'is_parked': True,
            'parked_since': park_datetime.strftime('%Y-%m-%d %H:%M:%S'),
            'park_duration': duration_str,
            'total_seconds': total_seconds,
        }

    # ==================== ЗАРЯДКА ====================

    def get_charging_info(self) -> Dict[str, Any]:
        """Получает информацию о зарядке (AC и DC)"""
        ev_status = self.data.get('additionalVehicleStatus', {}).get('electricVehicleStatus', {})

        return {
            # ===== AC ЗАРЯДКА =====
            'charge_status': self._parse_charge_status(ev_status.get('chargeSts', '0')),
            'charge_pile_voltage': float(ev_status.get('dcChargePileUAct', 0)),
            'current_power_input': float(ev_status.get('averPowerConsumption', 0)),
            'ac_charge_status': self._parse_charge_status(ev_status.get('chargeSts', '0')),

            # ===== DC ЗАРЯДКА (БЫСТРАЯ) =====
            'dc_charge_status': self._parse_dc_charge_status(ev_status.get('dcChargeSts', '0')),
            'dc_charge_pile_current': float(ev_status.get('dcChargePileIAct', 0)),
            'dc_charge_pile_voltage': float(ev_status.get('dcChargePileUAct', 0)),
            'dc_power': self._calculate_dc_power(
                float(ev_status.get('dcChargePileUAct', 0)),
                float(ev_status.get('dcChargePileIAct', 0))
            ),
            'dc_dc_activated': bool(int(ev_status.get('dcDcActvd', 0))),
            'dc_dc_connect_status': self._parse_dc_dc_status(ev_status.get('dcDcConnectStatus', '0')),

            # ===== РАЗРЯДКА (V2L, V2H) =====
            'discharge_voltage': float(ev_status.get('disChargeUAct', 0)),
            'discharge_current': float(ev_status.get('disChargeIAct', 0)),
            'discharge_power': self._calculate_discharge_power(
                float(ev_status.get('disChargeUAct', 0)),
                float(ev_status.get('disChargeIAct', 0))
            ),
            'discharge_connector_status': self._parse_charge_connector_status(
                ev_status.get('disChargeConnectStatus', '0')),

            # ===== ОБЩАЯ ИНФОРМАЦИЯ =====
            'charger_state': self._parse_charger_state(ev_status.get('chargerState', '0')),
            'time_to_fully_charged': int(float(ev_status.get('timeToFullyCharged', 0))),
        }

    def _parse_charge_connector_status(self, status_code: str) -> str:
        """Парсит статус разъема зарядки"""
        status_map = {
            '0': 'Не подключен',
            '1': 'Подключен',
            '2': 'Ошибка',
        }
        return status_map.get(str(status_code), 'Неизвестно')

    def estimate_battery_recovery(self) -> Dict[str, Any]:
        """
        Оценивает восстановление батареи через рекуперативное торможение
        """
        running = self.data.get('additionalVehicleStatus', {}).get('runningStatus', {})
        basic = self.data.get('basicVehicleStatus', {})
        ev_status = self.data.get('additionalVehicleStatus', {}).get('electricVehicleStatus', {})

        is_braking = bool(int(running.get('stopLi', 0)))
        speed = float(basic.get('speed', 0))
        charge_level = int(ev_status.get('chargeLevel', 0))

        return {
            'is_braking': is_braking,
            'speed': speed,
            'current_charge': charge_level,
            'is_recovering': is_braking and speed > 0,
            'recovery_status': '⚡ ВОССТАНОВЛЕНИЕ ЭНЕРГИИ' if (is_braking and speed > 0) else 'Нет восстановления',
        }

    # ==================== ПОЛНЫЙ ОТЧЕТ ====================

    def get_full_summary(self) -> str:
        """Возвращает полный красиво отформатированный отчет"""

        battery = self.get_battery_info()
        temp = self.get_temperature_info()
        position = self.get_position_info()
        security = self.get_security_info()
        windows = self.get_windows_info()
        tires = self.get_tires_info()
        maintenance = self.get_maintenance_info()
        movement = self.get_movement_info()
        pollution = self.get_pollution_info()
        park = self.get_park_info()
        lights = self.get_lights_status()
        climate = self.get_climate_info()
        charging = self.get_charging_info()
        roof = self.get_panoramic_roof_status()
        belts = self.get_seatbelt_status()
        theft = self.get_theft_and_security_status()

        report = f"""
{'=' * 80}
🚗 ПОЛНЫЙ ОТЧЕТ О СОСТОЯНИИ АВТОМОБИЛЯ
{'=' * 80}

📊 ОСНОВНАЯ ИНФОРМАЦИЯ
{'-' * 80}
VIN:                    {self.get_vin()}
Тип пропульсии:         {self.get_propulsion_type()}
Статус двигателя:       {self.get_engine_status()}
Последнее обновление:   {self.get_last_update_time()}

🔒 ОХРАНА И БЕЗОПАСНОСТЬ
{'-' * 80}
Охрана:                 {theft['theft_protection']}
Двигатель заблокирован: {'✅ ДА' if theft['engine_locked'] else '❌ НЕТ'}

🔋 БАТАРЕЯ И ЗАРЯД
{'-' * 80}
Уровень заряда:         {battery['battery_percentage']}%
Статус зарядки:         {battery['charge_status']}
Запас хода:             {battery['distance_to_empty']} км
Среднее потребление:    {battery['avg_power_consumption']} кВт
Напряжение 12V:         {battery['aux_battery_voltage']:.2f}V
Температура батареи:   {battery['hv_temp_level']}

☀️ ПАНОРАМНАЯ КРЫША И ЗАТЕМНЯЮЩИЕ ШТОРКИ
{'-' * 80}
Состояние крыши:        {roof['description']}
Крыша герметична:       {'✅ ДА' if roof['roof_sealed'] else '❌ НЕТ'}
Передняя шторка:        {roof['front_shade_status']}
  └─ Позиция:           {roof['front_shade_position']}%
Задняя шторка:          {roof['rear_shade_status']}
  └─ Позиция:           {roof['rear_shade_position']}%
Освещение в салоне:     {'☀️ МНОГО света' if roof['is_transparent'] else '🌙 ЗАТЕМНЕНО'}

🌡️ ТЕМПЕРАТУРА И КЛИМАТ
{'-' * 80}
Внутренняя температура: {temp['interior_temp']}°C
Внешняя температура:    {temp['exterior_temp']}°C
Отопление руля:         {climate['steering_wheel_heating']}
Отопление водителя:     {climate['driver_heating']}
Отопление пассажира:    {climate['passenger_heating']}
Дефрост:                {'Включен ✅' if climate['defrost'] else 'Выключен ❌'}

📍 ПОЛОЖЕНИЕ
{'-' * 80}
GPS:                    {self.get_gps_status()['gps_status']}
Широта:                 {position['latitude']:.6f}
Долгота:                {position['longitude']:.6f}
Высота:                 {position['altitude']} м

🔒 БЕЗОПАСНОСТЬ И РЕМНИ
{'-' * 80}
{belts['safety_alert']}
Водитель:               {belts['driver_belted']}
Пассажир:               {belts['passenger_belted']}
Задний левый:           {belts['driver_rear_belted']}
Задний правый:          {belts['passenger_rear_belted']}

🔓 ДВЕРИ И ОКНА
{'-' * 80}
Дверь водителя:         {'🔓 Открыта' if security['driver_door_open'] else '🔐 Закрыта'}
Дверь пассажира:        {'🔓 Открыта' if security['passenger_door_open'] else '🔐 Закрыта'}
Окно водителя:          {windows['driver_window']}
Окно пассажира:         {windows['passenger_window']}
Багажник:               {'🔓 Открыт' if security['trunk_open'] else '🔐 Закрыт'}
Капот:                  {'🔓 Открыт' if security['engine_hood_open'] else '🔐 Закрыт'}

🛞 ШИНЫ (Давление в кПа / Температура в °C)
{'-' * 80}
Передняя левая:         {tires['driver_tire']:.1f} кПа / {tires['driver_temp']:.1f}°C
Передняя правая:        {tires['passenger_tire']:.1f} кПа / {tires['passenger_temp']:.1f}°C
Задняя левая:           {tires['driver_rear_tire']:.1f} кПа / {tires['driver_rear_temp']:.1f}°C
Задняя правая:          {tires['passenger_rear_tire']:.1f} кПа / {tires['passenger_rear_temp']:.1f}°C

🔧 ТЕХНИЧЕСКОЕ ОБСЛУЖИВАНИЕ
{'-' * 80}
Одометр:                {maintenance['odometer']:.0f} км
Дней до ТО:             {maintenance['days_to_service']} дней
Км до ТО:               {maintenance['distance_to_service']} км
Тормозная жидкость:     {maintenance['brake_fluid_level']}
Омыватель:              {maintenance['washer_fluid_level']}
Охлаждающая жидкость:   {maintenance['engine_coolant_level']}

🚙 ДВИЖЕНИЕ
{'-' * 80}
Текущая скорость:       {movement['speed']:.1f} км/ч
Средняя скорость:       {movement['avg_speed']} км/ч
Коробка передач:        {movement['gear_auto']}
Направление:            {movement['direction']}°

💡 ОГНИ
{'-' * 80}
Статус:                 {lights['lights_status']}
Дневные огни:           {'✅' if lights['drl_active'] else '❌'}
Дальний свет:           {'✅' if lights['hi_beam'] else '❌'}
Ближний свет:           {'✅' if lights['lo_beam'] else '❌'}
Стоп-сигналы:           {'🔴 Включены' if lights['stop_lights'] else '✅ Выключены'}

💨 КАЧЕСТВО ВОЗДУХА
{'-' * 80}
PM2.5 внутри:           {pollution['interior_pm25']} мкг/м³ ({pollution['interior_pm25_level']})
Влажность:              {pollution['relative_humidity']}%

🅿️ ПАРКОВКА
{'-' * 80}
Припаркован:            {'Да ✅' if park['is_parked'] else 'Нет ❌'}
Время парковки:         {park['park_duration']}

{'=' * 80}
"""
        return report
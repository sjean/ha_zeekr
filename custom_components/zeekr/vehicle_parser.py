# custom_components/zeekr/vehicle_parser.py

"""
Vehicle data parser - extract and format information
更新：修正全景天幕遮阳帘状态解析
"""
from typing import Dict, Any, Optional
from datetime import datetime


class VehicleDataParser:
    """Parser for extracting all vehicle status information"""

    def _calculate_dc_power(self, voltage: float, current: float) -> float:
        """
        Calculate DC charging power
        Formula: Power (kW) = Voltage (V) × Current (A) / 1000
        """
        if voltage and current:
            power_kw = (voltage * abs(current)) / 1000
            return round(power_kw, 1)
        return 0.0

    def _calculate_discharge_power(self, voltage: float, current: float) -> float:
        """Calculate discharge power (V2L, V2H)"""
        if voltage and current:
            power_kw = (voltage * abs(current)) / 1000
            return round(power_kw, 1)
        return 0.0

    def _parse_dc_charge_status(self, status_code: str) -> str:
        """Parse the DC charging status"""
        status_map = {
            '0': '❌ 未激活',
            '1': '⚡ 已激活（已连接）',
            '2': '🔋 充电中',
            '3': '✅ 充电完成',
            '4': '⏸️ 已暂停',
        }
        return status_map.get(str(status_code), f'❓ 未知（{status_code}）')

    def _parse_dc_dc_status(self, status_code: str) -> str:
        """Parse the DC/DC converter status (400V to 12V)."""
        status_map = {
            '0': '❌ 已关闭',
            '1': '🔄 切换中',
            '2': '⚠️ 故障',
            '3': '✅ 已启用并运行',
        }
        return status_map.get(str(status_code), f'❓ 未知（{status_code}）')

    def _parse_charger_state(self, state_code: str) -> str:
        """Parse the charger state"""
        state_map = {
            '0': '❌ 未连接',
            '1': '🔌 已连接（等待中）',
            '2': '⚡ 预充中',
            '3': '🔋 主充电中',
            '4': '🔄 均衡中',
            '5': '✅ 已完成',
            '15': '⚙️ 就绪',
        }
        return state_map.get(str(state_code), f'⏳ 状态 {state_code}')

    def __init__(self, raw_data: Dict[str, Any]):
        """Initialize the parser"""
        self.data = raw_data

    # ==================== BASIC INFORMATION ====================

    def get_vin(self) -> str:
        """Get the vehicle VIN"""
        return self.data.get('configuration', {}).get('vin', 'N/A')

    def get_engine_status(self) -> str:
        """Get the engine status"""
        status = self.data.get('basicVehicleStatus', {}).get('engineStatus', 'unknown')
        return '✅ 运行中' if status == 'engine_running' else '❌ 已关闭'

    def get_last_update_time(self) -> str:
        """Get the last update time"""
        timestamp = int(self.data.get('updateTime', 0))
        if timestamp:
            dt = datetime.fromtimestamp(timestamp / 1000)
            return dt.strftime('%Y-%m-%d %H:%M:%S')
        return 'N/A'

    def get_propulsion_type(self) -> str:
        """Get the propulsion type (electric, hybrid, etc.)"""
        propulsion_map = {
            '0': '汽油',
            '1': '柴油',
            '2': '混动',
            '3': '插电混动',
            '4': '纯电',
        }
        prop_type = self.data.get('configuration', {}).get('propulsionType', '0')
        return propulsion_map.get(str(prop_type), '未知')

    def get_is_moving(self) -> bool:
        """Determine whether the vehicle is currently moving"""
        basic = self.data.get('basicVehicleStatus', {})
        speed = float(basic.get('speed', 0))
        speed_valid = basic.get('speedValidity', 'false') == 'true'
        return speed > 0 and speed_valid

    def get_theft_and_security_status(self) -> Dict[str, Any]:
        """Get theft-protection and security information"""
        theft = self.data.get('theftNotification', {})
        eg = self.data.get('eg', {}).get('blocked', {})

        activated = int(theft.get('activated', 0))

        status_map = {
            0: '❌ 已禁用',
            1: '⚠️ 启动中',
            2: '🔒 已启用（等待中）',
            3: '🔒 已激活并运行 🚨',
        }

        return {
            'theft_protection': status_map.get(activated, '未知'),
            'theft_activated': activated == 3,
            'engine_locked': bool(int(eg.get('status', 0))),
            'activation_time': int(theft.get('time', 0)),
        }

    # ==================== BATTERY AND CHARGING ====================

    def get_battery_info(self) -> Dict[str, Any]:
        """Get battery information"""
        ev_status = self.data.get('additionalVehicleStatus', {}).get('electricVehicleStatus', {})
        main_battery = self.data.get('additionalVehicleStatus', {}).get('maintenanceStatus', {}).get(
            'mainBatteryStatus', {})

        return {
            # Main battery (%)
            'battery_percentage': int(float(ev_status.get('chargeLevel', 0))),
            'distance_to_empty': int(float(ev_status.get('distanceToEmptyOnBatteryOnly', 0))),
            'charge_status': self._parse_charge_status(ev_status.get('chargeSts', '0')),
            'avg_power_consumption': float(ev_status.get('averPowerConsumption', 0)),
            'time_to_fully_charged': int(float(ev_status.get('timeToFullyCharged', 0))),

            # 12V auxiliary battery
            'aux_battery_percentage': float(main_battery.get('chargeLevel', 0)),
            'aux_battery_voltage': float(main_battery.get('voltage', 0)),

            # Additional metrics
            'soc': float(ev_status.get('stateOfCharge', 0)),
            'soh': float(ev_status.get('stateOfHealth', 0)),

            # Battery temperature
            'hv_temp_level': self._parse_hv_temp_level(ev_status.get('hvTempLevel', '0')),
            'hv_temp_level_numeric': int(ev_status.get('hvTempLevel', 0)),
        }

    def _parse_hv_temp_level(self, level_code: str) -> str:
        """Translate the battery temperature level"""
        temp_map = {
            '0': '温暖 🔥',
            '1': '略冷 ❄️',
            '2': '寒冷 🥶',
            '3': '很冷 🧊',
        }
        return temp_map.get(str(level_code), '未知')

    def _parse_charge_status(self, status_code: str) -> str:
        """Translate the charge status code."""
        status_map = {
            '0': '未连接',
            '1': '已连接（等待中）',
            '2': '预充中',
            '3': '充电完成',
            '4': '充电完成',
            '5': '已暂停',
        }
        return status_map.get(str(status_code), '未知')

    # ==================== TEMPERATURE ====================

    def get_temperature_info(self) -> Dict[str, Any]:
        """Get temperature information"""
        climate = self.data.get('additionalVehicleStatus', {}).get('climateStatus', {})

        return {
            'interior_temp': float(climate.get('interiorTemp', 0)),
            'exterior_temp': float(climate.get('exteriorTemp', 0)),
            'cabin_temp_reduction_status': bool(climate.get('cabinTempReductionStatus', 0)),
            'climate_over_heat_proactive': bool(climate.get('climateOverHeatProActive', 'false') == 'true'),
        }

    # ==================== POSITION AND COORDINATES ====================

    def get_position_info(self) -> Dict[str, Any]:
        """Get vehicle position information"""
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
        """Get GPS status"""
        position = self.data.get('basicVehicleStatus', {}).get('position', {})

        has_gps = bool(position.get('latitude') and position.get('longitude'))

        return {
            'has_gps_signal': has_gps,
            'gps_status': '✅ GPS 正常' if has_gps else '❌ GPS 丢失',
            'coordinates_trusted': position.get('posCanBeTrusted') == 'true',
            'location_upload_enabled': position.get('carLocatorStatUploadEn') == 'true',
            'latitude': float(position.get('latitude', 0)) / 1e7 if position.get('latitude') else None,
            'longitude': float(position.get('longitude', 0)) / 1e7 if position.get('longitude') else None,
            'altitude': int(position.get('altitude', 0)) if position.get('altitude') else None,
        }

    # ==================== DOORS AND SECURITY ====================

    def get_security_info(self) -> Dict[str, Any]:
        """Get safety information"""
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
        """Translate the lock status code"""
        status_map = {
            '0': '未知',
            '1': '已锁定',
            '2': '未锁定',
        }
        return status_map.get(str(status_code), '未知')

    def _parse_park_brake(self, status_code: str) -> str:
        """Translate the electronic parking brake status"""
        status_map = {
            '0': '关闭',
            '1': '开启',
            '2': '故障',
        }
        return status_map.get(str(status_code), '未知')

    # ==================== WINDOWS ====================

    def get_windows_info(self) -> Dict[str, Any]:
        """Get window information"""
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
        """Translate the window status code"""
        status_map = {
            '0': '打开',
            '1': '开启中',
            '2': '关闭',
            '3': '关闭中',
        }
        return status_map.get(str(status_code), '未知')

    def _parse_window_reminder(self, code: str) -> str:
        """Parse the window-close reminder"""
        map_reminder = {
            '0': '无提醒',
            '1': '车窗微开',
            '2': '车窗开启',
            '3': '请关闭车窗',
        }
        return map_reminder.get(str(code), '未知')

    # ==================== PANORAMIC ROOF (FULLY FIXED) ====================

    def get_panoramic_roof_status(self) -> Dict[str, Any]:
        """
        Get the status of the panoramic roof shade.

        ⭐ The panoramic roof is sealed and does not open!
        ⭐ Only the shade can open and close

        The shade controls light transmission:
        - 0% = fully darkened (the sky is not visible)
        - 50% = medium light
        - 101% = fully transparent (maximum light, the sky is visible)
        """
        climate = self.data.get('additionalVehicleStatus', {}).get('climateStatus', {})

        # === FRONT SHADE ===
        sunroof_open = bool(int(climate.get('sunroofOpenStatus', 0)))  # Is the shade open?
        sunroof_pos = int(climate.get('sunroofPos', 0))  # Position 0-101%

        # === REAR SHADE ===
        rear_curtain_open = bool(int(climate.get('curtainOpenStatus', 0)))  # Is the shade open?
        rear_curtain_pos = int(climate.get('curtainPos', 0))  # Position 0-101%

        return {
            # === ROOF PANEL (SEALED) ===
            'roof_sealed': True,  # ✅ The roof panel is always sealed and does not leak!

            # === FRONT SHADE ===
            'front_shade_open': sunroof_open,
            'front_shade_status': self._parse_sunroof_shade(sunroof_open, sunroof_pos),
            'front_shade_position': sunroof_pos,  # 0-101% (0=dark, 101=transparent)

            # === REAR SHADE ===
            'rear_shade_open': rear_curtain_open,
            'rear_shade_status': self._parse_sunroof_shade(rear_curtain_open, rear_curtain_pos),
            'rear_shade_position': rear_curtain_pos,  # 0-101% (0=dark, 101=transparent)

            # === CABIN LIGHTING ===
            'is_transparent': (sunroof_pos > 50 or rear_curtain_pos > 50),  # A lot of light?
            'is_darkened': (sunroof_pos <= 50 and rear_curtain_pos <= 50),  # Dark?

            'description': self._get_roof_description(sunroof_open, sunroof_pos, rear_curtain_open, rear_curtain_pos),
        }

    def _parse_sunroof_shade(self, is_open: bool, position: int) -> str:
        """
        Parse the panoramic roof shade status.

        Args:
            is_open: Whether the shade is open
            position: Shade position 0-101%

        Returns:
            Text description of the state
        """
        if position >= 100:
            return '☀️ 完全透光（采光最强，可见天空）'
        elif position >= 75:
            return '🌞 75% 透光（采光充足）'
        elif position >= 50:
            return '🌤️ 50% 透光（采光中等）'
        elif position >= 25:
            return '🌥️ 25% 透光（少量进光）'
        elif position > 0:
            return '⚫ 关闭中（弱光）'
        else:
            return '🌙 完全遮光（不可见天空）'

    def _get_roof_description(self, front_open: bool, front_pos: int, rear_open: bool, rear_pos: int) -> str:
        """
        Return a description of the panoramic roof state.

        Args:
            front_open: Whether the front shade is open
            front_pos: Front shade position
            rear_open: Whether the rear shade is open
            rear_pos: Rear shade position

        Returns:
            Full description
        """
        front_status = self._parse_sunroof_shade(front_open, front_pos)
        rear_status = self._parse_sunroof_shade(rear_open, rear_pos)

        return f"前部：{front_status} | 后部：{rear_status}"

    # ==================== CLIMATE ====================

    def get_climate_info(self) -> Dict[str, Any]:
        """Get climate information"""
        climate = self.data.get('additionalVehicleStatus', {}).get('climateStatus', {})

        return {
            'interior_temp': float(climate.get('interiorTemp', 0)),
            'exterior_temp': float(climate.get('exteriorTemp', 0)),
            'steering_wheel_heating': self._parse_heating_status(climate.get('steerWhlHeatingSts', '0')),
            'driver_heating': self._parse_heating_status(climate.get('drvHeatSts', '0')),
            'passenger_heating': self._parse_heating_status(climate.get('passHeatingSts', '0')),

            # === PANORAMIC ROOF AND SHADES ===
            'panoramic_roof_sealed': True,  # Roof is sealed
            'front_shade_open': bool(int(climate.get('sunroofOpenStatus', 0))),
            'front_shade_position': int(climate.get('sunroofPos', 0)),
            'rear_shade_open': bool(int(climate.get('curtainOpenStatus', 0))),
            'rear_shade_position': int(climate.get('curtainPos', 0)),

            # === VENTILATION ===
            'air_blower_active': climate.get('airBlowerActive', 'false') == 'true',
            'defrost': climate.get('defrost', 'false') == 'true',
        }

    def _parse_heating_status(self, status_code: str) -> str:
        """Parse the heating status"""
        status_map = {
            '0': '关闭',
            '1': '1 档',
            '2': '2 档',
            '3': '3 档',
        }
        return status_map.get(str(status_code), '未知')

    # ==================== TIRES ====================

    def get_tires_info(self) -> Dict[str, Any]:
        """Get tire pressure information"""
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

    # ==================== ODOMETER AND SERVICE ====================

    def get_maintenance_info(self) -> Dict[str, Any]:
        """Get maintenance information"""
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
        Parse fluid levels (brake, coolant).
        """
        level_map = {
            '0': '满 🟢',
            '1': '良好 🟢',
            '2': '正常 🟢',
            '3': '满 🟢',
        }
        return level_map.get(str(level_code), f'等级 {level_code}')

    def _parse_washer_fluid_level(self, level_code: str) -> str:
        """
        Parse the washer fluid level.
        (Zeekr may use inverted logic)
        """
        level_map = {
            '0': '满 ✅',
            '1': '低 🔴',
        }
        return level_map.get(str(level_code), f'等级 {level_code}')

    # ==================== SPEED AND MOVEMENT ====================

    def get_movement_info(self) -> Dict[str, Any]:
        """Get movement information"""
        basic = self.data.get('basicVehicleStatus', {})
        running = self.data.get('additionalVehicleStatus', {}).get('runningStatus', {})
        driving = self.data.get('additionalVehicleStatus', {}).get('drivingBehaviourStatus', {})

        return {
            # ===== SPEED =====
            'speed': float(basic.get('speed', 0)),
            'speed_valid': self._parse_speed_validity(basic.get('speedValidity', 'false')),
            'avg_speed': int(float(running.get('avgSpeed', 0))),
            'speed_numeric': float(basic.get('speed', 0)),

            # ===== GEARBOX =====
            'gear_auto': self._parse_gear_status(str(int(driving.get('gearAutoStatus', 0)))),
            'gear_auto_numeric': int(driving.get('gearAutoStatus', 0)),
            'engine_rpm': float(driving.get('engineSpeed', 0)),

            # ===== ENGINE =====
            'engine_status': 'engine_running' if basic.get('engineStatus') == 'engine_running' else 'engine_off',

            # ===== DIRECTION =====
            'direction': int(basic.get('direction', 0)) if basic.get('direction') else 0,

            # ===== ODOMETERS =====
            'trip_meter_1': float(running.get('tripMeter1', 0)),
            'trip_meter_2': float(running.get('tripMeter2', 0)),

            # ===== LIGHTS =====
            'drl_active': bool(int(running.get('drl', 0))),
            'hi_beam_active': bool(int(running.get('hiBeam', 0))),
            'lo_beam_active': bool(int(running.get('loBeam', 0))),
        }

    def _parse_speed_validity(self, validity: str) -> str:
        """Parse speed validity"""
        return '✅ 有效' if validity == 'true' else '⚠️ 无效'

    def _parse_gear_status(self, gear_code: str) -> str:
        """Parse gearbox status"""
        gear_map = {
            '0': '❌ 已禁用',
            '1': '✅ 自动挡已挂入',
            '2': '🔧 手动挡已挂入',
            '3': '⏸️ 保持 / 空挡模式',
        }
        return gear_map.get(str(gear_code), '未知')

    # ==================== BRAKES ====================

    def get_brake_status(self) -> Dict[str, Any]:
        """Get brake information"""
        running = self.data.get('additionalVehicleStatus', {}).get('runningStatus', {})

        stop_lights = bool(int(running.get('stopLi', 0)))

        return {
            'is_braking': stop_lights,
            'brake_status': self._parse_stop_light_status(running.get('stopLi', '0')),
            'stop_lights_on': stop_lights,
        }

    def _parse_stop_light_status(self, status: str) -> str:
        """Parse brake-light status"""
        status_map = {
            '0': '✅ 未制动（行驶或滑行）',
            '1': '🔴 制动中',
        }
        return status_map.get(str(status), '未知')

    # ==================== LIGHTS ====================

    def get_lights_status(self) -> Dict[str, Any]:
        """Get the complete light status"""
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
        """Return a text description of the lights"""
        drl = bool(int(running.get('drl', 0)))
        lo_beam = bool(int(running.get('loBeam', 0)))
        hi_beam = bool(int(running.get('hiBeam', 0)))
        stop = bool(int(running.get('stopLi', 0)))

        if stop:
            return '🔴 制动中'
        elif hi_beam:
            return '🔆 远光灯'
        elif lo_beam:
            return '💡 近光灯'
        elif drl:
            return '☀️ 日间行车灯'
        else:
            return '⚫ 灯光关闭（白天或驻车）'

    # ==================== AIR QUALITY ====================

    def get_pollution_info(self) -> Dict[str, Any]:
        """Get air-quality information"""
        pollution = self.data.get('additionalVehicleStatus', {}).get('pollutionStatus', {})

        return {
            'interior_pm25': int(float(pollution.get('interiorPM25', 0))),
            'interior_pm25_level': self._parse_pm25_level(pollution.get('interiorPM25Level', '0')),
            'exterior_pm25_level': self._parse_pm25_level(pollution.get('exteriorPM25Level', '0')),
            'relative_humidity': int(float(pollution.get('relHumSts', 0))),
        }

    def _parse_pm25_level(self, level_code: str) -> str:
        """Translate the PM2.5 level"""
        level_map = {
            '0': '优 🟢',
            '1': '良 🟢',
            '2': '中 🟡',
            '3': '差 🟠',
            '4': '很差 🔴',
            '5': '严重 🚨',
        }
        return level_map.get(str(level_code), '未知')

    def get_air_quality_alert(self) -> Dict[str, Any]:
        """Check air quality (ATTENTION!)"""
        pollution = self.data.get('additionalVehicleStatus', {}).get('pollutionStatus', {})

        interior_pm25 = int(pollution.get('interiorPM25', 0))
        interior_level = int(pollution.get('interiorPM25Level', 0))
        humidity = int(pollution.get('relHumSts', 0))

        alerts = []

        if interior_pm25 > 300:
            alerts.append(f"🚨 严重：PM2.5 = {interior_pm25} µg/m³（正常应 < 35）")
        elif interior_pm25 > 100:
            alerts.append(f"⚠️ 很差：PM2.5 = {interior_pm25} µg/m³")

        if interior_level == 5:
            alerts.append("🔴 污染等级：很差")

        if humidity > 100:
            alerts.append(f"⚠️ 湿度传感器异常：{humidity}%（不合理）")

        return {
            'alerts': alerts,
            'interior_pm25': interior_pm25,
            'interior_level': interior_level,
            'humidity': humidity,
            'has_alerts': len(alerts) > 0,
        }

    # ==================== PARKING TIME ====================

    def get_park_info(self) -> Dict[str, Any]:
        """
        Get parking information

        ✅ PROTECTION AGAINST EMPTY STRINGS!
        """

        # Step 1: Read the value as a string
        park_time_str = self.data.get('parkTime', {}).get('status', '')

        # Step 2: Check whether the string is empty
        if not park_time_str or park_time_str == '':
            print("[DEBUG] parkTime is empty - vehicle is not parked")
            return {
                'is_parked': False,
                'parked_since': None,
                'park_duration': '未停车',
                'total_seconds': 0,
            }
        try:
            park_time_ms = int(park_time_str)
        except (ValueError, TypeError) as e:
            print(f"[ERROR] Cannot convert parkTime to a number: {park_time_str} - {e}")
            return {
                'is_parked': False,
                'parked_since': None,
                'park_duration': '未停车',
                'total_seconds': 0,
            }

            # Step 4: If time = 0, the vehicle is not parked
        if park_time_ms == 0:
            return {
                'is_parked': False,
                'parked_since': None,
                'park_duration': '未停车',
                'total_seconds': 0,
            }

            # Step 5: Calculate the parking duration
        try:
            park_datetime = datetime.fromtimestamp(park_time_ms / 1000)
            current_time = datetime.now()
            park_duration = current_time - park_datetime

            total_seconds = int(park_duration.total_seconds())
            days = total_seconds // 86400
            hours = (total_seconds % 86400) // 3600
            minutes = (total_seconds % 3600) // 60

            # Format a readable duration
            if days > 0:
                duration_str = f"{days}天 {hours}小时 {minutes}分钟"
            elif hours > 0:
                duration_str = f"{hours}小时 {minutes}分钟"
            else:
                duration_str = f"{minutes}分钟"

            print(f"[DEBUG] Parked {duration_str}")

            return {
                'is_parked': True,
                'parked_since': park_datetime.strftime('%Y-%m-%d %H:%M:%S'),
                'park_duration': duration_str,
                'total_seconds': total_seconds,
            }
        except Exception as e:
            print(f"[ERROR] Ошибка при расhете вреmени парковки: {e}")
            return {
                'is_parked': False,
                'parked_since': None,
                'park_duration': '数据异常',
                'total_seconds': 0,
            }

    # ==================== CHARGING ====================

    def get_charging_info(self) -> Dict[str, Any]:
        """Get charging information (AC and DC)"""
        ev_status = self.data.get('additionalVehicleStatus', {}).get('electricVehicleStatus', {})

        return {
            # ===== AC CHARGING =====
            'charge_status': self._parse_charge_status(ev_status.get('chargeSts', '0')),
            'charge_pile_voltage': float(ev_status.get('dcChargePileUAct', 0)),
            'current_power_input': float(ev_status.get('averPowerConsumption', 0)),
            'ac_charge_status': self._parse_charge_status(ev_status.get('chargeSts', '0')),

            # ===== DC CHARGING (FAST) =====
            'dc_charge_status': self._parse_dc_charge_status(ev_status.get('dcChargeSts', '0')),
            'dc_charge_pile_current': float(ev_status.get('dcChargePileIAct', 0)),
            'dc_charge_pile_voltage': float(ev_status.get('dcChargePileUAct', 0)),
            'dc_power': self._calculate_dc_power(
                float(ev_status.get('dcChargePileUAct', 0)),
                float(ev_status.get('dcChargePileIAct', 0))
            ),
            'dc_dc_activated': bool(int(ev_status.get('dcDcActvd', 0))),
            'dc_dc_connect_status': self._parse_dc_dc_status(ev_status.get('dcDcConnectStatus', '0')),

            # ===== DISCHARGE (V2L, V2H) =====
            'discharge_voltage': float(ev_status.get('disChargeUAct', 0)),
            'discharge_current': float(ev_status.get('disChargeIAct', 0)),
            'discharge_power': self._calculate_discharge_power(
                float(ev_status.get('disChargeUAct', 0)),
                float(ev_status.get('disChargeIAct', 0))
            ),
            'discharge_connector_status': self._parse_charge_connector_status(
                ev_status.get('disChargeConnectStatus', '0')),

            # ===== GENERAL INFORMATION =====
            'charger_state': self._parse_charger_state(ev_status.get('chargerState', '0')),
            'time_to_fully_charged': int(float(ev_status.get('timeToFullyCharged', 0))),
        }

    def _parse_charge_connector_status(self, status_code: str) -> str:
        """Parse the charging connector status"""
        status_map = {
            '0': '未连接',
            '1': '已连接',
            '2': '故障',
        }
        return status_map.get(str(status_code), '未知')

    def estimate_battery_recovery(self) -> Dict[str, Any]:
        """
        Estimate battery recovery via regenerative braking.
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
            'recovery_status': '⚡ 能量回收中' if (is_braking and speed > 0) else '无能量回收',
        }

    def get_ahbc_status(self) -> str:
        """
        Get the AHBC status with debug context.
        JSON path: additionalVehicleStatus -> runningStatus -> ahbc
        """
        # 1. Try to read additionalVehicleStatus
        additional = self.data.get('additionalVehicleStatus')

        # If the payload is wrapped again in 'data' (can happen in saved files)
        if not additional:
            additional = self.data.get('data', {}).get('additionalVehicleStatus')

        if not additional:
            return "错误：缺少附加车辆状态"

        # 2. Try to read runningStatus
        running = additional.get('runningStatus')
        if not running:
            return "错误：缺少运行状态"

        # 3. Look up the ahbc value
        ahbc_val = running.get('ahbc')

        # If the key is completely missing
        if ahbc_val is None:
            return "错误：未找到防盗状态字段"

        # 4. Convert to a string and inspect it
        val_str = str(ahbc_val).strip()

        if val_str == '0':
            return "已启用"
        elif val_str == '1':
            return "已禁用"

        # If the value is unexpected (not 0 or 1), expose it
        return f"未知（值：{val_str}）"

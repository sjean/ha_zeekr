# custom_components/zeekr/const.py
"""Constants for the Zeekr integration."""

DOMAIN = "zeekr"
NAME = "Zeekr"
VERSION = "1.0.0"

CONF_MOBILE = "mobile"
CONF_SMS_CODE = "sms_code"

DEFAULT_SCAN_INTERVAL = 300  # 5 minutes

# Attributes
ATTR_VIN = "vin"
ATTR_LATITUDE = "latitude"
ATTR_LONGITUDE = "longitude"
ATTR_CHARGE_LEVEL = "charge_level"
ATTR_DISTANCE_TO_EMPTY = "distance_to_empty"

# Icons
ICON_BATTERY = "mdi:battery"
ICON_TEMPERATURE = "mdi:thermometer"
ICON_LOCATION = "mdi:map-marker"
ICON_DOOR = "mdi:door"
ICON_WINDOW = "mdi:window-closed"
ICON_CAR = "mdi:car"
ICON_REFRESH = "mdi:refresh"

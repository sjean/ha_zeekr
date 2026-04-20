# config.py
"""Configuration for the Zeekr API integration."""

# ==================== API ENDPOINTS ====================
BASE_URL_TOC = 'https://api-gw-toc.zeekrlife.com'  # Authentication
BASE_URL_SECURE = 'https://api.zeekrline.com'      # Vehicle data retrieval
BASE_URL_REMOTE_CONTROL = 'https://gric-zhf-api.geely.com'  # New Geely gateway for remote control
BASE_URL_REMOTE_CONTROL_AUTH = 'https://gric-api.geely.com'  # Midground auth exchange before remote control
YIKAT_AUTH_ENDPOINT = '/zeekrlife-mp-auth2/v1/auth/accessCodeList'  # YIKAT retrieval

# ==================== API KEYS ====================
X_CA_SECRET = 'MIGfMA0GCSqGSIb3DQEBAQUAA4GNADCBiQKBgQCz09z6e9WOcNq+nUMX8Vq1Xe2EmJxuR3XbtureDCS90dfkok'
X_CA_KEY = 'APP-SIGN-SECRET-KEY'
HMAC_SECRET = 'e83a60805fa54de9bdfcb0f2d6bca757'

# ==================== REMOTE CONTROL KEYS ====================
# These values were extracted from the official mobile app on 2026-04-18.
REMOTE_CONTROL_APP_ID = 'GEELYCNCH001M0001'
REMOTE_CONTROL_INSTRUCTION_APP_ID = 'e0fb071ad0a94387bc0d90d56ab7d2a2'
REMOTE_CONTROL_INSTRUCTION_APP_SECRET = '5bdc0105286c44d8a7bd41acd9faae5a'
REMOTE_CONTROL_HTTP_SECRET_KEY = 'c6163310f263911af87194dd290247fd'
REMOTE_CONTROL_VIN_KEY = '2014052600006128'
REMOTE_CONTROL_VIN_IV = 'aebd1811194e82d9'
REMOTE_CONTROL_SIGNATURE_VERSION = '2.1'

# ==================== REMOTE CONTROL DEFAULT HEADERS ====================
REMOTE_CONTROL_ACCEPT_LANGUAGE = 'zh_CN'
REMOTE_CONTROL_APP_VERSION = 'v1.0.0'
REMOTE_CONTROL_PLATFORM = 'Android'
REMOTE_CONTROL_SALES_PLATFORM = 'ZEEKR'
REMOTE_CONTROL_TENANT_ID = 'ZEEKR'
REMOTE_CONTROL_TSP_PLATFORM = '4'
REMOTE_CONTROL_VEHICLE_BRAND = 'ZEEKR'
REMOTE_CONTROL_DEVICE_BRAND = 'ONEPLUS'
REMOTE_CONTROL_DEVICE_MODEL = 'PLK110'
REMOTE_CONTROL_DEVICE_OS_VERSION = 'Android 16 (API 36)'

# ==================== APP INFO ====================
APP_VERSION = '4.0.2'
PHONE_MODEL = 'iPhone13'
PHONE_VERSION = '17.4.1'
APP_TYPE = 'IOS'

# ==================== REQUEST SETTINGS ====================
REQUEST_TIMEOUT = 30  # Request timeout in seconds
REFRESH_INTERVAL = 5  # Status refresh interval in minutes
MAX_RETRIES = 3       # Maximum reconnection attempts

# ==================== STORAGE ====================
TOKENS_FILE = '../../../../Downloads/HA_ZeekrCH/V3/HA_ZeekrCH_v3/tokens.json'  # Token storage file

# ==================== REGION ====================
REGION_CODE = '+86'  # China region

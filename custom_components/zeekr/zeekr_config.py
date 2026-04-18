# config.py
"""Configuration for the Zeekr API integration."""

# ==================== API ENDPOINTS ====================
BASE_URL_TOC = 'https://api-gw-toc.zeekrlife.com'  # Authentication
BASE_URL_SECURE = 'https://api.zeekrline.com'      # Vehicle data retrieval
YIKAT_AUTH_ENDPOINT = '/zeekrlife-mp-auth2/v1/auth/accessCodeList'  # YIKAT retrieval

# ==================== API KEYS ====================
X_CA_SECRET = 'MIGfMA0GCSqGSIb3DQEBAQUAA4GNADCBiQKBgQCz09z6e9WOcNq+nUMX8Vq1Xe2EmJxuR3XbtureDCS90dfkok'
X_CA_KEY = 'APP-SIGN-SECRET-KEY'
HMAC_SECRET = 'e83a60805fa54de9bdfcb0f2d6bca757'

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

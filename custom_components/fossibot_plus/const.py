"""Constants for the FOSSiBOT integration."""

DOMAIN = "fossibot_plus"

BASE_URL = "http://app.fossibot.hk"
LOGIN_ENDPOINT = f"{BASE_URL}/prod-api/app/user/login"
DEVICE_LIST_ENDPOINT = f"{BASE_URL}/prod-api/app/user_device/list"
CONTROL_ENDPOINT = f"{BASE_URL}/prod-api/app/ctrl/route"
WS_URL = "ws://app.fossibot.hk/ws"

HEARTBEAT_INTERVAL = 5
RECONNECT_DELAY = 5
FRAME_SILENCE_TIMEOUT = 30
DEVICE_STATUS_POLL_INTERVAL = 60

LOGIN_DUPLICATE_SUBMIT_MARKER = "重复提交"
LOGIN_RETRY_DELAY = 6
LOGIN_MAX_RETRIES = 2

CONF_EMAIL = "email"
CONF_PASSWORD = "password"

CTRL_COMMAND_PREFIX = "0e000c000800"

# ---------------------------------------------------------------------------
# TLV tags — confirmed from WS captures and ctrl-route command intercepts
# ---------------------------------------------------------------------------

# Telemetry (read)
TAG_BATTERY_SOC        = "0100"   # %
TAG_TEMPERATURE        = "0200"   # °C, take low 16 bits only
TAG_REMAINING_MINUTES  = "0300"   # minutes
TAG_CHARGING_ACTIVE    = "0400"   # 0/1
TAG_BMS_VERSION        = "0500"   # u32 packed version
TAG_AC_GRID_POWER      = "1300"   # W, grid input
TAG_AC_OUTPUT_POWER    = "1400"   # W, AC output only
TAG_AC_OUTPUT_VOLTAGE  = "1500"   # raw*0.1 = V
TAG_AC_FREQUENCY       = "1600"   # raw*0.1 = Hz
TAG_DC_INPUT_POWER     = "1700"   # W, solar/DC input
TAG_PCS_VERSION        = "1200"   # u32 packed version
TAG_TOTAL_INPUT_POWER  = "2200"   # W, grid + solar
TAG_TOTAL_OUTPUT_POWER = "2300"   # W, AC + USB + DC
TAG_DC_OUTPUT_POWER    = "2400"   # W, DC 12V output
TAG_USB_OUTPUT_POWER   = "2500"   # W, USB output
TAG_CHARGE_POWER       = "2a00"   # W, charge power (read + limit)
TAG_FIRMWARE           = "2f00"   # u32 packed version
TAG_SOLAR_ENERGY       = "3000"   # kWh accumulated DC input

# Control (read + write)
TAG_LED_MODE           = "2600"   # 0=off,1=steady,2=SOS,3=strobe
TAG_AC_STATE           = "2700"   # 0/1
TAG_DC_STATE           = "2800"   # 0/1
TAG_USB_STATE          = "2900"   # 0/1
TAG_OUTPUT_MEMORY      = "2b00"   # 0/1
TAG_SCREEN_TIMEOUT     = "2c00"   # index: 0=always,1=30s,2=1m,3=5m,4=10m,5=30m
TAG_POWER_OFF_TIMER    = "2d00"   # index: 0=never,1=5m,2=10m,3=1h,4=8h
TAG_CHARGE_MODE        = "2e00"   # 0=UPS,1=ECO
TAG_SOUND              = "3300"   # 0/1
TAG_CHARGE_LIMIT       = "3100"   # %, max SOC to charge to
TAG_DISCHARGE_LIMIT    = "3200"   # %, min SOC before stop discharge
TAG_SCREEN_BRIGHTNESS  = "3400"   # %
TAG_DC_CHARGE_CURRENT  = "3500"   # A, DC charge current
TAG_DC_STANDBY         = "3800"   # standby index (STANDBY_OPTIONS)
TAG_USB_STANDBY        = "3900"   # standby index
TAG_AC_STANDBY         = "3a00"   # standby index

# ---------------------------------------------------------------------------
# Model profiles
# ---------------------------------------------------------------------------

CHARGE_POWER_LIMITS: dict[str, dict] = {
    "f1800":  {"min": 100, "max": 1200, "step": 100},
    "f3000":  {"min": 100, "max": 2000, "step": 100},
    "custom": {"min": 100, "max": 2000, "step": 100},
}

DC_CHARGE_CURRENT_LIMITS: dict[str, int] = {
    "f1800": 15,
    "f3000": 25,
    "custom": 15,
}


def detect_model(sn_code: str) -> str:
    """Detect model family from the serial number prefix."""
    sn = sn_code.upper()
    if sn.startswith("F180"):
        return "f1800"
    if sn.startswith("F300"):
        return "f3000"
    return "custom"

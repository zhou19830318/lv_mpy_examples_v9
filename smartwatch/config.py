# config.py - 智能手表应用配置文件

# ===== WiFi 配置 =====
WIFI_SSID = "xxx"
WIFI_PASSWORD = "xxx"

# ===== 天气服务配置 (知心天气) =====
WEATHER_KEY = "xxx"
DEFAULT_CITY = "changzhou"
WEATHER_API_URL = "https://api.seniverse.com/v3/weather/now.json"

# 中国城市列表 (用于设置页面)
CHINESE_CITIES = [
    {"name": "北京", "id": "beijing"},
    {"name": "上海", "id": "shanghai"},
    {"name": "深圳", "id": "shenzhen"},
    {"name": "广州", "id": "guangzhou"},
    {"name": "常州", "id": "changzhou"},
    {"name": "杭州", "id": "hangzhou"},
    {"name": "成都", "id": "chengdu"},
    {"name": "南京", "id": "nanjing"}
]

# ===== 时区配置 =====
TIMEZONES = [
    {"name": "北京时间 (CST)", "offset": 8 * 3600},
    {"name": "伦敦时间 (GMT)", "offset": 0 * 3600},
    {"name": "纽约时间 (EST)", "offset": -5 * 3600},
    {"name": "迪拜时间 (GST)", "offset": 4 * 3600}
]
DEFAULT_TZ_INDEX = 0

# ===== API 接口信息 =====
# 如果有其它 API (如豆包、汇率等)，可以在此添加
EXCHANGE_RATE_API = "https://api.exchangerate-api.com/v4/latest/USD"

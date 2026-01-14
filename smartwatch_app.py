import lvgl as lv
import time
import gc
import machine
import network
import urequests
import json
import ntptime
import fs_driver
from machine import RTC, Pin, PWM
from display_driver import init_display, init_touch
from cst816s import GESTURE_SWIPE_LEFT, GESTURE_SWIPE_RIGHT, GESTURE_SWIPE_UP, GESTURE_SWIPE_DOWN

# ===== 配置信息 (参考 watch_th.py) =====
SSID = "xxx"
PASSWORD = "xxx"
CITY = "changzhou"

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

# 时区配置列表
TIMEZONES = [
    {"name": "北京时间 (CST)", "offset": 8 * 3600},
    {"name": "伦敦时间 (GMT)", "offset": 0 * 3600},
    {"name": "纽约时间 (EST)", "offset": -5 * 3600},
    {"name": "迪拜时间 (GST)", "offset": 4 * 3600}
]
current_tz_idx = 0

WEATHER_KEY = "xxx" # 知心天气 Key
WEATHER_URL = f"https://api.seniverse.com/v3/weather/now.json?key={WEATHER_KEY}&location={CITY}&language=zh-Hans&unit=c"

# ===== 初始化硬件 =====
lv.init()
display = init_display()
touch = init_touch()

# 手动初始化背光 PWM (Pin 2)
# 注意：由于在 display_driver.py 中移除了背光控制，这里我们可以安全地使用 PWM
bl_pwm = PWM(Pin(2), freq=1000)

def set_screen_brightness(value):
    # value 范围 0-100
    # 修正：根据用户反馈，亮度反了，说明硬件可能是高电平点亮 (STATE_HIGH)
    # 或者 PWM 逻辑与预期相反。
    # 100% 亮度 -> duty = 1023
    # 0% 亮度 -> duty = 0
    duty = int(value * 10.23)
    if duty > 1023: duty = 1023
    if duty < 0: duty = 0
    bl_pwm.duty(duty)
    print(f"Manual PWM duty set to {duty} for brightness {value}")

# 屏幕基本设置
display.set_power(True)
display.init()
display.set_color_inversion(True)
display.set_rotation(lv.DISPLAY_ROTATION._180)
# 初始亮度 100%
set_screen_brightness(100)

# 注册文件系统以便加载字体 (参考 watch_th.py)
try:
    fs_drv = lv.fs_drv_t()
    fs_driver.fs_register(fs_drv, 'S')
    # 尝试加载中文字体，优先尝试 assets 中的字体
    # 如果 watch_th.py 中的 myfont_18.bin 存在于根目录或 S: 盘，也可以尝试
    try:
        font_cn = lv.binfont_create("S:myfont_16.bin")
    except:
        try:
            font_cn = lv.binfont_create("S:myfont_18.bin")
        except:
            try:
                font_cn = lv.binfont_create("S:assets/font/font-PHT-cn-20.fnt")
            except:
                font_cn = lv.font_montserrat_16 # 备选
                print("Warning: Chinese font not found, using Montserrat")
except Exception as e:
    print(f"FS/Font init error: {e}")
    font_cn = lv.font_montserrat_16

rtc = RTC()
sta_if = network.WLAN(network.STA_IF)

# ===== 全局状态 =====
screens = []
current_screen_idx = 0
last_swipe_time = 0
swipe_cooldown = 800 # 增加冷却时间到 800ms，防止连跳
current_brightness = 100

# ===== 网络功能 (参考 watch_th.py) =====
def connect_wifi():
    if not sta_if.isconnected():
        print("Connecting to WiFi...")
        sta_if.active(True)
        sta_if.connect(SSID, PASSWORD)
        max_wait = 10
        while max_wait > 0:
            if sta_if.isconnected():
                print("WiFi Connected. IP:", sta_if.ifconfig()[0])
                return True
            max_wait -= 1
            time.sleep(1)
        print("WiFi Connection Failed")
        return False
    return True

def sync_time():
    if connect_wifi():
        try:
            print("Syncing time via NTP...")
            ntptime.settime()
            
            # 默认同步北京时间到 RTC
            utc_ticks = time.time()
            local_ticks = utc_ticks + TIMEZONES[0]['offset']
            t = time.localtime(local_ticks)
            
            rtc.datetime((t[0], t[1], t[2], t[6], t[3], t[4], t[5], 0))
            print("Time synced with Beijing offset")
            return True
        except Exception as e:
            print("NTP error:", e)
    return False

def fetch_weather_data():
    if connect_wifi():
        try:
            print("Fetching weather...")
            res = urequests.get(WEATHER_URL)
            data = res.json()
            res.close()
            return data["results"][0]["now"]
        except Exception as e:
            print("Weather fetch error:", e)
    return None

# ===== UI 组件创建 =====

# 1. 时间屏幕
screen_time = lv.obj()
screen_time.set_style_bg_color(lv.color_hex(0x000000), 0)

label_clock = lv.label(screen_time)
label_clock.set_style_text_font(lv.font_montserrat_48, 0)
label_clock.set_style_text_color(lv.color_hex(0xFFFFFF), 0)
label_clock.align(lv.ALIGN.CENTER, 0, -30)

label_date = lv.label(screen_time)
label_date.set_style_text_font(lv.font_montserrat_16, 0)
label_date.set_style_text_color(lv.color_hex(0xAAAAAA), 0)
label_date.align(lv.ALIGN.CENTER, 0, 20)

label_tz = lv.label(screen_time)
label_tz.set_style_text_font(font_cn, 0)
label_tz.set_style_text_color(lv.palette_main(lv.PALETTE.CYAN), 0)
label_tz.align(lv.ALIGN.CENTER, 0, 50)
label_tz.set_text(TIMEZONES[current_tz_idx]["name"])

# 2. 天气屏幕
screen_weather = lv.obj()
screen_weather.set_style_bg_color(lv.color_hex(0x000000), 0)

label_w_city = lv.label(screen_weather)
# 查找当前城市的中文名
city_name_cn = CITY.upper()
for c in CHINESE_CITIES:
    if c["id"] == CITY:
        city_name_cn = c["name"]
        break
label_w_city.set_text(city_name_cn)
label_w_city.set_style_text_font(font_cn, 0)
label_w_city.align(lv.ALIGN.TOP_MID, 0, 30)

img_w_icon = lv.image(screen_weather)
img_w_icon.align(lv.ALIGN.CENTER, 0, -40)
img_w_icon.set_size(60, 60)

label_w_temp = lv.label(screen_weather)
label_w_temp.set_text("--°C")
label_w_temp.set_style_text_font(lv.font_montserrat_48, 0)
label_w_temp.set_style_text_color(lv.palette_main(lv.PALETTE.ORANGE), 0)
label_w_temp.align(lv.ALIGN.CENTER, 0, 20)

label_w_desc = lv.label(screen_weather)
label_w_desc.set_text("加载中...")
label_w_desc.set_style_text_font(font_cn, 0)
label_w_desc.align(lv.ALIGN.BOTTOM_MID, 0, -40)

# 3. 二维码屏幕
screen_qr = lv.obj()
screen_qr.set_style_bg_color(lv.color_hex(0x000000), 0)

qr = lv.qrcode(screen_qr)
qr.set_size(140)
qr.set_dark_color(lv.color_hex(0x000000))
qr.set_light_color(lv.color_hex(0xFFFFFF))
qr_data = "https://lvgl.io"
qr.update(qr_data, len(qr_data))
qr.center()

label_qr = lv.label(screen_qr)
label_qr.set_text("扫码访问")
label_qr.set_style_text_font(font_cn, 0)
label_qr.align(lv.ALIGN.BOTTOM_MID, 0, -20)

# 4. 系统信息屏幕
screen_sys = lv.obj()
screen_sys.set_style_bg_color(lv.color_hex(0x000000), 0)

label_sys_title = lv.label(screen_sys)
label_sys_title.set_text("系统信息")
label_sys_title.set_style_text_font(font_cn, 0)
label_sys_title.align(lv.ALIGN.TOP_MID, 0, 40)

label_uptime = lv.label(screen_sys)
label_uptime.set_style_text_font(font_cn, 0)
label_uptime.align(lv.ALIGN.CENTER, 0, -10)

label_mem = lv.label(screen_sys)
label_mem.set_style_text_font(font_cn, 0)
label_mem.align(lv.ALIGN.CENTER, 0, 20)

# 5. 设置屏幕
screen_settings = lv.obj()
screen_settings.set_style_bg_color(lv.color_hex(0x000000), 0)

label_set_title = lv.label(screen_settings)
label_set_title.set_text("系统设置")
label_set_title.set_style_text_font(font_cn, 0)
label_set_title.align(lv.ALIGN.TOP_MID, 0, 20)

# 城市选择下拉框
dd_city = lv.dropdown(screen_settings)
dd_city.set_options("\n".join([city["name"] for city in CHINESE_CITIES]))
dd_city.set_style_text_font(font_cn, 0)

# 加载自定义下拉箭头图标 (参考 watch_th.py 的图片加载方式)
try:
    caret_path = "./img_caret_down_13x8_argb8888.png"
    with open(caret_path, 'rb') as f:
        caret_data = f.read()
    caret_img_dsc = lv.image_dsc_t({
        'data_size': len(caret_data),
        'data': caret_data
    })
    dd_city.set_symbol(caret_img_dsc)
    # 防止数据被 GC 回收
    dd_city_cache = {"data": caret_data, "dsc": caret_img_dsc}
except Exception as e:
    print(f"Caret icon load error: {e}")

# 重要：设置下拉列表（弹出菜单）的字体
dd_list = dd_city.get_list()
if dd_list:
    dd_list.set_style_text_font(font_cn, 0)
dd_city.set_width(150)
dd_city.align(lv.ALIGN.CENTER, 0, -45)

# 亮度调节
label_brightness = lv.label(screen_settings)
label_brightness.set_text("屏幕亮度")
label_brightness.set_style_text_font(font_cn, 0)
label_brightness.align(lv.ALIGN.CENTER, 0, 0)

slider_brightness = lv.slider(screen_settings)
slider_brightness.set_range(10, 100)
slider_brightness.set_value(current_brightness, False)
slider_brightness.set_width(160)
slider_brightness.align(lv.ALIGN.CENTER, 0, 30)

def slider_event_cb(e):
    global current_brightness
    current_brightness = slider_brightness.get_value()
    print(f"Setting brightness to: {current_brightness}")
    set_screen_brightness(current_brightness)

slider_brightness.add_event_cb(slider_event_cb, lv.EVENT.VALUE_CHANGED, None)

# 初始化下拉框选中项
for i, city in enumerate(CHINESE_CITIES):
    if city["id"] == CITY:
        dd_city.set_selected(i)
        break

# 确定按钮
btn_save = lv.button(screen_settings)
btn_save.set_size(100, 40)
btn_save.align(lv.ALIGN.CENTER, 0, 75)
btn_save_label = lv.label(btn_save)
btn_save_label.set_text("保存")
btn_save_label.set_style_text_font(font_cn, 0)
btn_save_label.set_style_text_color(lv.color_hex(0x000000), 0) # 设置字体颜色为黑色
btn_save_label.center()

def save_settings_event_cb(e):
    global CITY, WEATHER_URL
    selected_idx = dd_city.get_selected()
    CITY = CHINESE_CITIES[selected_idx]["id"]
    # 更新天气 URL，使用中文语言
    WEATHER_URL = f"https://api.seniverse.com/v3/weather/now.json?key={WEATHER_KEY}&location={CITY}&language=zh-Hans&unit=c"
    print(f"City updated to: {CITY}")
    
    # 更新天气页面显示的城市名
    city_name_cn = CHINESE_CITIES[selected_idx]["name"]
    label_w_city.set_text(city_name_cn)
    
    # 触发一次天气更新
    update_weather_cb(None)
    
    # 切换回时间页面
    switch_screen("next") # 简单切换到下一个屏幕

btn_save.add_event_cb(save_settings_event_cb, lv.EVENT.CLICKED, None)

screens = [screen_time, screen_weather, screen_qr, screen_sys, screen_settings]

# ===== 逻辑处理 =====

def update_time_cb(t):
    # RTC 存储的是北京时间 (UTC+8)
    # 我们先转回 UTC，再根据当前选择的时区偏移计算
    now_ticks = time.time()
    utc_ticks = now_ticks - TIMEZONES[0]['offset']
    local_ticks = utc_ticks + TIMEZONES[current_tz_idx]['offset']
    
    now = time.localtime(local_ticks)
    label_clock.set_text("{:02d}:{:02d}:{:02d}".format(now[3], now[4], now[5]))
    label_date.set_text("{:04d}-{:02d}-{:02d}".format(now[0], now[1], now[2]))
    label_tz.set_text(TIMEZONES[current_tz_idx]["name"])

def update_weather_cb(t):
    weather = fetch_weather_data()
    if weather:
        label_w_temp.set_text(f"{weather['temperature']}°C")
        label_w_desc.set_text(weather['text'])
        
        # 加载天气图标
        try:
            code = weather['code']
            # 尝试多种可能的路径格式
            paths = [
                f"weather_incons/{code}@1x.png",
                f"/weather_incons/{code}@1x.png"
            ]
            
            png_data = None
            tried_paths = []
            for path in paths:
                try:
                    with open(path, 'rb') as f:
                        png_data = f.read()
                    print(f"Icon loaded from: {path}")
                    break
                except:
                    tried_paths.append(path)
            
            if png_data:
                # 创建图像描述符
                img_dsc = lv.image_dsc_t({
                    'data_size': len(png_data),
                    'data': png_data
                })
                img_w_icon.set_src(img_dsc)
            else:
                print(f"Failed to find icon at: {tried_paths}")
                # 尝试加载默认图标
                for default_path in ["weather_incons/99@1x.png", "/weather_incons/99@1x.png"]:
                    try:
                        with open(default_path, 'rb') as f:
                            png_data = f.read()
                        img_dsc = lv.image_dsc_t({'data_size': len(png_data), 'data': png_data})
                        img_w_icon.set_src(img_dsc)
                        print(f"Loaded default icon from: {default_path}")
                        break
                    except:
                        pass
        except Exception as e:
            print(f"Icon update logic error: {e}")
    else:
        label_w_desc.set_text("离线")

start_ticks = time.ticks_ms()
def update_sys_cb(t):
    uptime_s = time.ticks_diff(time.ticks_ms(), start_ticks) // 1000
    label_uptime.set_text("运行时间: {}s".format(uptime_s))
    gc.collect()
    mem_free = gc.mem_free()
    mem_alloc = gc.mem_alloc()
    label_mem.set_text("内存剩余: {} KB".format(mem_free // 1024))

# 创建定时器
timer_time = lv.timer_create(update_time_cb, 200, None) # 提高刷新频率到 200ms，防止秒钟跳显
timer_weather = lv.timer_create(update_weather_cb, 3600000, None) # 每小时更新一次
timer_sys = lv.timer_create(update_sys_cb, 2000, None)

def switch_screen(direction):
    global current_screen_idx
    if direction == "next":
        current_screen_idx = (current_screen_idx + 1) % len(screens)
    elif direction == "prev":
        current_screen_idx = (current_screen_idx - 1) % len(screens)
    lv.screen_load(screens[current_screen_idx])

def switch_timezone(direction):
    global current_tz_idx
    if direction == "next":
        current_tz_idx = (current_tz_idx + 1) % len(TIMEZONES)
    elif direction == "prev":
        current_tz_idx = (current_tz_idx - 1) % len(TIMEZONES)
    update_time_cb(None)

def check_gesture():
    global last_swipe_time
    
    gesture = touch.get_gesture()
    if gesture == 0: # 无手势
        return

    now = time.ticks_ms()
    if time.ticks_diff(now, last_swipe_time) < swipe_cooldown:
        return

    if gesture == GESTURE_SWIPE_RIGHT:
        switch_screen("prev")
        last_swipe_time = now
    elif gesture == GESTURE_SWIPE_LEFT:
        switch_screen("next")
        last_swipe_time = now
    elif gesture == GESTURE_SWIPE_UP:
        if lv.screen_active() == screen_time:
            switch_timezone("next")
            last_swipe_time = now
    elif gesture == GESTURE_SWIPE_DOWN:
        if lv.screen_active() == screen_time:
            switch_timezone("prev")
            last_swipe_time = now

# ===== 初始化启动 =====
lv.screen_load(screen_time)
sync_time()
update_weather_cb(None)

# --- 主循环 ---
while True:
    lv.tick_inc(5)
    check_gesture()
    lv.task_handler()
    time.sleep_ms(5)

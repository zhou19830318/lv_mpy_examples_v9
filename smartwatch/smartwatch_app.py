import gc
import machine
import network
from machine import RTC, Pin, PWM

# 立即初始化 WiFi 接口，确保在内存碎片化前分配成功
gc.collect()
rtc = RTC()
sta_if = network.WLAN(network.STA_IF)
gc.collect()

import lvgl as lv
import time
import urequests
import json
import ntptime
import fs_driver
import random 
import math
try:
    import neopixel
except ImportError:
    neopixel = None
from display_driver import init_display, init_touch
from cst816s import GESTURE_SWIPE_LEFT, GESTURE_SWIPE_RIGHT, GESTURE_SWIPE_UP, GESTURE_SWIPE_DOWN
import config # 导入配置文件

# ===== 配置信息 (从 config.py 加载) =====
SSID = config.WIFI_SSID
PASSWORD = config.WIFI_PASSWORD
CITY = config.DEFAULT_CITY
CHINESE_CITIES = config.CHINESE_CITIES
TIMEZONES = config.TIMEZONES
current_tz_idx = config.DEFAULT_TZ_INDEX
WEATHER_KEY = config.WEATHER_KEY
WEATHER_URL = f"{config.WEATHER_API_URL}?key={WEATHER_KEY}&location={CITY}&language=zh-Hans&unit=c"
huilv_aip_key = config.HUILV_API_KEY

# ===== 初始化显示与输入 =====
lv.init()
display = init_display()
touch = init_touch()

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

# ===== 华为手表风格全局样式 =====
# 参考华为设计规范：https://developer.huawei.com/consumer/cn/doc/design-guides-V1/color-0000001053699747-V1
COLOR_HUAWEI_BLUE = lv.color_hex(0x1F71FF)     # 控件背景色
COLOR_HUAWEI_HIGHLIGHT = lv.color_hex(0x5EA1FF) # 文本高亮色
COLOR_HUAWEI_SUCCESS = lv.color_hex(0x64BB5C)   # 成功/通话色
COLOR_HUAWEI_WARNING = lv.color_hex(0xE84026)   # 警告/挂断色
COLOR_HUAWEI_SUBTEXT = lv.color_hex(0xAAAAAA)   # 二级文本色 (66% 不透明度近似)

style_title = lv.style_t()
style_title.init()
style_title.set_text_font(font_cn)
style_title.set_text_color(lv.color_hex(0xFFFFFF))

style_btn = lv.style_t()
style_btn.init()
style_btn.set_radius(21) # 胶囊形高度 42, 半径 21
style_btn.set_bg_color(COLOR_HUAWEI_BLUE)
style_btn.set_bg_opa(lv.OPA.COVER)
style_btn.set_text_color(lv.color_hex(0xFFFFFF))
style_btn.set_shadow_width(0)

style_value = lv.style_t()
style_value.init()
style_value.set_text_font(lv.font_montserrat_48)
style_value.set_text_color(lv.color_hex(0xFFFFFF))

style_subtext = lv.style_t()
style_subtext.init()
style_subtext.set_text_color(COLOR_HUAWEI_SUBTEXT)
style_subtext.set_text_font(font_cn)

# 特殊用途样式
style_btn_success = lv.style_t()
style_btn_success.init()
style_btn_success.set_radius(21)
style_btn_success.set_bg_color(COLOR_HUAWEI_SUCCESS)
style_btn_success.set_bg_opa(lv.OPA.COVER)
style_btn_success.set_text_color(lv.color_hex(0xFFFFFF))
style_btn_success.set_shadow_width(0)

style_btn_warning = lv.style_t()
style_btn_warning.init()
style_btn_warning.set_radius(21)
style_btn_warning.set_bg_color(COLOR_HUAWEI_WARNING)
style_btn_warning.set_bg_opa(lv.OPA.COVER)
style_btn_warning.set_text_color(lv.color_hex(0xFFFFFF))
style_btn_warning.set_shadow_width(0)

# 手动初始化背光 PWM (Pin 2)
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

# 初始化 WS2812 指示灯 (Pin 48)
try:
    if neopixel:
        np_led = neopixel.NeoPixel(Pin(48), 1)
        # 初始熄灭
        np_led[0] = (0, 0, 0)
        np_led.write()
    else:
        np_led = None
except Exception as e:
    print(f"WS2812 init error: {e}")
    np_led = None

# ===== 全局状态 =====
screens = []
current_screen_idx = 0
last_swipe_time = 0
swipe_cooldown = 800 # 增加冷却时间到 800ms，防止连跳
current_brightness = 100
last_weather_code = -1 # 缓存上次的天气代码
current_led_mode = 0 # 0:常亮, 1:爆闪, 2:呼吸, 3:彩虹, 4:渐进 (待生效)
active_led_mode = 0  # 实际运行的模式

# --- 初始化屏幕列表 (系统信息不再直接放入滑动列表) ---
# 注意：screen_sys 将通过设置页面进入
# screens 定义将在所有屏幕对象创建后进行
active_led_r = 0     # 实际运行的 R
active_led_g = 0     # 实际运行的 G
active_led_b = 0     # 实际运行的 B
led_effect_step = 0 # 用于动画步进

# ===== 运动数据状态 =====
sport_steps = 0
sport_calories = 0
sport_distance = 0.0
sport_duration = 0 # 秒
is_sporting = False

# ===== 网络功能 (参考 watch_th.py) =====
def connect_wifi():
    if not sta_if.isconnected():
        gc.collect() # 激活前清理内存
        print("Connecting to WiFi...")
        try:
            sta_if.active(True)
            sta_if.connect(SSID, PASSWORD)
        except OSError as e:
            print(f"WiFi Activation Error: {e}")
            return False
            
        max_wait = 15 # 增加等待时间
        while max_wait > 0:
            status = sta_if.status()
            if status == network.STAT_GOT_IP or sta_if.isconnected():
                print("WiFi Connected. IP:", sta_if.ifconfig()[0])
                gc.collect()
                return True
            elif status == network.STAT_WRONG_PASSWORD:
                print("WiFi: Wrong Password")
                return False
            elif status == network.STAT_NO_AP_FOUND:
                print("WiFi: AP not found")
            
            max_wait -= 1
            time.sleep(1)
        print("WiFi Connection Timeout")
        return False
    return True

def sync_time():
    if connect_wifi():
        try:
            print("Syncing time via NTP...")
            ntptime.settime()
            gc.collect() # 同步后清理
            
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
        res = None
        try:
            print("Fetching weather...")
            res = urequests.get(WEATHER_URL, timeout=10) # 增加超时
            if res.status_code == 200:
                data = res.json()
                res.close()
                res = None
                result = data["results"][0]["now"]
                del data
                gc.collect()
                return result
            else:
                print(f"Weather API Error: {res.status_code}")
                if res: res.close()
        except Exception as e:
            print(f"Weather Fetch Error: {e}")
            if res: res.close()
        finally:
            gc.collect()
    return None

# ===== UI 组件创建 =====

# 1. 时间屏幕 (华为手表表盘风格)
screen_time = lv.obj()
screen_time.set_style_bg_color(lv.color_hex(0x000000), 0)

label_clock = lv.label(screen_time)
label_clock.add_style(style_value, 0)
label_clock.set_style_text_font(lv.font_montserrat_48, 0) # 保持大字体
label_clock.align(lv.ALIGN.CENTER, 0, -20)

label_date = lv.label(screen_time)
label_date.add_style(style_subtext, 0)
label_date.set_style_text_font(lv.font_montserrat_16, 0)
label_date.align(lv.ALIGN.CENTER, 0, 25)

label_tz = lv.label(screen_time)
label_tz.add_style(style_title, 0)
label_tz.set_style_text_color(COLOR_HUAWEI_HIGHLIGHT, 0) # 华为高亮蓝
label_tz.align(lv.ALIGN.BOTTOM_MID, 0, -30)
label_tz.set_text(TIMEZONES[current_tz_idx]["name"])

# 2. 天气屏幕 (简洁卡片风格)
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
label_w_city.add_style(style_title, 0)
label_w_city.align(lv.ALIGN.TOP_MID, 0, 30)

img_w_icon = lv.image(screen_weather)
img_w_icon.align(lv.ALIGN.CENTER, 0, -30)
img_w_icon.set_size(64, 64)

label_w_temp = lv.label(screen_weather)
label_w_temp.set_text("--°C")
label_w_temp.add_style(style_value, 0)
label_w_temp.set_style_text_color(lv.color_hex(0xFF9500), 0) # 橙色强调
label_w_temp.align(lv.ALIGN.CENTER, 0, 35)

label_w_desc = lv.label(screen_weather)
label_w_desc.set_text("正在获取...")
label_w_desc.add_style(style_subtext, 0)
label_w_desc.align(lv.ALIGN.BOTTOM_MID, 0, -25)

# 3. 心率屏幕
screen_heart = lv.obj()
screen_heart.set_style_bg_color(lv.color_hex(0x000000), 0)

def init_screen_heart():
    if screen_heart.get_child_count() > 0: return
    
    label_h_title = lv.label(screen_heart)
    label_h_title.set_text("心率监测")
    label_h_title.add_style(style_title, 0)
    label_h_title.align(lv.ALIGN.TOP_MID, 0, 30)
    
    global label_h_val
    label_h_val = lv.label(screen_heart)
    label_h_val.set_text("75")
    label_h_val.add_style(style_value, 0)
    label_h_val.set_style_text_color(COLOR_HUAWEI_WARNING, 0) # 华为运动/健康红
    label_h_val.align(lv.ALIGN.CENTER, 0, -35)
    
    label_h_unit = lv.label(screen_heart)
    label_h_unit.set_text("BPM")
    label_h_unit.add_style(style_subtext, 0)
    label_h_unit.align_to(label_h_val, lv.ALIGN.OUT_RIGHT_BOTTOM, 5, -10)
    
    # 心电图 Chart
    global chart_ecg, ser_ecg
    chart_ecg = lv.chart(screen_heart)
    chart_ecg.set_size(200, 85) # 稍微加宽
    chart_ecg.align(lv.ALIGN.BOTTOM_MID, 0, -40)
    chart_ecg.set_type(lv.chart.TYPE.LINE)
    chart_ecg.set_update_mode(lv.chart.UPDATE_MODE.SHIFT)
    chart_ecg.set_point_count(60)
    chart_ecg.set_axis_range(lv.chart.AXIS.PRIMARY_Y, 0, 100)
    chart_ecg.set_style_size(0, 0, lv.PART.INDICATOR)
    chart_ecg.set_style_line_width(2, lv.PART.ITEMS)
    chart_ecg.set_style_bg_opa(0, 0)
    chart_ecg.set_style_border_opa(0, 0)
    ser_ecg = chart_ecg.add_series(COLOR_HUAWEI_WARNING, lv.chart.AXIS.PRIMARY_Y)
    gc.collect()

# 4. 运动屏幕
screen_sport = lv.obj()
screen_sport.set_style_bg_color(lv.color_hex(0x000000), 0)

def init_screen_sport():
    if screen_sport.get_child_count() > 0: return
    
    label_sport_title = lv.label(screen_sport)
    label_sport_title.set_text("运动训练")
    label_sport_title.add_style(style_title, 0)
    label_sport_title.align(lv.ALIGN.TOP_MID, 0, 30)
    
    global label_steps, label_calories, label_distance
    # 采用更整齐的网格感布局
    label_steps = lv.label(screen_sport)
    label_steps.set_text("步数: 0")
    label_steps.add_style(style_title, 0)
    label_steps.align(lv.ALIGN.CENTER, 0, -35)
    
    label_calories = lv.label(screen_sport)
    label_calories.set_text("消耗: 0 kcal")
    label_calories.add_style(style_subtext, 0)
    label_calories.align(lv.ALIGN.CENTER, 0, 0)
    
    label_distance = lv.label(screen_sport)
    label_distance.set_text("距离: 0.00 km")
    label_distance.add_style(style_subtext, 0)
    label_distance.align(lv.ALIGN.CENTER, 0, 30)
    
    btn_start_sport = lv.button(screen_sport)
    btn_start_sport.set_size(140, 42) # 华为风格大按钮
    btn_start_sport.add_style(style_btn_success, 0) # 使用成功绿色
    btn_start_sport.align(lv.ALIGN.BOTTOM_MID, 0, -25)
    btn_start_label = lv.label(btn_start_sport)
    btn_start_label.set_text("开始运动")
    btn_start_label.set_style_text_font(font_cn, 0)
    btn_start_label.center()
    btn_start_sport.add_event_cb(start_sport_event_cb, lv.EVENT.CLICKED, None)
    gc.collect()

# 5. 正在运动子页面
screen_sport_running = lv.obj()
screen_sport_running.set_style_bg_color(lv.color_hex(0x000000), 0)

def init_screen_sport_running():
    if screen_sport_running.get_child_count() > 0: return
    
    label_running_title = lv.label(screen_sport_running)
    label_running_title.set_text("正在跑步")
    label_running_title.add_style(style_title, 0)
    label_running_title.set_style_text_color(COLOR_HUAWEI_SUCCESS, 0)
    label_running_title.align(lv.ALIGN.TOP_MID, 0, 30)

    global label_duration
    label_duration = lv.label(screen_sport_running)
    label_duration.set_text("00:00")
    label_duration.add_style(style_value, 0)
    label_duration.align(lv.ALIGN.CENTER, 0, -10)

    # 停止按钮 (红色胶囊)
    btn_stop_sport = lv.button(screen_sport_running)
    btn_stop_sport.set_size(140, 42)
    btn_stop_sport.add_style(style_btn_warning, 0) # 使用警告红色
    btn_stop_sport.align(lv.ALIGN.BOTTOM_MID, 0, -35)
    btn_stop_label = lv.label(btn_stop_sport)
    btn_stop_label.set_text("结束运动")
    btn_stop_label.set_style_text_font(font_cn, 0)
    btn_stop_label.center()
    btn_stop_sport.add_event_cb(stop_sport_event_cb, lv.EVENT.CLICKED, None)
    gc.collect()

def start_sport_event_cb(e):
    global is_sporting, sport_duration, sport_steps, sport_calories, sport_distance
    is_sporting = True
    sport_duration = 0
    sport_steps = 0
    sport_calories = 0
    sport_distance = 0.0
    
    # 确保子页面已初始化
    init_screen_sport_running()
    
    label_duration.set_text("00:00")
    # 检查 UI 对象是否存在（由于延迟加载）
    if 'label_steps' in globals():
        label_steps.set_text("步数: 0")
        label_calories.set_text("消耗: 0 kcal")
        label_distance.set_text("距离: 0.00 km")
    lv.screen_load(screen_sport_running)

def stop_sport_event_cb(e):
    global is_sporting
    is_sporting = False
    lv.screen_load(screen_sport)

# 6. 汇率查询屏幕
screen_exchange = lv.obj()
screen_exchange.set_style_bg_color(lv.color_hex(0x000000), 0)

def init_screen_exchange():
    if screen_exchange.get_child_count() > 0: return
    
    label_exc_title = lv.label(screen_exchange)
    label_exc_title.set_text("汇率查询")
    label_exc_title.add_style(style_title, 0)
    label_exc_title.align(lv.ALIGN.TOP_MID, 0, 30)
    
    currency_options = "CNY\nUSD\nEUR\nJPY\nHKD\nGBP\nAUD\nCAD"
    
    global dd_from, dd_to, label_exc_status
    dd_from = lv.dropdown(screen_exchange)
    dd_from.set_options(currency_options)
    try:
        dd_from.set_symbol("S:img_caret_down_13x8_argb8888.png")
    except:
        pass
    dd_from.set_width(90)
    dd_from.align(lv.ALIGN.CENTER, -55, -20)
    dd_from.set_style_text_font(font_cn, 0)
    dd_from_list = dd_from.get_list()
    if dd_from_list: dd_from_list.set_style_text_font(font_cn, 0)
    
    dd_to = lv.dropdown(screen_exchange)
    dd_to.set_options(currency_options)
    try:
        dd_to.set_symbol("S:img_caret_down_13x8_argb8888.png")
    except:
        pass
    dd_to.set_selected(1) # 默认 USD
    dd_to.set_width(90)
    dd_to.align(lv.ALIGN.CENTER, 55, -20)
    dd_to.set_style_text_font(font_cn, 0)
    dd_to_list = dd_to.get_list()
    if dd_to_list: dd_to_list.set_style_text_font(font_cn, 0)
    
    label_arrow = lv.label(screen_exchange)
    label_arrow.set_text("→")
    label_arrow.add_style(style_title, 0)
    label_arrow.align(lv.ALIGN.CENTER, 0, -20)
    
    btn_exc_query = lv.button(screen_exchange)
    btn_exc_query.set_size(140, 42)
    btn_exc_query.add_style(style_btn, 0)
    btn_exc_query.align(lv.ALIGN.CENTER, 0, 40)
    btn_exc_lbl = lv.label(btn_exc_query)
    btn_exc_lbl.set_text("立即查询")
    btn_exc_lbl.set_style_text_font(font_cn, 0)
    btn_exc_lbl.center()
    btn_exc_query.add_event_cb(query_exchange_event_cb, lv.EVENT.CLICKED, None)
    
    label_exc_status = lv.label(screen_exchange)
    label_exc_status.set_text("")
    label_exc_status.add_style(style_subtext, 0)
    label_exc_status.set_style_text_color(lv.color_hex(0xFFD700), 0) # 金色提示
    label_exc_status.align(lv.ALIGN.BOTTOM_MID, 0, -20)
    gc.collect()

# 6.5 汇率结果屏幕
screen_exchange_result = lv.obj()
screen_exchange_result.set_style_bg_color(lv.color_hex(0x000000), 0)

def init_screen_exchange_result():
    if screen_exchange_result.get_child_count() > 0: return
    
    label_res_title = lv.label(screen_exchange_result)
    label_res_title.set_text("查询结果")
    label_res_title.add_style(style_title, 0)
    label_res_title.align(lv.ALIGN.TOP_MID, 0, 35)
    
    global label_res_val, label_res_rate
    label_res_val = lv.label(screen_exchange_result)
    label_res_val.set_text("")
    label_res_val.set_style_text_font(lv.font_montserrat_32, 0) # 调大结果显示
    label_res_val.set_style_text_color(COLOR_HUAWEI_HIGHLIGHT, 0)
    label_res_val.set_width(230)
    label_res_val.set_style_text_align(lv.TEXT_ALIGN.CENTER, 0)
    label_res_val.align(lv.ALIGN.CENTER, 0, -10)
    
    label_res_rate = lv.label(screen_exchange_result)
    label_res_rate.set_text("")
    label_res_rate.add_style(style_subtext, 0)
    label_res_rate.align(lv.ALIGN.CENTER, 0, 35)
    
    btn_res_back = lv.button(screen_exchange_result)
    btn_res_back.set_size(140, 42)
    btn_res_back.add_style(style_btn, 0)
    btn_res_back.align(lv.ALIGN.BOTTOM_MID, 0, -35)
    btn_res_back_lbl = lv.label(btn_res_back)
    btn_res_back_lbl.set_text("返回")
    btn_res_back_lbl.set_style_text_font(font_cn, 0)
    btn_res_back_lbl.center()
    btn_res_back.add_event_cb(back_to_exchange_cb, lv.EVENT.CLICKED, None)
    gc.collect()

def back_to_exchange_cb(e):
    lv.screen_load(screen_exchange)

def query_exchange_event_cb(e):
    # 获取选中的货币字符串 (增加缓冲区大小并检查)
    from_buf = " "*16
    dd_from.get_selected_str(from_buf, len(from_buf))
    from_coin = from_buf.strip()
    
    to_buf = " "*16
    dd_to.get_selected_str(to_buf, len(to_buf))
    to_coin = to_buf.strip()
    
    # 立即清理缓冲区字符串
    del from_buf
    del to_buf
    gc.collect()
    
    # 调试打印，检查获取到的货币代码
    print("Debug - From: [{}], To: [{}]".format(from_coin, to_coin))
    
    if not from_coin or not to_coin:
        label_exc_status.set_text("错误: 货币选择无效")
        return
    
    label_exc_status.set_text("正在查询...")
    
    url = "https://apis.tianapi.com/fxrate/index"
    api_key = huilv_aip_key
    # POST 参数使用 x-www-form-urlencoded 格式
    params = "key={}&money=1&fromcoin={}&tocoin={}".format(api_key, from_coin, to_coin)
    headers = {'Content-type': 'application/x-www-form-urlencoded'}
    
    print("Exchange API Request: {} data={}".format(url, params))
    
    if connect_wifi():
        retry_count = 2
        success = False
        while retry_count >= 0 and not success:
            try:
                gc.collect() # 请求前清理内存
                res = urequests.post(url, data=params, headers=headers, timeout=10)
                print("Response Status: {} (Retries left: {})".format(res.status_code, retry_count))
                
                # 分步解析以减少内存峰值
                data_all = res.json()
                res.close()
                
                if data_all.get("code") == 200:
                    result = data_all.get("result")
                    if result:
                        # 兼容不同版本的 API 返回结构
                        rate = result.get("exchange")
                        val = result.get("result")
                        
                        if rate is None: rate = result.get("money")
                        if val is None: val = result.get("money")
                        
                        # 主显示：1 CNY = 0.1437 USD
                        main_text = "1 {} = {} {}".format(from_coin, val, to_coin)
                        # 副显示：汇率: 0.1437
                        rate_text = "汇率: {}".format(rate)
                        
                        # 确保结果页面已初始化
                        init_screen_exchange_result()
                        
                        # 分别设置到两个 Label
                        label_res_val.set_text(main_text)
                        label_res_rate.set_text(rate_text)
                        
                        label_exc_status.set_text("") # 清空查询页面的状态
                        lv.screen_load(screen_exchange_result)
                        success = True
                    else:
                        label_exc_status.set_text("未获取到汇率结果")
                        success = True 
                else:
                    label_exc_status.set_text("失败: {}".format(data_all.get('msg', '未知错误')))
                    success = True 
                
                # 显式清理
                del data_all
                gc.collect()
            except Exception as ex:
                print("Exchange Query Error: {} (Retries left: {})".format(ex, retry_count))
                retry_count -= 1
                if retry_count < 0:
                    label_exc_status.set_text("网络连接中断\n请重试")
                else:
                    time.sleep(1) # 等待一秒后重试
                gc.collect()
    else:
        label_exc_status.set_text("请先连接 WiFi")

# 7. 二维码屏幕 (华为支付样式)
screen_qr = lv.obj()
screen_qr.set_style_bg_color(lv.color_hex(0x000000), 0)

def init_screen_qr():
    if screen_qr.get_child_count() > 0: return
    
    qr = lv.qrcode(screen_qr)
    qr.set_size(150)
    qr.set_dark_color(lv.color_hex(0x000000))
    qr.set_light_color(lv.color_hex(0xFFFFFF))
    qr_data = "https://lvgl.io"
    qr.update(qr_data, len(qr_data))
    qr.align(lv.ALIGN.CENTER, 0, -20)
    
    label_qr = lv.label(screen_qr)
    label_qr.set_text("扫码支付")
    label_qr.add_style(style_title, 0)
    label_qr.align(lv.ALIGN.BOTTOM_MID, 0, -25)
    gc.collect()

# 7.5 豆包对话屏幕
screen_doubao = lv.obj()
screen_doubao.set_style_bg_color(lv.color_hex(0xFFFFFF), 0) # 背景设为白色

def init_screen_doubao():
    if screen_doubao.get_child_count() > 0: return
    
    label_doubao_title = lv.label(screen_doubao)
    label_doubao_title.set_text("豆包助手")
    label_doubao_title.add_style(style_title, 0)
    label_doubao_title.set_style_text_color(lv.color_hex(0x000000), 0) # 白色背景下文字设为黑色
    label_doubao_title.align(lv.ALIGN.TOP_MID, 0, 15) # 向上移动 10 (原 25)
    
    img_doubao_logo = lv.image(screen_doubao)
    img_doubao_logo.set_src("S:logo-icon-white-bg.bmp")
    img_doubao_logo.align(lv.ALIGN.CENTER, 0, -20) # 向上移动 10 (原 -10)
    
    global btn_mic, is_mic_on
    is_mic_on = False
    
    btn_mic = lv.image(screen_doubao)
    btn_mic.set_src("S:mic-off.bmp")
    btn_mic.align(lv.ALIGN.BOTTOM_MID, 0, -10) # 向下移动 20 (原 -30)
    btn_mic.add_flag(lv.obj.FLAG.CLICKABLE)
    
    def mic_event_cb(e):
        global is_mic_on
        is_mic_on = not is_mic_on
        if is_mic_on:
            btn_mic.set_src("S:mic.bmp")
        else:
            btn_mic.set_src("S:mic-off.bmp")
        print(f"Microphone toggled: {'ON' if is_mic_on else 'OFF'}")
        
    btn_mic.add_event_cb(mic_event_cb, lv.EVENT.CLICKED, None)
    gc.collect()

# 8. 系统信息屏幕
screen_sys = lv.obj()
screen_sys.set_style_bg_color(lv.color_hex(0x000000), 0)

def init_screen_sys():
    if screen_sys.get_child_count() > 0: return
    
    label_sys_title = lv.label(screen_sys)
    label_sys_title.set_text("系统信息")
    label_sys_title.add_style(style_title, 0)
    label_sys_title.align(lv.ALIGN.TOP_MID, 0, 30)

    global label_uptime, label_mem
    label_uptime = lv.label(screen_sys)
    label_uptime.add_style(style_subtext, 0)
    label_uptime.align(lv.ALIGN.CENTER, 0, -15)

    label_mem = lv.label(screen_sys)
    label_mem.add_style(style_subtext, 0)
    label_mem.align(lv.ALIGN.CENTER, 0, 15)

    # 返回按钮
    btn_back = lv.button(screen_sys)
    btn_back.set_size(100, 40)
    btn_back.add_style(style_btn, 0)
    btn_back.align(lv.ALIGN.BOTTOM_MID, 0, -20)
    lbl_back = lv.label(btn_back)
    lbl_back.set_text("返回")
    lbl_back.set_style_text_font(font_cn, 0)
    lbl_back.center()

    def back_event_cb(e):
        lv.screen_load(screen_settings)

    btn_back.add_event_cb(back_event_cb, lv.EVENT.CLICKED, None)
    gc.collect()

# 9. 设置菜单主屏幕
screen_settings = lv.obj()
screen_settings.set_style_bg_color(lv.color_hex(0x000000), 0)

# 子页面定义
screen_set_region = lv.obj()
screen_set_region.set_style_bg_color(lv.color_hex(0x000000), 0)
screen_set_brightness = lv.obj()
screen_set_brightness.set_style_bg_color(lv.color_hex(0x000000), 0)

def create_menu_item(parent, text, y_pos, click_cb):
    btn = lv.button(parent)
    btn.set_size(180, 45) # 减小宽度，留出边缘滑动区域 (240 - 180 = 60px, 左右各 30px)
    btn.align(lv.ALIGN.TOP_MID, 0, y_pos)
    btn.set_style_bg_opa(0, 0)
    btn.set_style_border_width(0, 0)
    btn.set_style_shadow_width(0, 0)
    
    # 添加按下时的反馈效果
    btn.set_style_bg_color(lv.color_hex(0x333333), lv.STATE.PRESSED)
    btn.set_style_bg_opa(100, lv.STATE.PRESSED)
    
    lbl = lv.label(btn)
    lbl.set_text(text)
    lbl.set_style_text_font(font_cn, 0)
    lbl.align(lv.ALIGN.LEFT_MID, 0, 0)
    
    arrow = lv.label(btn)
    arrow.set_text(">")
    arrow.set_style_text_color(COLOR_HUAWEI_SUBTEXT, 0)
    arrow.align(lv.ALIGN.RIGHT_MID, 0, 0)
    
    # 改为长按触发，防止滑动切换屏幕时误触
    btn.add_event_cb(click_cb, lv.EVENT.LONG_PRESSED, None)
    return btn

def init_screen_settings():
    if screen_settings.get_child_count() > 0: return
    
    label_set_title = lv.label(screen_settings)
    label_set_title.set_text("系统设置")
    label_set_title.add_style(style_title, 0)
    label_set_title.align(lv.ALIGN.TOP_MID, 0, 20)

    # 菜单项
    create_menu_item(screen_settings, "城市设置", 65, lambda e: (init_screen_set_region(), lv.screen_load(screen_set_region)))
    create_menu_item(screen_settings, "亮度设置", 115, lambda e: (init_screen_set_brightness(), lv.screen_load(screen_set_brightness)))
    create_menu_item(screen_settings, "系统信息", 165, lambda e: (init_screen_sys(), lv.screen_load(screen_sys)))
    gc.collect()

# 9.1 区域设置子页面
def init_screen_set_region():
    if screen_set_region.get_child_count() > 0: return
    
    label_title = lv.label(screen_set_region)
    label_title.set_text("城市设置")
    label_title.add_style(style_title, 0)
    label_title.align(lv.ALIGN.TOP_MID, 0, 30)

    global dd_city
    dd_city = lv.dropdown(screen_set_region)
    dd_city.set_options("\n".join([city["name"] for city in CHINESE_CITIES]))
    dd_city.set_style_text_font(font_cn, 0)
    
    # 设置下拉菜单箭头为图片
    try:
        dd_city.set_symbol("S:img_caret_down_13x8_argb8888.png")
    except:
        pass
        
    dd_city.set_width(160)
    dd_city.align(lv.ALIGN.CENTER, 0, -20)
    
    dd_list = dd_city.get_list()
    if dd_list: dd_list.set_style_text_font(font_cn, 0)
    
    for i, city in enumerate(CHINESE_CITIES):
        if city["id"] == CITY:
            dd_city.set_selected(i)
            break

    btn_save = lv.button(screen_set_region)
    btn_save.set_size(120, 40)
    btn_save.add_style(style_btn, 0)
    btn_save.align(lv.ALIGN.BOTTOM_MID, 0, -20)
    lbl_save = lv.label(btn_save)
    lbl_save.set_text("保存返回")
    lbl_save.set_style_text_font(font_cn, 0)
    lbl_save.center()

    def save_region_cb(e):
        global CITY, WEATHER_URL
        selected_idx = dd_city.get_selected()
        CITY = CHINESE_CITIES[selected_idx]["id"]
        WEATHER_URL = f"{config.WEATHER_API_URL}?key={WEATHER_KEY}&location={CITY}&language=zh-Hans&unit=c"
        label_w_city.set_text(CHINESE_CITIES[selected_idx]["name"])
        update_weather_cb(None)
        lv.screen_load(screen_settings)

    btn_save.add_event_cb(save_region_cb, lv.EVENT.CLICKED, None)
    gc.collect()

# 9.2 亮度设置子页面
def init_screen_set_brightness():
    if screen_set_brightness.get_child_count() > 0: return
    
    label_title = lv.label(screen_set_brightness)
    label_title.set_text("亮度设置")
    label_title.add_style(style_title, 0)
    label_title.align(lv.ALIGN.TOP_MID, 0, 30)

    global slider_brightness, label_brightness_value
    label_brightness_value = lv.label(screen_set_brightness)
    label_brightness_value.set_text(str(current_brightness))
    label_brightness_value.add_style(style_subtext, 0)
    label_brightness_value.set_style_text_color(COLOR_HUAWEI_HIGHLIGHT, 0)
    label_brightness_value.align(lv.ALIGN.CENTER, 0, -10)

    slider_brightness = lv.slider(screen_set_brightness)
    slider_brightness.set_range(10, 100)
    slider_brightness.set_value(current_brightness, False)
    slider_brightness.set_width(160)
    slider_brightness.set_style_bg_color(COLOR_HUAWEI_HIGHLIGHT, lv.PART.INDICATOR)
    slider_brightness.set_style_bg_color(COLOR_HUAWEI_HIGHLIGHT, lv.PART.KNOB)
    slider_brightness.align(lv.ALIGN.CENTER, 0, 25)

    def slider_event_cb(e):
        label_brightness_value.set_text(str(slider_brightness.get_value()))
    slider_brightness.add_event_cb(slider_event_cb, lv.EVENT.VALUE_CHANGED, None)

    btn_save = lv.button(screen_set_brightness)
    btn_save.set_size(120, 40)
    btn_save.add_style(style_btn, 0)
    btn_save.align(lv.ALIGN.BOTTOM_MID, 0, -20)
    lbl_save = lv.label(btn_save)
    lbl_save.set_text("保存返回")
    lbl_save.set_style_text_font(font_cn, 0)
    lbl_save.center()

    def save_bright_cb(e):
        global current_brightness
        current_brightness = slider_brightness.get_value()
        set_screen_brightness(current_brightness)
        lv.screen_load(screen_settings)

    btn_save.add_event_cb(save_bright_cb, lv.EVENT.CLICKED, None)
    gc.collect()

# --- LED 控制页面 ---
screen_led = lv.obj()
screen_led.set_style_bg_color(lv.color_hex(0x000000), 0)

def dd_led_mode_event_cb(e):
    global current_led_mode
    current_led_mode = dd_led_mode.get_selected()

def init_screen_led():
    if screen_led.get_child_count() > 0: return
    
    label_led_title = lv.label(screen_led)
    label_led_title.set_text("呼吸灯设置")
    label_led_title.add_style(style_title, 0)
    label_led_title.align(lv.ALIGN.TOP_MID, 0, 30)
    
    global rect_preview
    rect_preview = lv.obj(screen_led)
    rect_preview.set_size(60, 30)
    rect_preview.align(lv.ALIGN.TOP_MID, -45, 55)
    rect_preview.set_style_bg_color(lv.color_hex(0x000000), 0)
    rect_preview.set_style_border_color(lv.color_hex(0xFFFFFF), 0)
    rect_preview.set_style_border_width(2, 0)
    rect_preview.set_style_radius(10, 0)
    
    global dd_led_mode
    dd_led_mode = lv.dropdown(screen_led)
    dd_led_mode.set_options("常亮\n爆闪\n呼吸\n彩虹\n渐进")
    try:
        dd_led_mode.set_symbol("S:img_caret_down_13x8_argb8888.png")
    except:
        pass
    dd_led_mode.set_size(100, 32)
    dd_led_mode.align(lv.ALIGN.TOP_MID, 45, 54)
    dd_led_mode.set_style_text_font(font_cn, 0)
    dd_led_mode_list = dd_led_mode.get_list()
    if dd_led_mode_list: dd_led_mode_list.set_style_text_font(font_cn, 0)
    
    global slider_led_r, label_val_r, slider_led_g, label_val_g, slider_led_b, label_val_b
    slider_led_r, label_val_r = create_led_slider(-15, 0xFF3B30, "R") # 红色调优
    slider_led_g, label_val_g = create_led_slider(15, 0x34C759, "G") # 绿色调优
    slider_led_b, label_val_b = create_led_slider(45, 0x007AFF, "B") # 蓝色调优

    dd_led_mode.add_event_cb(dd_led_mode_event_cb, lv.EVENT.VALUE_CHANGED, None)
    slider_led_r.add_event_cb(sliders_led_event_cb, lv.EVENT.VALUE_CHANGED, None)
    slider_led_g.add_event_cb(sliders_led_event_cb, lv.EVENT.VALUE_CHANGED, None)
    slider_led_b.add_event_cb(sliders_led_event_cb, lv.EVENT.VALUE_CHANGED, None)

    slider_led_r.set_value(active_led_r, False)
    slider_led_g.set_value(active_led_g, False)
    slider_led_b.set_value(active_led_b, False)
    label_val_r.set_text(str(active_led_r))
    label_val_g.set_text(str(active_led_g))
    label_val_b.set_text(str(active_led_b))
    rect_preview.set_style_bg_color(lv.color_make(active_led_r, active_led_g, active_led_b), 0)
    dd_led_mode.set_selected(active_led_mode)

    cont_btns = lv.obj(screen_led)
    cont_btns.set_size(220, 50)
    cont_btns.align(lv.ALIGN.BOTTOM_MID, 0, -20)
    cont_btns.set_style_bg_opa(0, 0)
    cont_btns.set_style_border_opa(0, 0)
    cont_btns.remove_flag(lv.obj.FLAG.SCROLLABLE)

    btn_led_ok = lv.button(cont_btns)
    btn_led_ok.set_size(80, 36)
    btn_led_ok.add_style(style_btn_success, 0)
    btn_led_ok.align(lv.ALIGN.LEFT_MID, 10, 0)
    btn_led_ok_lbl = lv.label(btn_led_ok)
    btn_led_ok_lbl.set_text("应用")
    btn_led_ok_lbl.set_style_text_font(font_cn, 0)
    btn_led_ok_lbl.center()
    btn_led_ok.add_event_cb(led_ok_event_cb, lv.EVENT.CLICKED, None)

    btn_led_close = lv.button(cont_btns)
    btn_led_close.set_size(80, 36)
    btn_led_close.add_style(style_btn_warning, 0)
    btn_led_close.align(lv.ALIGN.RIGHT_MID, -10, 0)
    btn_led_close_lbl = lv.label(btn_led_close)
    btn_led_close_lbl.set_text("关闭")
    btn_led_close_lbl.set_style_text_font(font_cn, 0)
    btn_led_close_lbl.center()
    btn_led_close.add_event_cb(led_close_event_cb, lv.EVENT.CLICKED, None)
    gc.collect()

# RGB 滑块辅助函数
def create_led_slider(y_offset, color_hex, label_text):
    cont = lv.obj(screen_led)
    cont.set_size(180, 26) # 稍微增加容器宽度以容纳数值
    cont.align(lv.ALIGN.CENTER, 0, y_offset)
    cont.set_style_bg_opa(0, 0)
    cont.set_style_border_opa(0, 0)
    cont.set_style_pad_all(0, 0)
    cont.remove_flag(lv.obj.FLAG.SCROLLABLE)
    
    lbl = lv.label(cont)
    lbl.set_text(label_text)
    lbl.set_style_text_color(lv.color_hex(0xFFFFFF), 0)
    lbl.align(lv.ALIGN.LEFT_MID, 0, 0)
    
    slider = lv.slider(cont)
    slider.set_range(0, 255)
    slider.set_size(110, 8) # 减小滑块宽度
    slider.align(lv.ALIGN.CENTER, 5, 0)
    slider.set_style_bg_color(lv.color_hex(color_hex), lv.PART.INDICATOR)
    slider.set_style_bg_color(lv.color_hex(color_hex), lv.PART.KNOB)
    
    val_lbl = lv.label(cont)
    val_lbl.set_text("0")
    val_lbl.set_style_text_color(lv.color_hex(0xAAAAAA), 0)
    val_lbl.align(lv.ALIGN.RIGHT_MID, 0, 0)
    
    return slider, val_lbl

def sliders_led_event_cb(e):
    r = slider_led_r.get_value()
    g = slider_led_g.get_value()
    b = slider_led_b.get_value()
    
    # 更新数值显示
    label_val_r.set_text(str(r))
    label_val_g.set_text(str(g))
    label_val_b.set_text(str(b))
    
    # 更新预览框颜色
    rect_preview.set_style_bg_color(lv.color_make(r, g, b), 0)

def led_ok_event_cb(e):
    global active_led_r, active_led_g, active_led_b, active_led_mode, led_effect_step
    if np_led:
        # 按下确认后，将当前滑块和下拉框的值应用到实际运行变量中
        active_led_r = slider_led_r.get_value()
        active_led_g = slider_led_g.get_value()
        active_led_b = slider_led_b.get_value()
        active_led_mode = current_led_mode
        led_effect_step = 0 # 重置步进以从头开始效果
        print(f"WS2812 Settings applied: Mode {active_led_mode}, Color ({active_led_r}, {active_led_g}, {active_led_b})")
    else:
        print("WS2812 not initialized")

def led_close_event_cb(e):
    global active_led_r, active_led_g, active_led_b, active_led_mode
    # 按下关闭后，熄灭灯（通过将运行变量设为0）
    if np_led:
        active_led_r = 0
        active_led_g = 0
        active_led_b = 0
        active_led_mode = 0 # 设为常亮模式但颜色为0
        print("WS2812 turned off")

# ===== 初始化屏幕列表 =====
# 移除了 screen_sys，它现在通过设置菜单进入
screens = [screen_time, screen_weather, screen_heart, screen_sport, screen_exchange, screen_led, screen_qr, screen_doubao, screen_settings]

# ===== 逻辑处理 =====

def update_time_cb(t):
    try:
        # RTC 存储的是北京时间 (UTC+8)
        # 我们先转回 UTC，再根据当前选择的时区偏移计算
        now_ticks = time.time()
        utc_ticks = now_ticks - TIMEZONES[0]['offset']
        local_ticks = utc_ticks + TIMEZONES[current_tz_idx]['offset']
        
        now = time.localtime(local_ticks)
        label_clock.set_text("{:02d}:{:02d}:{:02d}".format(now[3], now[4], now[5]))
        label_date.set_text("{:04d}-{:02d}-{:02d}".format(now[0], now[1], now[2]))
        label_tz.set_text(TIMEZONES[current_tz_idx]["name"])
    except Exception as e:
        print(f"Time update error: {e}")

def update_weather_cb(t):
    global last_weather_code
    try:
        weather = fetch_weather_data()
        if weather:
            label_w_temp.set_text(f"{weather['temperature']}°C")
            label_w_desc.set_text(weather['text'])
            
            code = weather['code']
            # 如果天气代码没变，不需要重新加载图标
            if code == last_weather_code:
                return
            
            # 优化：在加载新图标前手动触发 GC，并检查文件是否存在
            gc.collect()
            
            # 使用文件系统路径直接设置图片源，减少 MicroPython 内存占用
            try:
                icon_path = f"S:weather_incons/{code}@1x.png"
                img_w_icon.set_src(icon_path)
                last_weather_code = code
                print(f"Weather icon updated: {icon_path}")
            except Exception as e:
                print(f"Icon update error: {e}")
                try:
                    img_w_icon.set_src("S:weather_incons/99@1x.png")
                except:
                    pass
            
            # 强制释放缓存中的图像数据 (LVGL v9 绑定可能不支持 image_cache_drop)
            try:
                # 尝试 v9 可能支持的缓存清理方式
                if hasattr(lv, 'cache_drop_all'):
                    lv.cache_drop_all(None)
            except:
                pass
            gc.collect() 
        else:
            label_w_desc.set_text("离线")
            gc.collect()
    except Exception as e:
        print(f"Weather update error: {e}")

start_ticks = time.ticks_ms()
def update_sys_cb(t):
    # 仅在系统信息页面激活时更新
    if lv.screen_active() != screen_sys:
        return
        
    try:
        uptime_s = time.ticks_diff(time.ticks_ms(), start_ticks) // 1000
        label_uptime.set_text("运行时间: {}s".format(uptime_s))
        gc.collect()
        mem_free = gc.mem_free()
        mem_alloc = gc.mem_alloc()
        label_mem.set_text("内存剩余: {} KB".format(mem_free // 1024))
    except Exception as e:
        print(f"System update error: {e}")

def update_heart_cb(t):
    # 仅在心率页面激活时更新
    if lv.screen_active() != screen_heart:
        return

    try:
        # 模拟心率数值 (60-100之间小幅波动)
        current_val = int(label_h_val.get_text())
        new_val = current_val + random.randint(-2, 2)
        if new_val < 60: new_val = 60
        if new_val > 100: new_val = 100
        label_h_val.set_text(str(new_val))
        
        # 模拟心电图波动
        if random.random() > 0.8: # 20% 概率产生波动
            ecg_val = random.randint(40, 90)
        else:
            ecg_val = random.randint(20, 30)
        
        chart_ecg.set_next_value(ser_ecg, ecg_val)
    except Exception as e:
        print(f"Heart rate update error: {e}")

def update_sport_cb(t):
    global sport_steps, sport_calories, sport_distance, sport_duration
    if not is_sporting:
        return
        
    sport_duration += 1
    # 模拟步数增加 (每秒增加 1-3 步)
    sport_steps += random.randint(1, 3)
    # 模拟消耗 (大约 20步 1 kcal)
    sport_calories = sport_steps // 20
    # 模拟距离 (大约 1300步 1 km)
    sport_distance = sport_steps / 1300.0
    
    # 仅在页面激活且对象存在时更新 UI
    try:
        active_screen = lv.screen_active()
        # 更新正在运动页面的时长
        if active_screen == screen_sport_running and 'label_duration' in globals():
            mins = sport_duration // 60
            secs = sport_duration % 60
            label_duration.set_text("{:02d}:{:02d}".format(mins, secs))
        
        # 更新运动数据主页面的数值
        if active_screen == screen_sport and 'label_steps' in globals():
            label_steps.set_text("步数: {}".format(sport_steps))
            label_calories.set_text("消耗: {} kcal".format(sport_calories))
            label_distance.set_text("距离: {:.2f} km".format(sport_distance))
    except Exception as e:
        print(f"Sport update error: {e}")

def hsv_to_rgb(h, s, v):
    if s == 0: return v, v, v
    i = int(h * 6.0)
    f = (h * 6.0) - i
    p = v * (1.0 - s)
    q = v * (1.0 - s * f)
    t = v * (1.0 - s * (1.0 - f))
    i %= 6
    if i == 0: return int(v*255), int(t*255), int(p*255)
    if i == 1: return int(q*255), int(v*255), int(p*255)
    if i == 2: return int(p*255), int(v*255), int(t*255)
    if i == 3: return int(p*255), int(q*255), int(v*255)
    if i == 4: return int(t*255), int(p*255), int(v*255)
    if i == 5: return int(v*255), int(p*255), int(q*255)
    return 0, 0, 0

def update_led_effect_cb(t):
    global led_effect_step
    if not np_led: return
    
    # LED 效果更新不需要检查 UI 激活状态，因为它是硬件输出
    # 但如果是从 UI 读取参数，需要确保参数有效
    try:
        # 使用实际生效的变量，而不是直接读取滑块
        r_base = active_led_r
        g_base = active_led_g
        b_base = active_led_b
        
        if active_led_mode == 0: # 常亮
            np_led[0] = (r_base, g_base, b_base)
        elif active_led_mode == 1: # 爆闪
            if led_effect_step % 2 == 0:
                np_led[0] = (r_base, g_base, b_base)
            else:
                np_led[0] = (0, 0, 0)
            led_effect_step += 1
        elif active_led_mode == 2: # 呼吸
            # 使用正弦函数实现呼吸效果
            brightness = (math.sin(led_effect_step * 0.2) + 1) / 2
            np_led[0] = (int(r_base * brightness), int(g_base * brightness), int(b_base * brightness))
            led_effect_step += 1
        elif active_led_mode == 3: # 彩虹
            # 忽略基础颜色，循环色调
            h = (led_effect_step % 100) / 100.0
            rgb = hsv_to_rgb(h, 1.0, 1.0)
            np_led[0] = rgb
            led_effect_step += 1
        elif active_led_mode == 4: # 渐进
            # 颜色由暗变亮再变暗，循环
            factor = (led_effect_step % 50) / 50.0
            if (led_effect_step // 50) % 2 == 1:
                factor = 1.0 - factor
            np_led[0] = (int(r_base * factor), int(g_base * factor), int(b_base * factor))
            led_effect_step += 1
        
        np_led.write()
    except Exception as e:
        print(f"LED effect update error: {e}")

# 创建定时器
timer_time = lv.timer_create(update_time_cb, 500, None) # 降低刷新频率到 500ms
timer_weather = lv.timer_create(update_weather_cb, 3600000, None) # 每小时更新一次
timer_sys = lv.timer_create(update_sys_cb, 2000, None) # 降低到 2000ms，系统信息不需要频繁更新
timer_heart = lv.timer_create(update_heart_cb, 1000, None) # 降低到 1000ms
timer_sport = lv.timer_create(update_sport_cb, 2000, None) # 降低到 2000ms
timer_led = lv.timer_create(update_led_effect_cb, 200, None) # 降低到 200ms

def switch_screen(direction):
    global current_screen_idx, is_mic_on
    
    # 记录旧页面，用于后续清理
    old_screen_idx = current_screen_idx
    
    # 如果当前页面是豆包页面，且即将切走，则重置 mic 状态
    if screens[current_screen_idx] == screen_doubao:
        if 'is_mic_on' in globals() and is_mic_on:
            is_mic_on = False
            if 'btn_mic' in globals():
                btn_mic.set_src("S:mic-off.bmp")
                print("豆包页面退出：麦克风状态已重置为 OFF")

    if direction == "next":
        current_screen_idx = (current_screen_idx + 1) % len(screens)
    elif direction == "prev":
        current_screen_idx = (current_screen_idx - 1) % len(screens)
    
    # 获取目标屏幕对象
    target_screen = screens[current_screen_idx]
    
    # 延迟加载逻辑
    if target_screen == screen_heart: init_screen_heart()
    elif target_screen == screen_sport: init_screen_sport()
    elif target_screen == screen_exchange: init_screen_exchange()
    elif target_screen == screen_exchange_result: init_screen_exchange_result()
    elif target_screen == screen_led: init_screen_led()
    elif target_screen == screen_qr: init_screen_qr()
    elif target_screen == screen_doubao: init_screen_doubao()
    elif target_screen == screen_sys: init_screen_sys()
    elif target_screen == screen_settings: init_screen_settings()
    
    lv.screen_load(target_screen)
    
    # --- 架构优化：动态卸载旧页面 ---
    # 时间页面和天气页面通常保持常驻，其它页面切走时自动清理子对象
    old_screen = screens[old_screen_idx]
    if old_screen not in [screen_time, screen_weather, screen_settings]:
        # 延迟一点清理，确保切换动画完成，且只有在页面不再活跃时才清理
        def clean_old_screen_cb(t):
            # 只有当旧页面确实不再是当前活动页面时，才进行清理
            if lv.screen_active() != old_screen and hasattr(old_screen, 'get_child_count') and old_screen.get_child_count() > 0:
                old_screen.clean()
                print(f"Memory Cleanup: Screen {old_screen_idx} unloaded")
                gc.collect()
            if t: t.delete() # 执行完后删除定时器

        # 修复：某些固件版本中 timer_create_basic 可能不支持链式调用
        try:
            cleanup_timer = lv.timer_create(clean_old_screen_cb, 1000, None)
            cleanup_timer.set_repeat_count(1)
        except Exception as e:
            print(f"Cleanup timer creation failed: {e}")
            # 如果定时器创建失败，直接手动触发一次 GC
            gc.collect()
    else:
        gc.collect() 

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
loop_count = 0
while True:
    try:
        lv.tick_inc(5)
        check_gesture()
        lv.task_handler()
        time.sleep_ms(5)
        
        # 每 50 次循环（约 0.25 秒）进行一次轻量级 GC
        loop_count += 1
        if loop_count >= 50:
            gc.collect()
            loop_count = 0
            
        # 激进内存回收：如果剩余内存过低，强制深度清理
        if gc.mem_free() < 16384: # 低于 16KB
            gc.collect()
            
    except MemoryError:
        print("CRITICAL: Memory low, performing emergency GC")

        gc.collect()

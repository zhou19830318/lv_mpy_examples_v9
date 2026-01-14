import lvgl as lv
import time
import gc
import machine
import network
import urequests
import json
import ntptime
import fs_driver
import random # 用于模拟心率数据，实际数据可以通过传感器获取的数据进行传递
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

# ===== 运动数据状态 =====
sport_steps = 0
sport_calories = 0
sport_distance = 0.0
sport_duration = 0 # 秒
is_sporting = False

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

# 3. 心率屏幕
screen_heart = lv.obj()
screen_heart.set_style_bg_color(lv.color_hex(0x000000), 0)

label_h_title = lv.label(screen_heart)
label_h_title.set_text("心率监测")
label_h_title.set_style_text_font(font_cn, 0)
label_h_title.align(lv.ALIGN.TOP_MID, 0, 25)

label_h_val = lv.label(screen_heart)
label_h_val.set_text("75")
label_h_val.set_style_text_font(lv.font_montserrat_48, 0)
label_h_val.set_style_text_color(lv.palette_main(lv.PALETTE.RED), 0)
label_h_val.align(lv.ALIGN.CENTER, 0, -35)

label_h_unit = lv.label(screen_heart)
label_h_unit.set_text("BPM")
label_h_unit.set_style_text_font(lv.font_montserrat_16, 0)
label_h_unit.set_style_text_color(lv.color_hex(0xAAAAAA), 0)
label_h_unit.align_to(label_h_val, lv.ALIGN.OUT_RIGHT_BOTTOM, 5, -10)

# 心电图 Chart
chart_ecg = lv.chart(screen_heart)
chart_ecg.set_size(180, 80)
chart_ecg.align(lv.ALIGN.BOTTOM_MID, 0, -45)
chart_ecg.set_type(lv.chart.TYPE.LINE)
chart_ecg.set_update_mode(lv.chart.UPDATE_MODE.SHIFT)
chart_ecg.set_point_count(50)
chart_ecg.set_axis_range(lv.chart.AXIS.PRIMARY_Y, 0, 100)
# 隐藏点，只显示线
chart_ecg.set_style_size(0, 0, lv.PART.INDICATOR)
chart_ecg.set_style_line_width(2, lv.PART.ITEMS)

ser_ecg = chart_ecg.add_series(lv.palette_main(lv.PALETTE.RED), lv.chart.AXIS.PRIMARY_Y)

# 4. 运动屏幕
screen_sport = lv.obj()
screen_sport.set_style_bg_color(lv.color_hex(0x000000), 0)

label_sport_title = lv.label(screen_sport)
label_sport_title.set_text("运动数据")
label_sport_title.set_style_text_font(font_cn, 0)
label_sport_title.align(lv.ALIGN.TOP_MID, 0, 20)

# 步数
label_steps = lv.label(screen_sport)
label_steps.set_text("步数: 0")
label_steps.set_style_text_font(font_cn, 0)
label_steps.align(lv.ALIGN.CENTER, 0, -30)

# 卡路里
label_calories = lv.label(screen_sport)
label_calories.set_text("消耗: 0 kcal")
label_calories.set_style_text_font(font_cn, 0)
label_calories.align(lv.ALIGN.CENTER, 0, 0)

# 距离
label_distance = lv.label(screen_sport)
label_distance.set_text("距离: 0.00 km")
label_distance.set_style_text_font(font_cn, 0)
label_distance.align(lv.ALIGN.CENTER, 0, 30)

# 开始运动按钮
btn_start_sport = lv.button(screen_sport)
btn_start_sport.set_size(120, 40)
btn_start_sport.align(lv.ALIGN.BOTTOM_MID, 0, -20)
btn_start_label = lv.label(btn_start_sport)
btn_start_label.set_text("开始运动")
btn_start_label.set_style_text_font(font_cn, 0)
btn_start_label.set_style_text_color(lv.color_hex(0x000000), 0)
btn_start_label.center()

# 5. 正在运动子页面
screen_sport_running = lv.obj()
screen_sport_running.set_style_bg_color(lv.color_hex(0x000000), 0)

label_running_title = lv.label(screen_sport_running)
label_running_title.set_text("正在跑步")
label_running_title.set_style_text_font(font_cn, 0)
label_running_title.set_style_text_color(lv.palette_main(lv.PALETTE.GREEN), 0)
label_running_title.align(lv.ALIGN.TOP_MID, 0, 40)

label_duration = lv.label(screen_sport_running)
label_duration.set_text("时长: 00:00")
label_duration.set_style_text_font(font_cn, 0)
label_duration.align(lv.ALIGN.CENTER, 0, 0)

# 停止按钮
btn_stop_sport = lv.button(screen_sport_running)
btn_stop_sport.set_size(100, 40)
btn_stop_sport.align(lv.ALIGN.BOTTOM_MID, 0, -40)
btn_stop_sport.set_style_bg_color(lv.palette_main(lv.PALETTE.RED), 0)
btn_stop_label = lv.label(btn_stop_sport)
btn_stop_label.set_text("停止")
btn_stop_label.set_style_text_font(font_cn, 0)
btn_stop_label.set_style_text_color(lv.color_hex(0xFFFFFF), 0)
btn_stop_label.center()

def start_sport_event_cb(e):
    global is_sporting, sport_duration, sport_steps, sport_calories, sport_distance
    is_sporting = True
    sport_duration = 0
    sport_steps = 0
    sport_calories = 0
    sport_distance = 0.0
    label_duration.set_text("时长: 00:00")
    label_steps.set_text("步数: 0")
    label_calories.set_text("消耗: 0 kcal")
    label_distance.set_text("距离: 0.00 km")
    lv.screen_load(screen_sport_running)

def stop_sport_event_cb(e):
    global is_sporting
    is_sporting = False
    lv.screen_load(screen_sport)

btn_start_sport.add_event_cb(start_sport_event_cb, lv.EVENT.CLICKED, None)
btn_stop_sport.add_event_cb(stop_sport_event_cb, lv.EVENT.CLICKED, None)

# 6. 汇率查询屏幕
screen_exchange = lv.obj()
screen_exchange.set_style_bg_color(lv.color_hex(0x000000), 0)

label_exc_title = lv.label(screen_exchange)
label_exc_title.set_text("汇率查询")
label_exc_title.set_style_text_font(font_cn, 0)
label_exc_title.set_style_text_color(lv.color_hex(0xFFFFFF), 0)
label_exc_title.align(lv.ALIGN.TOP_MID, 0, 30)

# 货币选项
currency_options = "CNY\nUSD\nEUR\nJPY\nHKD\nGBP\nAUD\nCAD"

# 左边选择框 (From)
dd_from = lv.dropdown(screen_exchange)
dd_from.set_options(currency_options)
dd_from.set_width(85)
dd_from.align(lv.ALIGN.CENTER, -55, -20)
# 设置列表字体
dd_from_list = dd_from.get_list()
if dd_from_list: dd_from_list.set_style_text_font(font_cn, 0)

# 右边选择框 (To)
dd_to = lv.dropdown(screen_exchange)
dd_to.set_options(currency_options)
dd_to.set_selected(1) # 默认 USD
dd_to.set_width(85)
dd_to.align(lv.ALIGN.CENTER, 55, -20)
# 设置列表字体
dd_to_list = dd_to.get_list()
if dd_to_list: dd_to_list.set_style_text_font(font_cn, 0)

label_arrow = lv.label(screen_exchange)
label_arrow.set_text("->")
label_arrow.set_style_text_color(lv.color_hex(0xFFFFFF), 0)
label_arrow.align(lv.ALIGN.CENTER, 0, -20)

# 查询按钮
btn_exc_query = lv.button(screen_exchange)
btn_exc_query.set_size(100, 40)
btn_exc_query.align(lv.ALIGN.CENTER, 0, 35)
btn_exc_lbl = lv.label(btn_exc_query)
btn_exc_lbl.set_text("查询")
btn_exc_lbl.set_style_text_font(font_cn, 0)
btn_exc_lbl.center()

# 状态提示 (原本的结果显示位置改为显示"正在查询"等状态)
label_exc_status = lv.label(screen_exchange)
label_exc_status.set_text("")
label_exc_status.set_style_text_font(font_cn, 0)
label_exc_status.set_style_text_color(lv.palette_main(lv.PALETTE.YELLOW), 0)
label_exc_status.align(lv.ALIGN.BOTTOM_MID, 0, -30)

# 6.5 汇率结果屏幕
screen_exchange_result = lv.obj()
screen_exchange_result.set_style_bg_color(lv.color_hex(0x000000), 0)

label_res_title = lv.label(screen_exchange_result)
label_res_title.set_text("查询结果")
label_res_title.set_style_text_font(font_cn, 0)
label_res_title.set_style_text_color(lv.color_hex(0xFFFFFF), 0)
label_res_title.align(lv.ALIGN.TOP_MID, 0, 40)

label_res_val = lv.label(screen_exchange_result)
label_res_val.set_text("")
label_res_val.set_style_text_font(lv.font_montserrat_16, 0)
label_res_val.set_style_text_color(lv.palette_main(lv.PALETTE.LIGHT_BLUE), 0)
label_res_val.set_width(230)
label_res_val.set_style_text_align(lv.TEXT_ALIGN.CENTER, 0)
label_res_val.align(lv.ALIGN.CENTER, 0, -10)

label_res_rate = lv.label(screen_exchange_result)
label_res_rate.set_text("")
label_res_rate.set_style_text_font(font_cn, 0)
label_res_rate.set_style_text_color(lv.color_hex(0xAAAAAA), 0)
label_res_rate.align(lv.ALIGN.CENTER, 0, 30)

btn_res_back = lv.button(screen_exchange_result)
btn_res_back.set_size(100, 40)
btn_res_back.align(lv.ALIGN.BOTTOM_MID, 0, -40)
btn_res_back_lbl = lv.label(btn_res_back)
btn_res_back_lbl.set_text("返回")
btn_res_back_lbl.set_style_text_font(font_cn, 0)
btn_res_back_lbl.set_style_text_color(lv.color_hex(0x000000), 0)
btn_res_back_lbl.center()

def back_to_exchange_cb(e):
    lv.screen_load(screen_exchange)

btn_res_back.add_event_cb(back_to_exchange_cb, lv.EVENT.CLICKED, None)

def query_exchange_event_cb(e):
    # 获取选中的货币字符串 (增加缓冲区大小并检查)
    from_buf = " "*16
    dd_from.get_selected_str(from_buf, len(from_buf))
    from_coin = from_buf.strip()
    
    to_buf = " "*16
    dd_to.get_selected_str(to_buf, len(to_buf))
    to_coin = to_buf.strip()
    
    # 调试打印，检查获取到的货币代码
    print("Debug - From: [{}], To: [{}]".format(from_coin, to_coin))
    
    if not from_coin or not to_coin:
        label_exc_status.set_text("错误: 货币选择无效")
        return
    
    label_exc_status.set_text("正在查询...")
    
    url = "https://apis.tianapi.com/fxrate/index"
    api_key = "xxx" # https://www.tianapi.com/获取汇率api-key
    # POST 参数使用 x-www-form-urlencoded 格式
    params = "key={}&money=1&fromcoin={}&tocoin={}".format(api_key, from_coin, to_coin)
    headers = {'Content-type': 'application/x-www-form-urlencoded'}
    
    print("Exchange API Request: {} data={}".format(url, params))
    
    if connect_wifi():
        retry_count = 2
        success = False
        while retry_count >= 0 and not success:
            try:
                res = urequests.post(url, data=params, headers=headers, timeout=10)
                print("Response Status: {} (Retries left: {})".format(res.status_code, retry_count))
                data_all = res.json()
                print("Response Body: {}".format(data_all))
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
                        
                        print("Setting Result: {} | {}".format(main_text, rate_text))
                        
                        # 分别设置到两个 Label
                        label_res_val.set_text(main_text)
                        label_res_rate.set_text(rate_text)
                        
                        label_exc_status.set_text("") # 清空查询页面的状态
                        lv.screen_load(screen_exchange_result)
                        success = True
                    else:
                        if "newslist" in data_all and len(data_all["newslist"]) > 0:
                            label_exc_status.set_text("接口返回了新闻数据\n请检查API类型")
                        else:
                            label_exc_status.set_text("未获取到汇率结果")
                        success = True # 虽然没数据但请求成功了，不再重试
                else:
                    label_exc_status.set_text("失败: {}".format(data_all.get('msg', '未知错误')))
                    success = True # 接口返回了错误码，通常是参数或Key问题，不再重试
            except Exception as ex:
                print("Exchange Query Error: {} (Retries left: {})".format(ex, retry_count))
                retry_count -= 1
                if retry_count < 0:
                    label_exc_status.set_text("网络连接中断\n请重试")
                else:
                    time.sleep(1) # 等待一秒后重试
    else:
        label_exc_status.set_text("请先连接 WiFi")

btn_exc_query.add_event_cb(query_exchange_event_cb, lv.EVENT.CLICKED, None)

# 7. 二维码屏幕
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
label_qr.set_text("扫码支付")
label_qr.set_style_text_font(font_cn, 0)
label_qr.align(lv.ALIGN.BOTTOM_MID, 0, -20)

# 8. 系统信息屏幕
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

# 9. 设置屏幕
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

screens = [screen_time, screen_weather, screen_heart, screen_sport, screen_exchange, screen_qr, screen_sys, screen_settings]

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

def update_heart_cb(t):
    # 模拟心率数值 (60-100之间小幅波动)
    current_val = int(label_h_val.get_text())
    new_val = current_val + random.randint(-2, 2)
    if new_val < 60: new_val = 60
    if new_val > 100: new_val = 100
    label_h_val.set_text(str(new_val))
    
    # 模拟心电图波动
    # 产生一个类似心跳的波形：大部分时间在基线，偶尔有突起
    if random.random() > 0.8: # 20% 概率产生波动
        ecg_val = random.randint(40, 90)
    else:
        ecg_val = random.randint(20, 30)
    
    chart_ecg.set_next_value(ser_ecg, ecg_val)

def update_sport_cb(t):
    global sport_steps, sport_calories, sport_distance, sport_duration
    if is_sporting:
        sport_duration += 1
        # 模拟步数增加 (每秒增加 1-3 步)
        sport_steps += random.randint(1, 3)
        # 模拟消耗 (大约 20步 1 kcal)
        sport_calories = sport_steps // 20
        # 模拟距离 (大约 1300步 1 km)
        sport_distance = sport_steps / 1300.0
        
        # 更新正在运动页面的时长
        mins = sport_duration // 60
        secs = sport_duration % 60
        label_duration.set_text("时长: {:02d}:{:02d}".format(mins, secs))
        
        # 更新运动数据主页面的数值
        label_steps.set_text("步数: {}".format(sport_steps))
        label_calories.set_text("消耗: {} kcal".format(sport_calories))
        label_distance.set_text("距离: {:.2f} km".format(sport_distance))

# 创建定时器
timer_time = lv.timer_create(update_time_cb, 200, None) # 提高刷新频率到 200ms，防止秒钟跳显
timer_weather = lv.timer_create(update_weather_cb, 3600000, None) # 每小时更新一次
timer_sys = lv.timer_create(update_sys_cb, 2000, None)
timer_heart = lv.timer_create(update_heart_cb, 300, None) # 心率图表刷新快一点
timer_sport = lv.timer_create(update_sport_cb, 1000, None) # 运动数据每秒更新一次

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



#!/opt/bin/lv_micropython -i
import time
import lvgl as lv
import display_driver

cw = lv.colorwheel(lv.screen_active(), True)
cw.set_size(200, 200)
cw.center()


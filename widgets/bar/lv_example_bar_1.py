#!/opt/bin/lv_micropython -i
import time
import lvgl as lv
import display_driver

bar1 = lv.bar(lv.screen_active())
bar1.set_size(200, 20)
bar1.center()
bar1.set_value(70, None)

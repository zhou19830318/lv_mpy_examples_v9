#!//opt/bin/lv_micropython -i
import time
import lvgl as lv
import display_driver

#
# Scrolling with Right To Left base direction
#
obj = lv.obj(lv.screen_active())
obj.set_style_base_dir(lv.BASE_DIR.RTL, 0)
obj.set_size(200, 100)
obj.center()

label = lv.label(obj)
label.set_text("hello,LVGL!")
label.set_width(400)
label.set_style_text_font(lv.font_montserrat_16, 0)

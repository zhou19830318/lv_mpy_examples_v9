#!/opt/bin/lv_micropython -i
import time
import lvgl as lv
import display_driver

# Create a spinner
spinner = lv.spinner(lv.screen_active())
spinner.set_size(100, 100)
spinner.center()
spinner.set_anim_params(1000, 60)

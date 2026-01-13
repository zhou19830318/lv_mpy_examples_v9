#!/opt/bin/lv_micropython -i
import sys
import lvgl as lv
import display_driver
from fs_driver import fs_register

fs_drv = lv.fs_drv_t()
fs_register(fs_drv, "S")

img = lv.image(lv.screen_active())
img.set_src("S:wink.png")
img.set_size(100, 100)
img.center()


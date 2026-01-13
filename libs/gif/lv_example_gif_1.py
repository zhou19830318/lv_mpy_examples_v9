#!/opt/bin/lv_micropython -i
import sys
import lvgl as lv
import display_driver
import fs_driver

# Initialize file system and fonts
fs_drv = lv.fs_drv_t()
fs_driver.fs_register(fs_drv, 'S')

img1 = lv.gif(lv.screen_active())
# The File system is attached to letter 'S'

img1.set_src("S:bulb.gif")
img1.align(lv.ALIGN.CENTER, 0, 0)

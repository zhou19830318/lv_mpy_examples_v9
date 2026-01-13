#!/opt/bin/lv_micropython-ffmpeg -i
import sys
import lvgl as lv
import display_driver

try:
    #
    # Open an image from a file
    #
    img = lv.image(lv.screen_active())
    img.set_src("ffmpeg.png")
    img.center()
except Exception as e:
    print(e)
    # TODO
    # fallback for online examples

    label = lv.label(lv.screen_active())
    label.set_text("FFmpeg is not installed")
    label.center()

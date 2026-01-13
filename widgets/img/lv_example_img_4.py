#!/opt/bin/lv_micropython -i
import sys
import lvgl as lv
import display_driver


def ofs_y_anim(img, v):    
    img.set_offset_y(v)
    # print(img,v)
    

# Create an image from the png file
try:
    with open('./wink.png','rb') as f:
        png_data = f.read()
except:
    print("Could not find img_skew_strip.png")
    sys.exit()
    
img_skew_strip = lv.image_dsc_t({
  'data_size': len(png_data),
  'data': png_data 
})

#
# Image styling and offset
#

style = lv.style_t()
style.init()
style.set_bg_color(lv.palette_main(lv.PALETTE.YELLOW))
style.set_bg_opa(lv.OPA.COVER)
style.set_image_recolor_opa(lv.OPA.COVER)
style.set_image_recolor(lv.color_black())

img = lv.image(lv.screen_active())
img.add_style(style, 0)
img.set_src(img_skew_strip)
img.set_size(150, 100)
img.center()

a = lv.anim_t()
a.init()
a.set_var(img)
a.set_values(0, 100)
a.set_duration(3000)
a.set_reverse_duration(500)
a.set_repeat_count(lv.ANIM_REPEAT_INFINITE)
a.set_custom_exec_cb(lambda a,val: ofs_y_anim(img,val))
lv.anim_t.start(a)

#!/opt/bin/lv_micropython -i
import sys
import lvgl as lv
import display_driver


# Create an image from the png file
try:
    with open('./wink.png','rb') as f:
        png_data = f.read()
except:
    print("Could not find img_cogwheel_argb.png")
    sys.exit()
    
img_cogwheel_argb = lv.image_dsc_t({
  'data_size': len(png_data),
  'data': png_data 
})

def set_angle(img, v):
    img.set_rotation(v)

def set_scale(img, v):
    img.set_scale(v)


#
# Show transformations (zoom and rotation) using a pivot point.
#

# Now create the actual image
img = lv.image(lv.screen_active())
img.set_src(img_cogwheel_argb)
img.align(lv.ALIGN.CENTER, 50, 50)
img.set_pivot(0, 0)               # Rotate around the top left corner

a1 = lv.anim_t()
a1.init()
a1.set_var(img)
a1.set_custom_exec_cb(lambda a,val: set_angle(img,val))
a1.set_values(0, 3600)
a1.set_duration(5000)
a1.set_repeat_count(lv.ANIM_REPEAT_INFINITE)
lv.anim_t.start(a1)

a2 = lv.anim_t()
a2.init()
a2.set_var(img)
a2.set_custom_exec_cb(lambda a,val: set_scale(img,val))
a2.set_values(128, 256)
a2.set_duration(5000)
a2.set_reverse_duration(3000)
a2.set_repeat_count(lv.ANIM_REPEAT_INFINITE)
lv.anim_t.start(a2)

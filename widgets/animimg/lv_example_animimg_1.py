#!/opt/bin/lv_micropython -i
import sys
import lvgl as lv
import display_driver

anim_imgs = [None]*3
# Create an image from the png file
try:
    with open('./wink1.png','rb') as f:
        anim001_data = f.read()
except:
    print("Could not find animimg001.png")
    sys.exit()
    
anim_imgs[0] = lv.image_dsc_t({
  'data_size': len(anim001_data),
  'data': anim001_data 
})

try:
    with open('./wink2.png','rb') as f:
        anim002_data = f.read()
except:
    print("Could not find animimg002.png")
    sys.exit()
    
anim_imgs[1] = lv.image_dsc_t({
  'data_size': len(anim002_data),
  'data': anim002_data 
})

try:
    with open('./wink3.png','rb') as f:
        anim003_data = f.read()
except:
    print("Could not find animimg003.png")
    sys.exit()
    
anim_imgs[2] = lv.image_dsc_t({
  'data_size': len(anim003_data),
  'data': anim003_data 
})

animimg0 = lv.animimg(lv.screen_active())
animimg0.center()
animimg0.set_src(anim_imgs, 3)
animimg0.set_duration(1000)
animimg0.set_repeat_count(lv.ANIM_REPEAT_INFINITE)
animimg0.start()

#!//opt/bin/lv_micropython -i
import time
import lvgl as lv
import display_driver

def event_cb(e):
    obj = lv.buttonmatrix.__cast__(e.get_target())
    id = obj.get_selected_button()
    if id == 0:
        prev = True
    else:
        prev = False
    if id == 6:
        next = True
    else:
        next = False
    if prev or next:
        # Find the checked butto
        for i in range(7):
            if obj.has_button_ctrl(i, lv.buttonmatrix.CTRL.CHECKED):
                break
        if prev and i > 1:
            i-=1
        elif next and i < 5:
            i+=1

        obj.set_button_ctrl(i, lv.buttonmatrix.CTRL.CHECKED)

#
# Make a button group
#

style_bg = lv.style_t()
style_bg.init()
style_bg.set_pad_all(0)
style_bg.set_pad_gap(0)
style_bg.set_clip_corner(True)
style_bg.set_radius(lv.RADIUS_CIRCLE)
style_bg.set_border_width(0)


style_btn = lv.style_t()
style_btn.init()
style_btn.set_radius(0)
style_btn.set_border_width(1)
style_btn.set_border_opa(lv.OPA._50)
style_btn.set_border_color(lv.palette_main(lv.PALETTE.GREY))
style_btn.set_border_side(lv.BORDER_SIDE.INTERNAL)
style_btn.set_radius(0)

map = [lv.SYMBOL.LEFT,"1","2", "3", "4", "5",lv.SYMBOL.RIGHT, ""]

btnm = lv.buttonmatrix(lv.screen_active())
btnm.set_map(map)
btnm.add_style(style_bg, 0);
btnm.add_style(style_btn, lv.PART.ITEMS)
btnm.add_event_cb(event_cb, lv.EVENT.VALUE_CHANGED, None)
btnm.set_size(225, 35)

# Allow selecting on one number at time
btnm.set_button_ctrl_all(lv.buttonmatrix.CTRL.CHECKABLE)
btnm.clear_button_ctrl(0, lv.buttonmatrix.CTRL.CHECKABLE)
btnm.clear_button_ctrl(6, lv.buttonmatrix.CTRL.CHECKABLE)

btnm.set_one_checked(True);
btnm.set_button_ctrl(1, lv.buttonmatrix.CTRL.CHECKED)

btnm.center()

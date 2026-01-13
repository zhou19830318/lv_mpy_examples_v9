#!/opt/bin/lv_micropython -i
import time
import lvgl as lv
import display_driver

def event_cb(e):
    btn = e.get_tatget_obj()
    label = btn.get_child(0)
    print("Button " + label.get_text() + " clicked")

btns = ["Apply", "Close", ""]

mbox1 = lv.msgbox(lv.screen_active())
mbox1.add_title("Hello")
mbox1.add_text("This is a message box with two buttons.")
mbox1.add_close_button()
mbox1.center()
btn = lv.button(lv.screen_active())
btn = mbox1.add_footer_button(btns[0])
btn = mbox1.add_footer_button(btns[1])
btn.add_event_cb(event_cb, lv.EVENT.VALUE_CHANGED, None)


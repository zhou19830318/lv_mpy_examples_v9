#!/opt/bin/lv_micropython -i
import time
import lvgl as lv
import display_driver

class Event_1():
    def __init__(self):
        self.cnt = 1
        #
        # Add click event to a button
        #

        btn = lv.button(lv.screen_active())
        btn.set_size(100, 50)
        btn.center()
        btn.add_event_cb(self.event_cb, lv.EVENT.CLICKED, None)
        
        label = lv.label(btn)
        label.set_text("Click me!");
        label.center()

    def event_cb(self,e):
        print("Clicked");
            
        btn = lv.button.__cast__(e.get_target())
        label = btn.get_child(0)
        label.set_text(str(self.cnt))
        self.cnt += 1

evt1 = Event_1()

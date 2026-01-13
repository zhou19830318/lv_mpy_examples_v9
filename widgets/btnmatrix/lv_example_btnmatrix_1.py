#!//opt/bin/lv_micropython -i
import time
import lvgl as lv
import display_driver

def event_handler(evt):
    code = evt.get_code()
    obj  = evt.get_target_obj()

    if code == lv.EVENT.VALUE_CHANGED :
        id = obj.get_selected_button()
        txt = obj.get_button_text(id)

        print("%s was pressed"%txt)

btnm_map = ["1", "2", "3", "4", "5", "\n",
            "6", "7", "8", "9", "0", "\n",
            "Action1", "Action2", ""]

btnm1 = lv.buttonmatrix(lv.screen_active())
btnm1.set_map(btnm_map)
btnm1.set_button_width(10, 2)        # Make "Action1" twice as wide as "Action2"
btnm1.set_button_ctrl(10, lv.buttonmatrix.CTRL.CHECKABLE)
btnm1.set_button_ctrl(11, lv.buttonmatrix.CTRL.CHECKED)
btnm1.align(lv.ALIGN.CENTER, 0, 0)
btnm1.add_event_cb(event_handler, lv.EVENT.ALL, None)


#endif

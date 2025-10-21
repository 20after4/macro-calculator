# Copyright © 2025 by Mukunda Modell
# You can use this code under the terms of the GNU GPL v3.0
# see LICENSE.md
# https://git.sr.ht/~twentyafterfour/macro-calculator

import time
import re
import io
import os
import machine
from sys import platform
from machine import Pin, Signal, SPI
from micropython import const
from rp2_dma import DMA
from st77xx import St7789
import lvgl as lv
from lv_utils import event_loop
import bus
from bus import led
import keymap
from keymap import keys, keyboard
import style
from style import Menu,HIDDEN
from settimeout import setTimeout
from decimal import DecimalNumber
from usbkeypad import KeypadInterface
from history import History

DecimalNumber.set_scale(16)
MAX_LINE_LEN = const(17)


def numformat(num):
    if type(num) is DecimalNumber:
        return num.to_string_max_length(17)
    else:
        return "{: 16.10g}".format(num)

M1 = 0
M2 = 0
M3 = 0
M4 = 0

num_expr = "([M0-9\.]+)*"
oper_expr = "([\+\-\*\/\=])?"
tok = re.compile("^"+num_expr+oper_expr+num_expr+"(.*)")

def lvgl_keypad_read(kp, data):
    scan = input_next()
    if scan is not None:

        key, value = scan

        if value:
            data.state = lv.INDEV_STATE.PRESSED
        else:
            data.state = lv.INDEV_STATE.RELEASED
        keycode = key[0]
        res = key.update(value)
        if res is not None:
            return
        if keyboard.layer==1:
            if keycode == keymap.KP8:
                data.key = lv.KEY.UP
            elif keycode == keymap.KP2:
                data.key = lv.KEY.DOWN
            elif keycode == keymap.KP4:
                data.key = lv.KEY.LEFT
            elif keycode == keymap.KP6:
                data.key = lv.KEY.RIGHT
            elif keycode == keymap.F18:
                data.key = lv.KEY.ESC
            elif keycode == keymap.KP3:
                data.key = lv.KEY.PREV
            elif keycode == keymap.KP9:
                data.key = lv.KEY.NEXT
            elif keycode == keymap.KP7:
                data.key = lv.KEY.HOME
            elif keycode == keymap.KP1:
                data.key = lv.KEY.END
            else:
                app.send_key(keycode, key, value)
                data.state = lv.INDEV_STATE.RELEASED
        else:
            if keycode == keymap.ENTER:
                data.key = lv.KEY.ENTER
            elif keycode == keymap.F19:
                data.key = lv.KEY.BACKSPACE
            elif len(key[2]) == 1:
                data.key = ord(key[2])
            else:
                #app.send_key(keycode, key, value)
                data.state = lv.INDEV_STATE.RELEASED
        print('LVGL key', data.state, data.key)
    else:
        data.state = lv.INDEV_STATE.RELEASED



def lvgl_input():
    kp = lv.indev_create()
    kp.set_type(lv.INDEV_TYPE.KEYPAD)
    kp.set_read_cb(lvgl_keypad_read)
    return kp




class Calc:
    state = keymap.keyboard.state
    operators = ('+', '-', '*', '/', '%', '^', '<', '>', '!')

    saved_expr = None

    def show_err(self, err):
        self.show_msg(err.value, 8, style.red)

    def show_msg(self, msg, timeout=5, color=None):
        if color is None:
            color = style.blue
        self.msg.set_text(msg)
        self.msg.set_style_text_color(color, lv.PART.MAIN)
        self.msg.remove_flag(HIDDEN)
        setTimeout(timeout, self.hide_msg)

    def hide_msg(self):
        self.msg.add_flag(HIDDEN)

    def __init__(self):
        self.NUMLOCK(True)
        self.scr = lv.obj()
        self.scr.add_style(style.DEFAULT, lv.PART.MAIN)
        self.panel = lv.obj(self.scr)
        self.panel.add_style(style.DEFAULT, lv.PART.MAIN)
        self.panel.add_flag(self.panel.FLAG.SCROLLABLE)
        self.panel.add_flag(self.panel.FLAG.SCROLL_ON_FOCUS)
        self.panel.set_scrollbar_mode(lv.SCROLLBAR_MODE.OFF)
        self.panel.set_style_pad_all(0,0)
        self.panel.set_size(284, 76)
        self.panel.add_event_cb(self.focus_changed, lv.EVENT.FOCUSED, None)
        self.grp = lv.group_create()
        self.grp.set_default()
        self.menu = Menu(self)
        self.input = lvgl_input()
        self.input.set_group(self.grp)
        self.mono_font = lv.font_unscii_16
        self.small_font = lv.font_montserrat_14
        # create labels for our 4 lines of text:
        self.txt = self.textarea(3,17)

        self.set_lines([
            self.txt,
            self.text_line(1,17),
            self.text_line(2,17),
            self.text_line(3,17),
        ])

        self.history = History(10, self.lines[1:])

        self.txt.add_event_cb(self.ENTER, lv.EVENT.READY, None)

        # And a label above the top line, to be shown when there is an input error.
        self.msg = self.text_line(0, 20, "", self.small_font, self.scr)
        self.msg.add_flag(self.msg.FLAG.FLOATING)
        self.msg.add_flag(HIDDEN)
        self.msg.set_style_text_align(lv.TEXT_ALIGN.LEFT, 0)
        self.msg.set_style_text_color(style.blue, lv.PART.SELECTED)
        self.msg.set_style_bg_color(style.black, lv.PART.SELECTED)

        self.index = 0

        # current_line is normally pointing to the last/bottom line of text
        self.current_line = self.txt
        # we use lvgl selection and an empty space for a cursor - empty label can't have a selection
        self.current_line.set_text('')

        self.load_history()

        lv.screen_load(self.scr)

        self.k = KeypadInterface()

        global keyboard
        keyboard.app = self

        if (event_loop.is_running()):
            self.event_loop = event_loop.current_instance()
        else:
            self.event_loop = event_loop()

        self.event_loop.refresh_cb = scan_keys


    def text_line(self, index, maxlen=17, text="", font=None, parent=None):
        """ Create a single label object to represent 1 line of text on the display. """
        if parent is None:
            parent = self.panel
        line = lv.label(parent)
        if font == None:
            line.set_style_text_font(self.mono_font, 0)
        else:
            line.set_style_text_font(font, 0)
        style.set_style(line)

        #line.set_pos(0, 2 + (index * 17))
        line.set_size(lv.pct(100), lv.SIZE_CONTENT)
        line.set_style_text_align(lv.TEXT_ALIGN.RIGHT, lv.PART.MAIN)
        line.set_text(text)

        self.grp.add_obj(line)
        return line

    def textarea(self, index, maxlen=17, text="", font=None):
        """ Create a single textarea object to represent the editable line """
        line = lv.textarea(self.panel)
        if font == None:
            line.set_style_text_font(self.mono_font, 0)
        else:
            line.set_style_text_font(font, 0)
        line.set_one_line(True)
        self.grp.add_obj(line)
        line.set_height(18)
        line.set_width(275)
        line.set_max_length(maxlen)
        style.set_style(line)
        lbl = line.get_label()
        lbl.set_style_pad_right(2, lv.PART.MAIN)
        #line.add_style(style.text_selected, lv.PART.SELECTED)
        #line.add_style(style.text_cursor, lv.PART.CURSOR | lv.STATE.FOCUSED)

        #line.set_pos(0, 2 + (index * 17))
        line.set_style_text_align(lv.TEXT_ALIGN.RIGHT, lv.PART.MAIN)
        line.set_scrollbar_mode(lv.SCROLLBAR_MODE.OFF)
        line.set_text(text)
        line.set_cursor_pos(len(text))
        line.add_state(lv.STATE.FOCUSED)
        line.scroll_to_view_recursive(False)
        return line


    def focus_changed(self, e):
        target = e.get_target_obj()
        print(target)
        print(target.get_text())

        y = target.get_y()
        sy = self.panel.get_scroll_y()

        print(f"{y}, {sy}, {y-sy}, {sy-y}")
        #self.panel.scroll_by(0, diff, 0)

    def set_lines(self, lines):
        self.lines = lines
        prev = None
        i=0
        for line in reversed(lines):
            line.set_pos(0,i*17)
            i += 1


    def load_history(self):
        try:
            os.stat('/data/history.txt')
        except Exception as e:
            return
        f = io.open('/data/history.txt', mode="r")
        try:
            lines = []
            val = f.readline()
            while val != '':
                val = val.rstrip()
                lines.append(val)
                if len(lines) > 4:
                    lines.pop(0)
                val = f.readline()

            for i in range(3, 0, -1):
                self.set_line(i-1, lines.pop())
            f.seek(0)
            f.write("\n")
            f.flush()
            f.close()
            os.unlink('/data/history.txt')
        except Exception as e:
            print(e)
        finally:
            f.close()


    def set_line(self, linenum, value):
        self.lines[linenum].set_text(str(value))
        if (value == ""):
            num = DecimalNumber(0)
        else:
            num = DecimalNumber(value)
        if linenum == 1:
            M1 = num
        elif linenum == 2:
            M2 = num
        elif linenum == 3:
            M3 = num
        elif linenum == 4:
            M4 = num

    def clear(self, linenum):
        self.set_line(linenum, 0)


    def send_key(self, scancode, key, keydown=1):
        keycode, symbol, value = key[0:3]
        if len(key) > 3:
            shifted = key[3]
        else:
            shifted = None

        if keycode == keymap.NUMLOCK:
            if keydown == 1:
                self.NUMLOCK()
            return

        if not self._lock:
            if keydown:
                self.k.send_key(keycode)
            else:
                self.k.send_key(None)
            return
        if symbol is None and value is None:
            return
        else:
            if keyboard.layer==1 and shifted is not None:
                method = getattr(self, shifted, None)
            else:
                method = getattr(self, symbol, None)

            if method is not None:
                method(keydown)
            elif keydown:
                if keyboard.layer==1 and shifted is not None:
                    self.insert_text(shifted)
                else:
                    self.insert_text(value)


    def insert_text(self, value, pos=lv.LABEL_POS_LAST):
        current = self.current_line
        current_text = current.get_text()
        current_length = len(current_text)
        if current_length == MAX_LINE_LEN or current_length + len(value) > MAX_LINE_LEN:
            return
        if pos == lv.LABEL_POS_LAST:
            pos = current_length

        is_operator = value in self.operators

        if (current_text == " " or
            (is_operator and current_text[-1:] in self.operators)
        ):
            # replace the operator at the end of line with a new operator
            current_text = current_text[0:-1] + value
            current.set_text(current_text)
        elif is_operator and current_text[0:1] in self.operators:
            # replace the operator at the start of line with a new operator
            current_text = value + current_text[1:]
            current.set_text(current_text)
        else:
            current.add_text(value)



    def update_cursor(self, current_line=None):
        pass


    def NUMLOCK(self, value=None):
        if value is None:
            self._lock = not self._lock
        else:
            self._lock = value

        led.value(self._lock)
        if not self._lock:
            self.k.initialize_usb()


    def HOME(self):
        self.send_key(HOME)

    def RECALL(self, keydown):
        if not keydown:
            return
        if self.saved_expr is not None:
            self.current_line.set_text(self.saved_expr)
            self.update_cursor()

    def ENTER(self, keydown):
        if not keydown:
            return
        if keyboard.layer == 1:
            self.insert_text("=")
            return

        global M1, M2, M3, M4

        try:
            orig_expr = self.txt.get_text().strip()
            if orig_expr == "":
                return
            out = []
            saved_expr = orig_expr
            while len(orig_expr) > 0:
                groups = None
                print("tokenize: ",orig_expr)
                expr = tok.match(orig_expr)
                print('done tokenizing')
                if expr:
                    groups = expr.groups()
                    end = expr.end()
                    orig_expr = orig_expr[end:]
                if not groups:
                    groups = [orig_expr]
                    orig_expr = ""
                for group in groups:
                    if group is None or group == "":
                        continue
                    if group.isdigit():
                        out.append('DecimalNumber("'+group+'")')
                    else:
                        out.append(group)

            assign = None
            if len(out) > 1 and out[1] == '=' and (out[0] == 'M3' or out[0] == 'M4'):
                assign = out[0]
                out = out[2:]

            expr = "".join(out)
            if (expr[0] in ("+","/","*","-")):
                expr = "M1" + expr
            print('eval:',str(expr))
            res = eval(str(expr))
            if type(res) is float:
                res = DecimalNumber(str(res))
            elif type(res) is not DecimalNumber:
                res = DecimalNumber(res)
            if assign == 'M3':
                M3 = res
            elif assign == 'M4':
                M4 = res

            self.history.append(numformat(res))

            M2 = M1
            M1 = res
            self.hide_msg()

            self.txt.set_text("")
            self.saved_expr = saved_expr


        except Exception as e:
            self.show_err(e)

        #self.send_key(keymap.ENTER)

    def F13(self, keydown):
        self.menu_key(keydown, 0)
    def F14(self, keydown):
        self.menu_key(keydown, 1)
    def F15(self, keydown):
        self.menu_key(keydown, 2)
    def F16(self, keydown):
        self.menu_key(keydown, 3)

    def action(self, key, action, symbol):
        method = getattr(self, symbol, None)
        if method is not None:
            method(key, action)
        else:
            print('Unmatched key', key, symbol)

    def STORE(self, key, action):
        global M1, M2, M3, M4
        if action == keymap.LONGPRESS:
            if key.symbol == "M3":
                M3 = M1
                self.show_msg('stored')
            elif key.symbol == "M4":
                M4 = M1
                self.show_msg('stored')

    def menu_key(self, keydown, index):

        if keydown and keyboard.layer==1:
            print('show menu', index)
            self.menu.show(index)
        else:
            page = self.menu.active_page()
            self.menu.hide()
            if page is not None and keydown:
                item = page.get_child(index)
                print('selected item', item.get_text())
            else:
                if keydown:
                    pass
                else:
                    self.insert_text('M')
                    self.insert_text(str(index+1))

    def F17(self, keydown):
        self.shifted = keydown
        # if (self.shifted):
        #     lv.screen_load(self.menu.obj)
        # else:
        #     lv.screen_load(self.scr)


    def F18(self, keydown):
        if keydown:
            if keyboard.layer==1:
                self.clear(0)
                self.history.clear()
            else:
                self.clear(self.index)

    def F19(self, keydown):
        if keydown:
            self.current_line.set_text(self.current_line.get_text()[0:-1])
            self.update_cursor()

    def pgdn(self):
        self.send_key(keymap.PGDN)

    def pgup(self):
        self.send_key(keymap.PGUP)


input_buffer = []
def input_next():
    if len(input_buffer) > 0:
        return input_buffer.pop(0)
    return None


def scan_keys():
    cols = keymap.cols
    rows = keymap.rows
    state = keymap.keyboard.state

    is_pico2 = platform == "rp2"

    for c in range(len(cols)):
        # turn on one column at a time
        cols[c].on()

        for r in range(len(rows)):
            scancode = (r * len(cols)) + c
            # Read the state from each row to find keys that are pressed.

            # We have to re-init each GPIO to OUTPUT then back to INPUT in order
            # to use the PULL_DOWN inputs. This is due to a hardware bug (RP2350 Errata E9)
            # These next 3 lines are not needed for the rp2040.
            # Hopefully future hardware revisions will fix this, unfortunately, The RPI Pico 2
            # boards that I have tested definitely need this workaround:
            if is_pico2:
                rows[r].init(mode=Pin.OUT, pull=None, value=0)
                time.sleep_us(10)
                rows[r].init(mode=Pin.IN, pull=Pin.PULL_DOWN)
                time.sleep_us(10)
            # end Errata workaround


            # read the value from the row's GPIO pin

            value = rows[r].value()

            # the state array tracks which keys were pressed the last time we scanned the matrix.
            if state[scancode] != value:
                # Only react to key state that has changed since the last scan
                key = keys[scancode]
                # TODO: We couold add key repeating for held down keys here. Currently we only report
                # key down and key up events.

                print(scancode, key, value)
                if (key is not None):
                    try:
                        input_buffer.append((key, value))

                        # key behavior is defined in the app class, just pass the raw data to app.send_key
                        # if app.shifted and shifted_key == None and key[0] != keymap.F17:
                        #     input_buffer.append((scancode, key, value))
                        # else:
                        #    app.send_key(scancode, key[0], key[1], key[2], shifted_key, value)

                    except Exception as e:
                        print(e)

                # record the state of each key
                state[scancode] = value

        # turn off this column and move on to the next
        cols[c].off()

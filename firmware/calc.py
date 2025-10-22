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

kpp = None
kpd = None

def lvgl_keypad_read(kp, data):
    try:
        global input_buffer
        data.key = 0
        scan = input_next()

        if scan is not None:

            key, value = scan

            if value:
                data.state = lv.INDEV_STATE.PRESSED
            else:
                data.state = lv.INDEV_STATE.RELEASED
            keycode = key[0]
            res = key.update(value)
            if res:
                return
            if key.scancode == keymap.NUMLOCK and value:
                app.NUMLOCK(keyboard.NumLock)
                app.k.send_key(None)
                return
            elif keyboard.NumLock:
                if value:
                    app.k.send_key(key.scancode)
                else:
                    app.k.send_key(None)
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
                    kp.stop_processing()

            else:
                if keycode == keymap.ENTER:
                    data.key = lv.KEY.ENTER
                elif keycode == keymap.F19:
                    data.key = lv.KEY.BACKSPACE
                elif type(key[2]) is str and len(key[2]) == 1:
                    data.key = ord(key[2])
                else:
                    app.send_key(keycode, key, value)
                    kp.stop_processing()
            print('LVGL key', data.state, data.key)
        else:
            data.state = lv.INDEV_STATE.RELEASED
        if len(input_buffer):
            data.continue_reading = 1
    except Exception as e:
        print(e)


class Calc:
    state = keymap.keyboard.state
    operators = ('+', '-', '*', '/', '%', '^', '<', '>', '!')

    saved_expr = None

    def __init__(self):
        # some global state is stored in the keymap.keyboard singleton object
        global keyboard
        keyboard.app = self

        self.NUMLOCK(True)
        self.scr = lv.obj()
        self.scr.add_style(style.DEFAULT, lv.PART.MAIN)

        # The main calculator interface (4 lines of text, 1 input and 3 output)
        self.panel = lv.obj(self.scr)
        self.panel.add_style(style.DEFAULT, lv.PART.MAIN)
        self.panel.add_flag(self.panel.FLAG.SCROLLABLE)
        self.panel.add_flag(self.panel.FLAG.SCROLL_ON_FOCUS)
        self.panel.set_scrollbar_mode(lv.SCROLLBAR_MODE.OFF)
        self.panel.set_style_pad_all(0,0)
        self.panel.set_size(284, 76)
        self.panel.add_event_cb(self.focus_changed, lv.EVENT.FOCUSED, None)

        self.menu = Menu(self)

        # lvgl focus group & input device
        self.grp = lv.group_create()
        self.grp.set_default()
        self.get_focused = self.grp.get_focused()
        self.input = lv.indev_create()
        self.input.set_type(lv.INDEV_TYPE.KEYPAD)
        self.input.set_read_cb(lvgl_keypad_read)
        self.input.set_group(self.grp)

        self.mono_font = lv.font_unscii_16
        self.small_font = lv.font_montserrat_14

        # create labels for our 4 lines of text:
        self.txt = self.textarea()

        self.set_lines([
            self.txt,
            self.text_line(1),
            self.text_line(2),
            self.text_line(3),
        ])

        # a circular buffer to store a history of the resuolts from evaluated expressions
        self.history = History(10, self.lines[1:])

        # lvgl callback to evaluate the user's expression input
        self.txt.add_event_cb(self.ENTER, lv.EVENT.READY, None)

        # And a label above the top line, to be shown when there is an input error.
        # Remains hidden until there is something to show.
        self.msg = self.text_line(0, self.small_font, self.scr)
        self.msg.add_flag(self.msg.FLAG.FLOATING)
        self.msg.add_flag(HIDDEN)
        self.msg.set_style_text_align(lv.TEXT_ALIGN.LEFT, 0)

        # current_line is normally pointing to the last/bottom line of text
        self.current_line = self.txt
        # we use lvgl selection and an empty space for a cursor - empty label can't have a selection
        self.current_line.set_text('')

        # activate the main lvgl screen component
        lv.screen_load(self.scr)

        # initialize the usb keyboard HID interface
        self.k = KeypadInterface()

        # start the event loop if it isn't already started:
        if (event_loop.is_running()):
            self.event_loop = event_loop.current_instance()
        else:
            self.event_loop = event_loop()

        self.event_loop.refresh_cb = scan_keys


    def text_line(self, index=-1, font=None, parent=None):
        """ Create a single label object to represent 1 line of text on the display. """
        if parent is None:
            parent = self.panel
        line = lv.label(parent)
        if font == None:
            font = self.mono_font
        line.set_style_text_font(font, 0)
        style.set_style(line)

        line.set_size(lv.pct(100), lv.SIZE_CONTENT)
        line.set_style_text_align(lv.TEXT_ALIGN.RIGHT, lv.PART.MAIN)
        if index >= 0:
            line.set_user_data(str(index))

        self.grp.add_obj(line)
        return line

    def textarea(self):
        """ Create a single textarea object to represent the editable line """
        line = lv.textarea(self.panel)
        line.set_style_text_font(self.mono_font, 0)

        line.set_one_line(True)
        self.grp.add_obj(line)
        line.set_height(18)
        line.set_width(275)
        line.set_max_length(17)
        style.set_style(line)
        lbl = line.get_label()
        lbl.set_style_pad_right(2, lv.PART.MAIN)

        line.set_style_text_align(lv.TEXT_ALIGN.RIGHT, lv.PART.MAIN)
        line.set_scrollbar_mode(lv.SCROLLBAR_MODE.OFF)

        line.add_state(lv.STATE.FOCUSED)
        line.scroll_to_view_recursive(False)
        return line

    def show_err(self, err):
        """ display an error message for a few seconds """
        self.show_msg(err.value, 8, style.red)

    def show_msg(self, msg, timeout=5, color=None):
        """ display a line of text at the top left of the display """
        if color is None:
            color = style.blue
        self.msg.set_text(msg)
        self.msg.set_style_text_color(color, lv.PART.MAIN)
        self.msg.remove_flag(HIDDEN)
        setTimeout(timeout, self.hide_msg)

    def hide_msg(self):
        """ hide the feedback / error message text """
        self.msg.add_flag(HIDDEN)

    def focus_changed(self, e):
        target = e.get_target_obj()
        self.focused_widget = target

    def set_lines(self, lines):
        self.lines = lines
        prev = None
        i=0
        for line in reversed(lines):
            line.set_pos(0,i*17)
            i += 1



    def clear(self):
        """ clear the input textarea """
        self.txt.set_text("")

    def send_key(self, scancode, key, keydown=1):
        """ process a keystroke """
        symbol = key.get_symbol()
        print(key, symbol)

        if callable(symbol):
            if keydown == 1:
                symbol()
        else:
            method = getattr(self, symbol, None)
            if method is not None:
                method(keydown)
            elif keydown == 1:
                self.insert_text(str(symbol))

    def insert_text(self, value):
        """ Insert text into the input textarea """
        current_text = self.txt.get_text()
        current_length = len(current_text)
        if current_length == MAX_LINE_LEN or current_length + len(value) > MAX_LINE_LEN:
            return

        is_operator = value in self.operators
        if current_text == " " or current_text == "0":
            self.txt.set_text(value)
        elif (is_operator and current_text[-1:] in self.operators):
            # replace the operator at the end of line with a new operator
            current_text = current_text[0:-1] + value
            self.txt.set_text(current_text)
        elif is_operator and current_text[0:1] in self.operators:
            # replace the operator at the start of line with a new operator
            current_text = value + current_text[1:]
            self.txt.set_text(current_text)
        else:
            self.txt.add_text(value)

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
        """ recall the most recently evaluated expression """
        if not keydown:
            return
        if self.saved_expr is not None:
            self.current_line.set_text(self.saved_expr)

    def ENTER(self, keydown):
        """ Parse and evaluate a one-line expression """
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
                    if group[0].isdigit():
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


    def action(self, key, action, symbol):
        method = getattr(self, symbol, None)
        if method is not None:
            method(key, action)
        else:
            print('Unmatched key', key, symbol)

    def STORE(self, key, action):
        """ Take the most recent result value (M1) and assign the value to one
            of the user variable slots (M3 or M4)
        """
        global M1, M2, M3, M4
        if action == keymap.LONGPRESS:
            if key.symbol == "M3":
                M3 = M1
                self.show_msg('stored')
            elif key.symbol == "M4":
                M4 = M1
                self.show_msg('stored')

    def F17(self, keydown):
        self.shifted = keydown
        # if (self.shifted):
        #     lv.screen_load(self.menu.obj)
        # else:
        #     lv.screen_load(self.scr)

    def F19(self, keydown):
        if keydown:
            self.current_line.set_text(self.current_line.get_text()[0:-1])

    def pgdn(self):
        self.send_key(keymap.PGDN)

    def pgup(self):
        self.send_key(keymap.PGUP)

from collections import deque
input_buffer = deque((),10)

def input_next():
    global input_buffer
    if len(input_buffer) > 0:
        return input_buffer.popleft()
    return None


def scan_keys():
    global input_buffer
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

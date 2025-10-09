from st77xx import St7789
import lvgl as lv
from lv_utils import event_loop
import machine
from machine import Pin, Signal, SPI
from rp2_dma import DMA
from micropython import const
import time
import usb.device
from usb.device.hid import HIDInterface
from keymap import keys
import keymap
from settimeout import setTimeout
from decimal import DecimalNumber
import re

blue = lv.color_hex(0x0000ff)
red = lv.color_hex(0xff0000)
white = lv.color_hex(0xffffff)
black = lv.color_hex(0x000000)
yellow = lv.color_hex(0xaacc00)
green = lv.color_hex(0xff0000)
HIDDEN = lv.obj.FLAG.HIDDEN

led = Pin(25, Pin.OUT)

MAX_LINE_LEN = const(17)
_INTERFACE_PROTOCOL_KEYBOARD = const(0x01)

def numformat(num):
    if type(num) is DecimalNumber:
        return num.to_string_max_length(16)
    else:
        return "{: 16.10g}".format(num)

M1 = 0
M2 = 0
M3 = 0
M4 = 0

num_expr = "([0-9]*\.?[0-9]+|M[1-4])*"
oper_expr = "[ ]*([\+\-\*\/])[ ]*"
tok = re.compile(num_expr+oper_expr+num_expr)

class KeypadInterface(HIDInterface):
    # Very basic synchronous USB keypad HID interface

    def __init__(self):
        super().__init__(
            _KEYPAD_REPORT_DESC,
            set_report_buf=bytearray(1),
            protocol=_INTERFACE_PROTOCOL_KEYBOARD,
            interface_str="CalcPad",
        )
        self.numlock = False
        self.enabled = True
        self.usb_initialized = False

    def initialize_usb(self):
        if not self.usb_initialized:
            usb.device.get().init(self, builtin_driver=True)
            self.usb_initialized = True

    def on_set_report(self, report_data, _report_id, _report_type):
        report = report_data[0]
        b = bool(report & 1)
        if b != self.numlock:
            print("Numlock: ", b)
            self.numlock = b

    def send_key(self, key=None):
        if not (self.enabled and self.is_open()):
            return
        if key is None:
            self.send_report(b"\x00")
        else:
            self.send_report(key.to_bytes(1, "big"))



_KEYPAD_REPORT_DESC = (
    b'\x05\x01'  # Usage Page (Generic Desktop)
        b'\x09\x07'  # Usage (Keypad)
    b'\xA1\x01'  # Collection (Application)
        b'\x05\x07'  # Usage Page (Keypad)
            b'\x19\x00'  # Usage Minimum (0)
            b'\x29\xFF'  # Usage Maximum (ff)
            b'\x15\x00'  # Logical Minimum (0)
            b'\x25\xFF'  # Logical Maximum (ff)
            b'\x95\x01'  # Report Count (1),
            b'\x75\x08'  # Report Size (8),
            b'\x81\x00'  # Input (Data, Array, Absolute)
        b'\x05\x08'  # Usage page (LEDs)
            b'\x19\x01'  # Usage Minimum (1)
            b'\x29\x01'  # Usage Maximum (1),
            b'\x95\x01'  # Report Count (1),
            b'\x75\x01'  # Report Size (1),
            b'\x91\x02'  # Output (Data, Variable, Absolute)
            b'\x95\x01'  # Report Count (1),
            b'\x75\x07'  # Report Size (7),
            b'\x91\x01'  # Output (Constant) - padding bits
    b'\xC0'  # End Collection
)



spi = SPI(0, baudrate=24_000_000, polarity=0, phase=0,
    sck = Pin(2, Pin.OUT),
    mosi = Pin(3, Pin.OUT))

lcd = St7789(rot=1, res=(76,284), spi=spi, cs=5, dc=6, rst=7, factor=8, bgr=False)



from array import array
import time

class Calc:

    cols = [ Pin(9, Pin.OUT),
            Pin(16, Pin.OUT),
            Pin(17, Pin.OUT),
            Pin(18, Pin.OUT),
            Pin(19, Pin.OUT)
    ]

    rows = [
            Pin(10, Pin.IN, Pin.PULL_DOWN),
            Pin(11, Pin.IN, Pin.PULL_DOWN),
            Pin(12, Pin.IN, Pin.PULL_DOWN),
            Pin(13, Pin.IN, Pin.PULL_DOWN),
            Pin(14, Pin.IN, Pin.PULL_DOWN),
            Pin(15, Pin.IN, Pin.PULL_DOWN)
    ]

    callbacks = [
        "home", "enter", "pgup",
        "end", "up", "pgdn",
        "left", "down", "right"
    ]
    state = array('b', [0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0])

    shifted = False

    operators = ('+', '-', '*', '/', '%', '^', '<', '>', '!')

    def show_err(self, err):
        self.error.set_text(err.value)
        self.error.set_text_selection_start(0)
        self.error.set_text_selection_end(len(err.value))
        self.error.remove_flag(HIDDEN)
        setTimeout(6,self.hide_err)

    def hide_err(self):
        self.error.add_flag(HIDDEN)

    def __init__(self):
        self.NUMLOCK(True)

        self.scr = lv.obj()

        self.mono_font = lv.font_unscii_16

        # create labels for our 4 lines of text:
        self.lines = [ self.text_line(0,17),
                      self.text_line(1,17),
                      self.text_line(2,17),
                      self.text_line(3,17)]

        # And a label above the top line, to be shown when there is an input error.
        self.error = self.text_line(0,10)
        self.error.add_flag(HIDDEN)
        self.error.set_style_text_align(lv.TEXT_ALIGN.LEFT, 0)
        self.error.set_style_text_color(red, lv.PART.SELECTED)
        self.index = 3

        # current_line is normally pointing to the last/bottom line of text
        self.current_line = self.lines[self.index]
        # we use lvgl selection and an empty space for a cursor - empty label can't have a selection
        self.current_line.set_text(' ')


        lv.screen_load(self.scr)
        #self.grp = lv.group_create()
        self.k = KeypadInterface()

        if (event_loop.is_running()):
            self.event_loop = event_loop.current_instance()
        else:
            self.event_loop = event_loop()

        self.event_loop.refresh_cb = scan_keys


    def text_line(self, index, len=17, text=""):
        """ Create a single label object to represent 1 line of text on the display. """
        line = lv.label(self.scr)
        line.set_style_text_font(self.mono_font, 0)
        line.set_style_text_align(lv.TEXT_ALIGN.RIGHT, 0)
        line.set_style_text_color(white, lv.PART.SELECTED)
        line.set_style_bg_color(blue, lv.PART.SELECTED)
        line.set_pos(0, 2 + (index * 17))
        line.set_width(16*len)
        line.set_text(text)

        return line

    def clear(self, linenum):
        if linenum == self.index:
            M1 = 0
            if self.current_line.get_text() == "":
                linenum = linenum - 1
                M2 = 0
        elif linenum == 1:
            M3 = 0
        self.lines[linenum].set_text(" ")
        self.lines[linenum].set_text_selection_start(0)
        self.lines[linenum].set_text_selection_end(1)

    def send_key(self, scancode=None, keycode=None, symbol=None, value=None, shifted=None, keydown=1):
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
            method = getattr(self, symbol, None)
            if method is not None:
                method(keydown)
            elif keydown:
                if self.shifted and shifted is not None:
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
        current_symbol = current_text[-1:]

        if (current_text == " " or
            (current_symbol in self.operators and value in self.operators)
        ):
            current_text = current_text[0:-1] + value
            current.set_text(current_text)
        else:
            current.ins_text(pos, value)
            self.update_cursor(current)


    def update_cursor(self, current_line=None):
        if current_line is None:
            current_line = self.current_line
        line_length = len(current_line.get_text())
        if line_length < 1:
            return
        current_line.set_text_selection_start(line_length-1);
        current_line.set_text_selection_end(line_length);


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

    def tokenize(self, text):
        return tok.match(text)

    def ENTER(self, keydown):
        if not keydown:
            return
        if self.shifted:
            self.insert_text("=")
        global M1, M2, M3, M4
        lines = len(self.lines)

        try:
            orig_expr = self.current_line.get_text()
            expr = self.tokenize(orig_expr)
            out = []
            groups = None
            if expr:
                groups = expr.groups()
            if not groups:
                groups = [orig_expr]
            for group in groups:
                if group is None:
                    continue
                if group[0] not in ("+","/","*","-","M"):
                    out.append('DecimalNumber("'+group+'")')
                else:
                    out.append(group)
            expr = "".join(out)
            if (expr == "" or expr[0] in ("+","/","*","-")):
                expr = "M1" + expr
            res = eval(str(expr))
            if type(res) is float:
                res = DecimalNumber(str(res))
            elif type(res) is not DecimalNumber:
                res = DecimalNumber(res)
            M4 = M3
            M3 = M2
            M2 = M1
            M1 = res
            self.hide_err()
            self.lines[lines-4].set_text(numformat(M3))
            self.lines[lines-3].set_text(numformat(M2))
            self.lines[lines-2].set_text(numformat(res))
            self.clear(self.index)
        except Exception as e:
            self.show_err(e)

        #self.send_key(keymap.ENTER)

    def F17(self, keydown):
        self.shifted = keydown

    def F18(self, keydown):
        if keydown:
            self.clear(self.index)

    def F19(self, keydown):
        if keydown:
            self.current_line.set_text(self.current_line.get_text()[0:-1])
            self.update_cursor()

    def pgdn(self):
        self.send_key(keymap.PGDN)

    def pgup(self):
        self.send_key(keymap.PGUP)


def scan_keys():
    cols = Calc.cols
    rows = Calc.rows
    callbacks = Calc.callbacks
    state = Calc.state

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
            rows[r].init(mode=Pin.OUT, pull=None, value=0)
            time.sleep_us(10)
            rows[r].init(mode=Pin.IN, pull=Pin.PULL_DOWN)
            # end Errata workaround


            # read the value from the row's GPIO pin
            value = rows[r].value()
            time.sleep_us(10)

            # the state array tracks which keys were pressed the last time we scanned the matrix.
            if state[scancode] != value:
                # Only react to key state that has changed since the last scan
                key = keys[scancode]
                # TODO: We couold add key repeating for held down keys here. Currently we only report
                # key down and key up events.

                print(scancode, key, value)
                if (key is not None):
                    try:
                        if len(key) > 3: # some keys have a shifted alternate key code
                            shifted_key = key[3]
                        else:
                            shifted_key = None

                        # key behavior is defined in the app class, just pass the raw data to app.send_key
                        app.send_key(scancode, key[0], key[1], key[2], shifted_key, value)
                    except Exception as e:
                        print(e)
                # record the state of each key
                state[scancode] = value

        # turn off this column and move on to the next
        cols[c].off()


from machine import Pin
from array import array
import time
from settimeout import setTimeout
# This keypad has a contiguous series of keys (KEYPAD_KEY_IDS) starting at 0x4A:
_KEYPAD_KEY_OFFS = const(0x4A)

# See HID Usages and Descriptions 1.4, section 10 Keyboard/Keypad Page (0x07)
#
# https://usb.org/sites/default/files/hut1_21.pdf
#

# these const names are defined for convenience and easier identification in
# the rest of the codebase when referencing keys by their int keycode.
# The mapping of keycodes to the physical key matrix is handled with the keys
# list defined below.

HOME = const(0x4A)
PGUP = const(0x4B)
DEL = const(0x4C)
END = const(0x4D)
PGDN = const(0x4E)
RIGHT = const(0x4F)
LEFT = const(0x50)
DOWN = const(0x51)
UP = const(0x52)
NUMLOCK = const(0x53)
DIVIDE = const(0x54)
MULTIPLY = const(0x55)
SUBTRACT = const(0x56)
ADD = const(0x57)
ENTER = const(0x58)
KP1 = const(0x59)
KP2 = const(0x5A)
KP3 = const(0x5B)
KP4 = const(0x5C)
KP5 = const(0x5D)
KP6 = const(0x5E)
KP7 = const(0x5F)
KP8 = const(0x60)
KP9 = const(0x61)
KP0 = const(0x62)
PERIOD = const(0x63)
EQUAL = const(0x67)
F13 = const(0x68)
F14 = const(0x69)
F15 = const(0x6A)
F16 = const(0x6B)
F17 = const(0x6C)
F18 = const(0x6D)
F19 = const(0x6E)
F20 = const(0x6F)

RELEASE = const(0)
PRESS = const(1)
LONGPRESS = const(2)

# rows and cols contain all of the gpio pins that are connected to
# the key matrix. Rows are inputs and columns are outputs.
# When scanning the keys, we enable each column one by one, then read all
# rows to see which keys are pressed in the given column.
# Note: We are using pulldown on the rows and this is problematic on the
# RP2350, however, a workaround has been implemented in the key scanning code.

rows = [
        Pin(10, Pin.IN, Pin.PULL_DOWN),
        Pin(11, Pin.IN, Pin.PULL_DOWN),
        Pin(12, Pin.IN, Pin.PULL_DOWN),
        Pin(13, Pin.IN, Pin.PULL_DOWN),
        Pin(14, Pin.IN, Pin.PULL_DOWN),
        Pin(15, Pin.IN, Pin.PULL_DOWN)
]

cols = [ Pin(9, Pin.OUT),
        Pin(16, Pin.OUT),
        Pin(17, Pin.OUT),
        Pin(18, Pin.OUT),
        Pin(19, Pin.OUT)
]


class KeyboardState:
  state = array('b', [0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0])
  layer = 0
  instance = None

  def __init__(self):
    self.app = None
    pass

  @classmethod
  def singleton(cls):
    if cls.instance is None:
      cls.instance = KeyboardState()
    return cls.instance

  def action(self, key, action, symbol=None):
    if symbol is None:
      symbol = key.symbol
    if self.app is not None:
      self.app.action(key, action, symbol)


keyboard = KeyboardState.singleton()

class Key:
  lower_key = None

  def __init__(self, scancode, name, symbol, shifted=None):
    global keyboard
    self.keyboard = keyboard
    self.scancode = scancode
    self.name = name
    self.symbol = symbol
    self.shifted = shifted
    self.keydown=0
    self.press_cb = None
    self.release_cb = None

  def set_lower(self, key):
    self.lower_key = key

  def update(self, keydown):
    if self.keydown != keydown:
      self.keydown = keydown
      if keydown == 0:
        self.on_release()
      else:
        self.on_press()

  def on_press(self):
    if self.press_cb is not None:
      self.press_cb()
    elif self.lower_key is not None:
      self.lower_key.on_press()

  def on_release(self):
    if self.release_cb is not None:
      self.release_cb()
    elif self.lower_key is not None:
      self.lower_key.on_release()

  def __getitem__(self, index):
    if index==0:
      return self.scancode
    elif index==1:
      return self.name
    elif index==2:
      return self.symbol
    elif index==3:
      return self.shifted
    elif isinstance(index, slice):
      tmp = (self.scancode, self.name, self.symbol, self.shifted)
      start, stop, step = index.indices(len(self))
      return tmp[start:stop:step]
    else:
      raise(IndexError('Key: Invalid index'))

  def __len__(self):
    if self.shifted is not None:
      return 4
    else:
      return 3

  def __repr__(self):
    return f"Key({self.scancode}, {self.name}, {self.symbol})"

class ShiftKey(Key):

  def __init__(self, scancode, name, symbol, layer=1):
    super().__init__(scancode, name, symbol)
    self.layer = layer

  def on_press(self):
    self.keyboard.layer += self.layer

  def on_release(self):
    self.keyboard.layer -= self.layer

class ToggleKey(Key):
  def __init__(self, scancode, name, symbol):
    super().__init__(scancode, name, symbol)

  def get_state(self):
    return self.state

  def on_release(self):
    self.state = not self.state
    setattr(self.keyboard, self.name, self.state)

class LongPressKey(Key):
  def __init__(self, scancode, name, symbol, long_press_sym):
    super().__init__(scancode, name, symbol)
    self.long_press_sym = long_press_sym

  def on_press(self):
    def callback():
      if self.keydown:
        keyboard.action(self, LONGPRESS, self.long_press_sym)
    keyboard.action(self, PRESS, self.symbol)
    setTimeout(1, callback)

  def on_release(self):
    keyboard.action(self, RELEASE)

# Key metadata.  see ../docs/keymap.md for some notes about key mapping.
keys = [
  #row 1
  ShiftKey(F17, 'F17', "SHIFT", 1),        # 0
  Key(KP0, 'KP0', "0"),            # 1
  None,                         # 2 Not connected
  Key(PERIOD, 'PERIOD', '.'),      # 3
  Key(ENTER, 'ENTER', "\n", "="),  # 4
  # row 2
  Key(F18, 'F18', "CLEAR"),        # 5
  Key(KP1, "KP1", "1"),            # 6
  Key(KP2, "KP2", "2"),            # 7
  Key(KP3, "KP3", "3"),            # 8
  None,                         # 9 Not connected
  # row 3
  Key(F19, "F19", "BACKSPACE", "RECALL"), # 10
  Key(KP4, "KP4", "4"),            # 11
  Key(KP5, "KP5", "5"),            # 12
  Key(KP6, "KP6", "6"),            # 13
  None,                         # 14 Not connected
  # row 4
  None,                         # 15 Not connected
  Key(KP7, "KP7", "7"),            # 16
  Key(KP8, "KP8", "8"),            # 17
  Key(KP9, "KP9", "9"),            # 18
  Key(ADD, "ADD", "+"),            # 19
  #row 5
  None,                         # 20 Not connected
  ToggleKey(NUMLOCK, "NUMLOCK", "NumLock"),# 21
  Key(DIVIDE, "DIVIDE", "/"),        # 22
  Key(MULTIPLY, "MULTIPLY", "*"),    # 23
  Key(SUBTRACT, "SUBTRACT", "-"),    # 24
  # row 6:
  None,                           # 25 Not connected
  Key(F13, "F13", "M1"),             # 26
  Key(F14, "F14", "M2"),             # 27
  LongPressKey(F15, "F15", "M3", "STORE"),             # 28
  LongPressKey(F16, "F16", "M4", "STORE"),             # 29
]

def lookup_key(keyid, field=0):
  """ look up a key by any key metadata field value.
  keyid is the value to match
  field is the index of the field to search.
  0 = integer: the key code
  1 = string: the key name
  2 = string: the primary key symbol
  3 = string: the shifted key symbol
  """
  for key in keys:
    if field in key and key[field] == keyid:
      return key
  return None



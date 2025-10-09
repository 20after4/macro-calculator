# See HID Usages and Descriptions 1.4, section 10 Keyboard/Keypad Page (0x07)
#
# https://usb.org/sites/default/files/hut1_21.pdf
#
# This keypad has a contiguous series of keys (KEYPAD_KEY_IDS) starting at 0x4A:
_KEYPAD_KEY_OFFS = const(0x4A)

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

keys = [
  (F17, 'F17', "M5"),      # 0
  (KP0, 'KP0', "0"),       # 1
  None,                    # 2 Not connected
  (PERIOD, 'PERIOD', '.'), # 3
  (ENTER, 'ENTER', "\n", "="),  # 4
  (F18, 'F18', "END"), # 5
  (KP1, "KP1", "1"),  # 6
  (KP2, "KP2", "2"),  # 7
  (KP3, "KP3", "3"),  # 8
  None,               # 9 Not connected
  (F19, "F19", "HOME"), # 10
  (KP4, "KP4", "4"),  # 11
  (KP5, "KP5", "5"),  # 12
  (KP6, "KP6", "6"),  # 13
  None,               # 14 Not connected
  None,               # 15 Not connected
  (KP7, "KP7", "7"),  # 16
  (KP8, "KP8", "8"),  # 17
  (KP9, "KP9", "9"),  # 18
  (ADD, "ADD", "+"),  # 19
  None,               # 20 Not connected
  (NUMLOCK, "NUMLOCK", "NumLock"),# 21
  (DIVIDE, "DIVIDE", "/"),        # 22
  (MULTIPLY, "MULTIPLY", "*"),    # 23
  (SUBTRACT, "SUBTRACT", "-"),    # 24
  None,               # 25 Not connected
  (F13, "F13", "M1"), # 26
  (F14, "F14", "M2"), # 27
  (F15, "F15", "M3"), # 28
  (F16, "F16", "M4"), # 29
]

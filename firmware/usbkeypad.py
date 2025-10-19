import usb.device
from usb.device.hid import HIDInterface


_INTERFACE_PROTOCOL_KEYBOARD = const(0x01)

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



class KeypadInterface(HIDInterface):

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

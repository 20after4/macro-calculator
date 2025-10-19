from st77xx import St7789
from machine import Pin, Signal, SPI
sckpin = Pin(2, Pin.OUT)
mosipin = Pin(3, Pin.OUT)
spi = SPI(0, baudrate=24000000, polarity=0, phase=0, sck=sckpin, mosi=mosipin)
lcd = St7789(rot=1, res=(76,284), spi=spi, cs=5, dc=6, rst=7, factor=8, bgr=False)
led = Pin(25, Pin.OUT)

from machine import Timer
import time

timeouts = []
def setTimeout(seconds, callback, arg=None):
    timeouts.append((time.ticks_ms(), seconds*1000, callback, arg))

def PeriodicInterrupt(timer):
    global timeouts

    for i in range(len(timeouts)):
        t = timeouts[i]
        if time.ticks_diff(time.ticks_ms(), t[0]) >= t[1]:
            cb = t[2]
            if (t[3] is None):
                cb()
            else:
                cb(t[3])
            timeouts.remove(t)


timer = Timer(period=1000, mode=Timer.PERIODIC, callback=PeriodicInterrupt)

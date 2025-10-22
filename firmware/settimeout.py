from machine import Timer
import time

# Fire and forget scheduling of callbacks,
# something sort of like setTimeout from JavaScript.

timeouts = [None, None, None, None]

tid = 0

def get_id():
    global tid, tlen
    tid += 1
    tlen = len(timeouts)
    tindex = tid % tlen
    while timeouts[tindex] != None:
        tid += 1
        tindex = tid % tlen
        if tindex == tlen:
            timeouts.append(None)


    if tid > 1000:
        tid = tindex
    return tid, tindex


def setTimeout(seconds, callback, arg=None):
    global timeouts
    tid, tindex = get_id()
    timeout = (time.ticks_ms(), seconds*1000, callback, arg, tid)
    timeouts[tindex] = timeout
    return tid

def cancelTimeout(tid):
    tindex = tid % len(timeouts)
    timeout = timeouts[tindex]
    print("cancelTimeout", tid, timeout)
    if timeout is not None and timeout[4] == tid:
        timeouts[tindex] = None
        return True
    else:
        return False

def PeriodicInterrupt(timer):
    global timeouts

    for i in range(len(timeouts)):
        t = timeouts[i]
        if t is None:
            continue
        if time.ticks_diff(time.ticks_ms(), t[0]) >= t[1]:
            timeouts[i] = None
            cb = t[2]
            if (t[3] is None):
                cb()
            else:
                cb(t[3])


timer = Timer(period=1000, mode=Timer.PERIODIC, callback=PeriodicInterrupt)

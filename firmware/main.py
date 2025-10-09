import machine, sys, time
import calc

try:
    calc.app = calc.Calc()
except Exception as e:
    sys.print_exception(e)
    time.sleep(5)
    machine.reset()

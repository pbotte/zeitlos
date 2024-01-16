# Submit status of pins 0,1 via Serial as JSON string
# bonus: build in led lights up on any incoming edge detected

from machine import Timer
from machine import Pin
import json

p0 = Pin(0, Pin.IN, Pin.PULL_UP)
p1 = Pin(1, Pin.IN, Pin.PULL_UP)
pled = Pin(25, Pin.OUT) #use Pin 'LED' for Pico WLAN

time_light = 0

def mycallback(p):
    global time_light
    print(json.dumps({'Pin0': p0.value(), 'Pin1': p1.value()}))
    if time_light > 0:
        time_light -= 1
    else:
        pled.off()

def light_up(p):
    global time_light
    pled.on()
    time_light = 1

p0.irq(trigger=Pin.IRQ_FALLING | Pin.IRQ_RISING, handler=light_up)
p1.irq(trigger=Pin.IRQ_FALLING | Pin.IRQ_RISING, handler=light_up)

tim = Timer(period=1000, mode=Timer.PERIODIC, callback=mycallback)

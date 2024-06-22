import sys
import myconfig
import time
import machine
import scale_assignment
import download_helper
import eink_update
import mqtt_helper
import wlan_helper

print("Setup starts.\n")

#start watchdog and make it available for the download and eink modules
wdt = machine.WDT(timeout=8300)
download_helper.my_wdt = wdt
eink_update.my_wdt = wdt

#Connect via WLAN
wlan_helper.connect(wdt)
wdt.feed()

#Activate the onboard buttons 
input_pins = [machine.Pin(i, machine.Pin.IN, machine.Pin.PULL_UP) for i in (15,17)]  # Adjust range according to your board
last_pin_action_queue = None
def PinId(pin):
    return int(str(pin)[8:10].rstrip(","))
def pin_callback(pin):
    print(f"Pin {pin} changed to {pin.value()}")
    global last_pin_action_queue
    last_pin_action_queue = PinId(pin)
for pin in input_pins:
    print(f"Pin {pin} registered")
    pin.irq(trigger=machine.Pin.IRQ_RISING, handler=pin_callback)
wdt.feed()

#read in the configuration, which should be currently displayed
scale_assignment.read_file()
mqtt_helper.assigned_scaleid = scale_assignment.assigned_scale
mqtt_helper.assigned_product_id = scale_assignment.assigned_productid
mqtt_helper.assigned_product_hash = scale_assignment.product_hash
wdt.feed()

#connect via MQTT
mqtt_helper.reconnect_MQTT(scaleid=scale_assignment.assigned_scale, productid=179)
wdt.feed()

print("script fully loaded, entering loop.\n\n\n")

#start the main loop
#data via mqtt will come in here
loop_count = 0
while True:
    #checks for incoming packages, do it often
    if loop_count % 2 == 0: mqtt_helper.mqtt_keep_checking()
    
    #if no mqtt connection: try to reconnect every 1 second
    if loop_count % 10 == 0: mqtt_helper.reconnect_MQTT(scaleid=scale_assignment.assigned_scale, productid=mqtt_helper.assigned_product_id)

    #pings the mqtt-server, do it only every few seconds
    if loop_count % 50 == 0: mqtt_helper.mqtt_isconnected()
    
    #give some status update via mqtt every 1 min
    if loop_count % 600 == 0: mqtt_helper.report_status({'scaleid': scale_assignment.assigned_scale,
                                                         'productid': scale_assignment.assigned_productid,
                                                         'product_hash': scale_assignment.product_hash})
    
    #process mqtt topics in this main loop:
    if mqtt_helper.mqtt_queue == 1:
        download_helper.download_img(scaleid=scale_assignment.assigned_scale)
        wdt.feed()
        mqtt_helper.mqtt_keep_checking()
        eink_update.update_from_file()
        mqtt_helper.reset_queue()
        

    if last_pin_action_queue:
        if last_pin_action_queue == 15:
            download_helper.download_config(myconfig.CLIENT_UID)
            wdt.feed()
            scale_assignment.read_file()
        if last_pin_action_queue == 17:
            download_helper.download_img(scaleid=scale_assignment.assigned_scale)
            wdt.feed()
            mqtt_helper.mqtt_keep_checking()
            eink_update.update_from_file()
        last_pin_action_queue = None


    #if everything is okay, do feed the watchdog
    if wlan_helper.wlan.isconnected() and mqtt_helper.mqtt_connected:
        wdt.feed()

    loop_count += 1
    time.sleep(0.1)

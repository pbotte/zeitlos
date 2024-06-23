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
scale_assignment.print_status()
wdt.feed()


print("\n\nDownload the image file if scaleid is defined:")
if scale_assignment.assigned_scale:
    download_helper.download_img(scaleid=scale_assignment.assigned_scale)
else:
    print("no scaleid defined.")
wdt.feed()

print("\n\nRefresh eink image during first boot.")
eink_update.update_from_file()


print("script fully loaded, entering loop.\n\n\n")

#start the main loop
#data via mqtt will come in here
loop_count = 0
while True:
    #if no mqtt connection: try to reconnect every 1 second
    mqtt_helper.reconnect_MQTT()

    #checks for incoming packages, do it often
    if loop_count % 2 == 0:
        mqtt_helper.mqtt_keep_checking()
    
    #pings the mqtt-server, do it only every few seconds
    if loop_count % 50 == 0:
        mqtt_helper.mqtt_isconnected()
    
    #give some status update via mqtt every 1 min
    if loop_count % 600 == 0:
        mqtt_helper.report_status()
    
    #process mqtt topics in this main loop:
    if mqtt_helper.mqtt_queue == 1:
        mqtt_helper.reset_queue()
        download_helper.download_img(scaleid=scale_assignment.assigned_scale)
        wdt.feed()
        mqtt_helper.mqtt_keep_checking()
        eink_update.update_from_file()
    if mqtt_helper.mqtt_queue == 2:
        mqtt_helper.reset_queue()
        print(f"Got a new scaleid from MQTT. Next: write to file and restart.")
        scale_assignment.write_file(scaleid=mqtt_helper.via_mqtt_received_scaleid)
        print("Reset in 1 second.")
        time.sleep(1)
        machine.reset()

    
    if loop_count % 20 == 0:
        if scale_assignment.assigned_scale is None:
            print(f"No Scale assigned yet. Do so by pressing key0 or via MQTT {myconfig.mqtt_clientname}/config/scaleid/set")
        else:
            print(f"{scale_assignment.assigned_scale=} {scale_assignment.assigned_productid=} {scale_assignment.product_hash=} {mqtt_helper.via_mqtt_received_scaleid=} {mqtt_helper.via_mqtt_received_productid=} {mqtt_helper.via_mqtt_received_hash=}")

            # 1st: productid changed via MQTT, reconfigure to get the hash via MQTT as well
            if scale_assignment.assigned_productid is None and mqtt_helper.via_mqtt_received_productid and \
                mqtt_helper.via_mqtt_received_hash is None:
                print("\n\nProductID not on disk AND no hash received yet. Add hash to subscribed topics:")
                mqtt_helper.disconnect()
                wdt.feed()
                mqtt_helper.reconnect_MQTT()
                wdt.feed()

            elif mqtt_helper.via_mqtt_received_productid and mqtt_helper.via_mqtt_received_hash and \
                (   \
                    str(scale_assignment.assigned_productid) != str(mqtt_helper.via_mqtt_received_productid)
                ):
                print("\n\nProductID has changed:")
                wdt.feed()
                print("Start refresh. Download and refresh image:")
                # download image from webserver and refresh
                download_helper.download_img(scaleid=scale_assignment.assigned_scale)
                wdt.feed()
                mqtt_helper.mqtt_keep_checking()
                eink_update.update_from_file()
                wdt.feed()
                scale_assignment.write_file(scaleid=scale_assignment.assigned_scale,
                                            productid=mqtt_helper.via_mqtt_received_productid,
                                            myhash=None)
                wdt.feed()
                print("Reconnect MQTT to update for possibe new productid:")
                mqtt_helper.disconnect()
                wdt.feed()
                mqtt_helper.reconnect_MQTT()
                print("Completed.\n\n\n")
                
            elif mqtt_helper.via_mqtt_received_productid and mqtt_helper.via_mqtt_received_hash and \
                 scale_assignment.product_hash and \
                (   \
                    str(scale_assignment.product_hash) != str(mqtt_helper.via_mqtt_received_hash) \
                ):
                print("\n\nhash has changed:")
                wdt.feed()
                print("Start refresh. Download and refresh image:")
                # download image from webserver and refresh
                download_helper.download_img(scaleid=scale_assignment.assigned_scale)
                wdt.feed()
                mqtt_helper.mqtt_keep_checking()
                eink_update.update_from_file()
                wdt.feed()
                scale_assignment.write_file(scaleid=scale_assignment.assigned_scale,
                                            productid=mqtt_helper.via_mqtt_received_productid,
                                            myhash=mqtt_helper.via_mqtt_received_hash)
                wdt.feed()
                print("Completed.\n\n\n")

            #product id change and no hash yet on file
            elif scale_assignment.product_hash is None and mqtt_helper.via_mqtt_received_hash:
                print("\n\nhash on disk was None and some hash has been received via MQTT. Store it.")
                wdt.feed()
                scale_assignment.write_file(scaleid=scale_assignment.assigned_scale,
                                            productid=scale_assignment.assigned_productid,
                                            myhash=mqtt_helper.via_mqtt_received_hash)
                wdt.feed()
                print("Completed.\n\n\n")





    if last_pin_action_queue:
        if last_pin_action_queue == 15: #key0
            v = download_helper.get_config(myconfig.CLIENT_UID)
            wdt.feed()
            if v and v != scale_assignment.assigned_scale:
                print(f"Got a new scaleid from webserver. Next: write to file and restart.")
                scale_assignment.write_file(scaleid=v)
                print("Reset in 1 second.")
                time.sleep(1)
                machine.reset()
        if last_pin_action_queue == 17: #key1
            # download image from webserver and refresh
            download_helper.download_img(scaleid=scale_assignment.assigned_scale)
            wdt.feed()
            mqtt_helper.mqtt_keep_checking()
            eink_update.update_from_file()
            scale_assignment.write_file(scaleid=scale_assignment.assigned_scale,
                                        productid=scale_assignment.assigned_productid, #mqtt_helper.via_mqtt_received_productid,
                                        myhash=None) #mqtt_helper.via_mqtt_received_hash)
        last_pin_action_queue = None


    #if everything is okay, do feed the watchdog
    if wlan_helper.wlan.isconnected() and mqtt_helper.mqtt_connected:
        wdt.feed()
    else:
        print(f"ERROR: WLAN connectivity: {wlan_helper.wlan.isconnected()}     MQTT Connectivity: {mqtt_helper.mqtt_connected}")

    loop_count += 1
    time.sleep(0.1)

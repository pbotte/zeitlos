#!/usr/bin/python3

import paho.mqtt.client as paho
import json
import time
from datetime import datetime
import logging
import argparse
import queue, traceback
import signal
import sys
import math
import re

logging.basicConfig(level=logging.WARNING, format='%(asctime)-6s %(levelname)-8s  %(message)s')
logger = logging.getLogger("Shop Track Collector")

parser = argparse.ArgumentParser(description='Shop Track Collector')
parser.add_argument("-v", "--verbosity", help="increase output verbosity", default=0, action="count")
parser.add_argument("-b", "--mqtt-broker-host", help="MQTT broker hostname. default=localhost", default="localhost")
args = parser.parse_args()
logger.setLevel(logging.WARNING-(args.verbosity * 10 if args.verbosity <= 2 else 20))

debug = True if args.verbosity>1 else False

mqtt_client_name = "shop-track-collector"

def on_connect(client, userdata, flags, rc):
    if rc == 0:
        logger.info("MQTT connected OK. Return code "+str(rc))
        client.subscribe("homie/+/tof/actreading")
        client.subscribe(f"homie/{mqtt_client_name}/reference")
        client.subscribe(f"homie/{mqtt_client_name}/reference/set")
        client.subscribe("homie/shop_controller/shop_status")
        logger.debug("MQTT: Subscribed to all topics")

        client.publish(f"homie/{mqtt_client_name}/state", '1', qos=1, retain=True)
    else:
        logger.error("Bad connection. Return code="+str(rc))

def on_disconnect(client, userdata, rc):
    if rc != 0:
        logger.warning("Unexpected MQTT disconnection. Will auto-reconnect")

mqtt_queue=queue.Queue()
def on_message(client, userdata, message):
    global mqtt_queue
    try:
        mqtt_queue.put(message)
        m = message.payload.decode("utf-8")
        logger.debug("MQTT message received. Topic: "+message.topic+" Payload: "+m)
    except Exception as err:
        traceback.print_tb(err.__traceback__)


#connect to MQTT broker
client = paho.Client(mqtt_client_name)
client.on_message = on_message
client.on_connect = on_connect
client.on_disconnect = on_disconnect
client.enable_logger(logger) #info: https://www.eclipse.org/paho/clients/python/docs/#callbacks
logger.info("connecting to broker: "+args.mqtt_broker_host+". If it fails, check whether the broker is reachable. Check the -b option.")

# start with MQTT connection and set last will
logger.info(f"mqtt_client_name: {mqtt_client_name}")
client.will_set(f"homie/{mqtt_client_name}/state", '0', qos=1, retain=True)
client.connect(args.mqtt_broker_host)
client.loop_start() #start loop to process received messages in separate thread
logger.debug("MQTT loop started.")

##############################################################################
##############################################################################
main_loop_var = True
def signal_handler(sig, frame):
    global main_loop_var
    logger.info(f"Program terminating. Sending correct /state ... (this takes 1 second)")

    main_loop_var = False
#    sys.exit(0)

signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)
##############################################################################

values={}
values_reference = {}
number_pixels_above_ref = None

time_last_message_missing_data = 0 #to not print to often msg about missing data

while main_loop_var:
    while not mqtt_queue.empty():
        message = mqtt_queue.get()
        if message is None:
            continue
        logger.debug(f"Process queued MQTT message now: {str(message.payload.decode('utf-8'))}")

        try:
            m = message.payload.decode("utf-8")
        except Exception as err:
            traceback.print_tb(err.__traceback__)
        logger.debug("Topic: "+message.topic+" Message: "+m)

        msplit = re.split("/", message.topic)

        if message.topic.lower() == f"homie/{mqtt_client_name}/reference":
            logger.info("reference received")
            values_reference = json.loads(m)

        if message.topic.lower() == "homie/shop_controller/shop_status":
            if int(m) ==2:
                logger.info("shop_status == 2 received, saving reference.")
                values_reference = values.copy()
                client.publish(f"homie/{mqtt_client_name}/reference", json.dumps(values_reference), qos=1, retain=True)
        if message.topic.lower() == "homie/shop-track-collector/reference/set":
            logger.info("saving reference.")
            values_reference = values.copy()
            client.publish(f"homie/{mqtt_client_name}/reference", json.dumps(values_reference), qos=1, retain=True)

        if msplit[2] == "tof" and msplit[3] == "actreading":
            values[msplit[1].lower()] = json.loads(m)


    #check start
    res = 0
    for vr in values_reference.items():
        if vr[0] in values:
            compare_list_act = values[vr[0]]
            compare_list_ref = vr[1]
            for i in range(len(compare_list_act)):
                if compare_list_act[i] is None or compare_list_ref[i] is None:
                    #pixel ist ggf. ausgefallen
                    pass
                else:
                    if (compare_list_ref[i] - compare_list_act[i]) > 300:
                        logger.debug(f"The following pixel is below reference: {vr[0]} {i}")
                        res += 1
        else:
            if time.time()-time_last_message_missing_data > 60:
                logger.warning(f"Reference values for {vr[0]} present, but no actual data (yet). This is a normal behaviour after a fresh restart until all data from all sensors got received.")
                time_last_message_missing_data = time.time()
    logger.debug(f"Number of pixels different from reference: {res=}")
    if number_pixels_above_ref != res: 
        number_pixels_above_ref = res
        logger.info(f"Report new number of pixels different from reference. Send MQTT message: {number_pixels_above_ref=}")
        client.publish(f"homie/{mqtt_client_name}/pixels-above-reference", number_pixels_above_ref, qos=1, retain=True)
    #check stop

    time.sleep(0.1)


# Terminating everything
logger.info(f"Terminating. Cleaning up.")

# send state=0
client.publish(f"homie/{mqtt_client_name}/state", '0', qos=1, retain=True)

time.sleep(1) #to allow the published message to be delivered.

client.loop_stop()
client.disconnect()

logger.info("Programm stopped.")

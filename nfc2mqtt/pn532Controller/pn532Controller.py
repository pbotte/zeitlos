#!/usr/bin/python3

import paho.mqtt.client as paho 
import json
import time
from datetime import datetime
import serial
import logging
import argparse
import sys
import re
import os
import yaml #pip3 install pyyaml
import struct #to unpack 4 bytes to int
import numpy as np # for variance

logging.basicConfig(level=logging.WARNING,
                    format='%(asctime)-6s %(levelname)-8s  %(message)s')
logger = logging.getLogger("PN532 chip receiver")

parser = argparse.ArgumentParser(
    description='MQTT to PN532 converter.')
parser.add_argument("-v", "--verbosity",
                    help="increase output verbosity", default=0, action="count")
parser.add_argument("-b", "--mqtt-broker-host",
                    help="MQTT broker hostname. default=localhost", default="localhost")
parser.add_argument("-t", "--watchdog-timeout",
                    help="timeout in seconds for the watchdog. default=1h", default=100*60*60, type=int)
parser.add_argument("serial_device_name",
                    help="Serial port used, eg /dev/ttyUSB0", type=str)
args = parser.parse_args()
logger.setLevel(logging.WARNING-(args.verbosity *
                                 10 if args.verbosity <= 2 else 20))

logger.info("Watchdog timeout (seconds): "+str(args.watchdog_timeout))
logger.info('Use the following Serial-Device: '+str(args.serial_device_name))

mqtt_client_name = "unconfiguredPN5322MQTT"

def on_connect(client, userdata, flags, rc):
    if rc==0:
        logger.info("MQTT connected OK. Return code "+str(rc) )
        logger.debug("MQTT: Subscribed to all topics")
    else:
        logger.error("Bad connection. Return code="+str(rc))

def on_disconnect(client, userdata, rc):
    if rc != 0:
        logger.warning("Unexpected MQTT disconnection. Will auto-reconnect")

client = paho.Client(mqtt_client_name)
client.on_connect = on_connect
client.on_disconnect = on_disconnect
client.enable_logger(logger) # info: https://www.eclipse.org/paho/clients/python/docs/#callbacks
logger.info("Connecting to broker "+args.mqtt_broker_host)

#start with MQTT connection and set last will
logger.info("mqtt_client_name: {}".format(mqtt_client_name))
client.will_set("homie/"+mqtt_client_name+"/state", 'offline', qos=1, retain=True)
client.connect(args.mqtt_broker_host)
client.loop_start()
logger.info("MQTT loop started.")
client.publish("homie/"+mqtt_client_name+"/state", 'online', qos=1, retain=True)


#Connect normally
ser = serial.Serial(args.serial_device_name, 115200, timeout=0.5)

WatchDogCounter = args.watchdog_timeout
charSet = bytearray()
numberMessagesRecv = 0

status = None

while (WatchDogCounter > 0):

    if ser.inWaiting() > 0:
        line = ser.readline().decode("utf-8").strip()
        
        logger.info("Serial.readline(): {}".format(line) )

        t = None
        try:
          t = json.loads(line)
          t["time"]=time.time()
        except:
          logger.error("An error accoured when converting the JSON string.")
          sys.exit()

        if t is not None:
            try:
                newStatus = 0
                topicStr = "status"
                if "cardUID" in t:
                    topicStr = "cardread"
                    newStatus = 1
                if newStatus != status:
                    client.publish("homie/"+mqtt_client_name+"/"+topicStr, json.dumps(t, sort_keys=True), qos = 1, retain=True)
                status = newStatus
                WatchDogCounter = args.watchdog_timeout
                numberMessagesRecv += 1
            except:
                logger.error("An error accoured when publishing the JSON string.")
                sys.exit()

    time.sleep(.01)
    WatchDogCounter -= 1

ser.close()

client.disconnect()
client.loop_stop()
logger.info("Program stopped.")

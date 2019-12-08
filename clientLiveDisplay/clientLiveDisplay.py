#!/usr/bin/python3

import paho.mqtt.client as paho 
import json
import time
from datetime import datetime
import serial
import logging
import argparse
import math
import sys
import re
import os #for replace the output file
import yaml #pip3 install pyyaml

logging.basicConfig(level=logging.WARNING,
                    format='%(asctime)-6s %(levelname)-8s  %(message)s')
logger = logging.getLogger("Client Live Display")

parser = argparse.ArgumentParser(
    description='Client Live Display.')
parser.add_argument("-v", "--verbosity",
                    help="increase output verbosity", default=0, action="count")
parser.add_argument("-b", "--mqtt-broker-host",
                    help="MQTT broker hostname. default=localhost", default="localhost")
parser.add_argument("-t", "--watchdog-timeout",
                    help="timeout in seconds for the watchdog. default=1h", default=100*60*60, type=int)
parser.add_argument("html_output_filepath",
                    help="File path into which the html file should be saved, eg /var/www/html", type=str)
args = parser.parse_args()
logger.setLevel(logging.WARNING-(args.verbosity *
                                 10 if args.verbosity <= 2 else 20))

logger.info("Watchdog timeout (seconds): "+str(args.watchdog_timeout))

mqtt_client_name = "unconfiguredClientLiveDisplay"

def on_connect(client, userdata, flags, rc):
    if rc==0:
        logger.info("MQTT connected OK. Return code "+str(rc) )
        client.subscribe("homie/"+mqtt_client_name+"/+/set")
        client.subscribe("homie/#")
        logger.debug("MQTT: Subscribed to all topics")
    else:
        logger.error("Bad connection. Return code="+str(rc))

def on_disconnect(client, userdata, rc):
    if rc != 0:
        logger.warning("Unexpected MQTT disconnection. Will auto-reconnect")

def on_message(client, userdata, message):
    global WatchDogCounter
    m = message.payload.decode("utf-8")
    try:
        j = json.loads(m)
        logger.info("Topic: "+message.topic+" JSON:"+str(j))
        try:
            msplit = re.split("/", message.topic)
            if len(msplit) == 4 and msplit[3].lower() == "set":
                if (msplit[2]=="cardread"):
                    #Do something
                    WatchDogCounter = args.watchdog_timeout
                    pass
                if (msplit[2]=="status"):
                    #Do something
                    pass
        except:
            logger.error("error in processing JSON message.")
    except:
        logger.error("error on converting MQTT message to JSON.")

client = paho.Client(mqtt_client_name)
client.on_connect = on_connect
client.on_message = on_message
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


WatchDogCounter = args.watchdog_timeout

while (WatchDogCounter > 0):
    filename = args.html_output_filepath+'/index.html'
    with open('skeleton.html', 'r') as file:
        with open(filename+'_temp', 'w+') as output_file:
            output_file.write(file.read().replace('{{{ZEIT}}}', datetime.now().strftime("%Y-%m-%d %H:%M:%S") ))
    os.replace(filename+'_temp', filename)
    logger.info("New file written to "+filename)

    time.sleep(1-math.modf(time.time())[0])
    WatchDogCounter -= 1

client.disconnect()
client.loop_stop()
logger.info("Program stopped.")

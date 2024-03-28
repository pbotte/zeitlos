#!/usr/bin/python3

import paho.mqtt.client as paho
import json
import time
from datetime import datetime
import logging
import argparse
import traceback
import math
import sys
import re
import os
import parse #pip install parse
import requests

logging.basicConfig(level=logging.WARNING,
                    format='%(asctime)-6s %(levelname)-8s  %(message)s')
logger = logging.getLogger("Display power control")

parser = argparse.ArgumentParser(description='Display power control')
parser.add_argument("-v", "--verbosity",
                    help="increase output verbosity", default=0, action="count")
parser.add_argument("-b", "--mqtt-broker-host",
                    help="MQTT broker hostname. default=localhost", default="localhost")
parser.add_argument("mqtt_client_name", help="MQTT client name")
args = parser.parse_args()
logger.setLevel(logging.WARNING-(args.verbosity * 10 if args.verbosity <= 2 else 20))

def on_connect(client, userdata, flags, rc):
    if rc == 0:
        logger.info("MQTT connected OK. Return code "+str(rc))
        client.subscribe("homie/"+args.mqtt_client_name+"/power/set")
        logger.debug("MQTT: Subscribed to all topics")
    else:
        logger.error("Bad connection. Return code="+str(rc))


def on_disconnect(client, userdata, rc):
    if rc != 0:
        logger.warning("Unexpected MQTT disconnection. Will auto-reconnect")

last_power_status = None
def on_message(client, userdata, message):
    global last_power_status
    try:
        m = message.payload.decode("utf-8")
        logger.info("Topic: "+message.topic+" Message: "+m)
        msplit = re.split("/", message.topic)

        if message.topic.lower() == "homie/"+args.mqtt_client_name+"/power/set":
          stream = os.popen("vcgencmd display_power "+m)
          output = stream.read().strip()
          logger.info("power_status changed")
          r=parse.parse("display_power={v:d}", output) #definition see: https://pypi.org/project/parse/
          if r:
            if last_power_status != r['v']:
              last_power_status = r['v']
              client.publish("homie/"+args.mqtt_client_name+"/power", r['v'], qos=1, retain=True)

    except Exception as err:
        traceback.print_tb(err.__traceback__)

client = paho.Client(paho.CallbackAPIVersion.VERSION1, args.mqtt_client_name)
client.on_connect = on_connect
client.on_message = on_message
client.on_disconnect = on_disconnect
client.enable_logger(logger)
logger.info("Connecting to broker "+args.mqtt_broker_host)

# start with MQTT connection and set last will
logger.info("mqtt_client_name: {}".format(args.mqtt_client_name))
client.will_set("homie/"+args.mqtt_client_name+"/state", 'offline', qos=1, retain=True)
client.connect(args.mqtt_broker_host)
client.loop_start()
logger.info("MQTT loop started.")
client.publish("homie/"+args.mqtt_client_name+"/state", 'online', qos=1, retain=True)


while True:
  # perform regular status checks
  stream = os.popen("vcgencmd display_power")
  output = stream.read().strip()
  r=parse.parse("display_power={v:d}", output) #definition see: https://pypi.org/project/parse/
  if r:
    if last_power_status != r['v']:
      last_power_status = r['v']
      client.publish("homie/"+args.mqtt_client_name+"/power", r['v'], qos=1, retain=True)
  time.sleep(10-math.modf(time.time())[0])  # make the loop run every second

client.disconnect()
client.loop_stop()
logger.info("Program stopped.")

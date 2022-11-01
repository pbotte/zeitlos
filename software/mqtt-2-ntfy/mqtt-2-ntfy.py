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
import parse #pip install parse
import requests

logging.basicConfig(level=logging.WARNING,
                    format='%(asctime)-6s %(levelname)-8s  %(message)s')
logger = logging.getLogger("MQTT 2 ntfy")

parser = argparse.ArgumentParser(description='MQTT 2 ntfy')
parser.add_argument("-v", "--verbosity",
                    help="increase output verbosity", default=0, action="count")
parser.add_argument("-b", "--mqtt-broker-host",
                    help="MQTT broker hostname. default=localhost", default="localhost")
args = parser.parse_args()
logger.setLevel(logging.WARNING-(args.verbosity * 10 if args.verbosity <= 2 else 20))

mqtt_client_name = "mqtt2ntfy"

def on_connect(client, userdata, flags, rc):
    if rc == 0:
        logger.info("MQTT connected OK. Return code "+str(rc))
        client.subscribe("homie/shop_controller/shop_status")
        logger.debug("MQTT: Subscribed to all topics")
    else:
        logger.error("Bad connection. Return code="+str(rc))


def on_disconnect(client, userdata, rc):
    if rc != 0:
        logger.warning("Unexpected MQTT disconnection. Will auto-reconnect")

shop_status_descr = {0: "Geräte Initialisierung", 1: "Bereit, Kein Kunde im Laden", 2: "Kunde authentifiziert/Waagen tara",
    3: "Kunde betritt/verlässt gerade den Laden", 4: "Möglicherweise: Einkauf finalisiert & Kunde nicht mehr im Laden",
    5: "Einkauf beendet und abgerechnet", 6: "ungenutzt",
    7: "Warten auf: Vorbereitung für nächsten Kunden", 8: "Technischer Fehler aufgetreten", 9: "Kunde benötigt Hilfe",
    10: "Laden geschlossen", 11: "Kunde möglicherweise im Laden", 12:"Kunde sicher im Laden", 13:"Fehler bei Authentifizierung",
    14: "Bitte Laden betreten", 15: "Kunde nicht mehr im Laden. Abrechnung wird vorbereitet." }

last_shop_status = None
def on_message(client, userdata, message):
    global last_shop_status
    try:
        m = message.payload.decode("utf-8")
        logger.info("Topic: "+message.topic+" Message: "+m)
        msplit = re.split("/", message.topic)

        if message.topic.lower() == "homie/shop_controller/shop_status":
          if last_shop_status != m:
            logger.info("shop_status changed")
            temp_str = m
            if int(m) in shop_status_descr:
              temp_str = m+": "+shop_status_descr[int(m)]
            requests.post("https://ntfy.sh/zeitlos-state", data=temp_str.encode(encoding='utf-8'))
            last_shop_status = m

    except Exception as err:
        traceback.print_tb(err.__traceback__)

client = paho.Client(mqtt_client_name)
client.on_connect = on_connect
client.on_message = on_message
client.on_disconnect = on_disconnect
client.enable_logger(logger)
logger.info("Connecting to broker "+args.mqtt_broker_host)

# start with MQTT connection and set last will
logger.info("mqtt_client_name: {}".format(mqtt_client_name))
client.will_set("homie/"+mqtt_client_name+"/state", 'offline', qos=1, retain=True)
client.connect(args.mqtt_broker_host)
client.loop_start()
logger.info("MQTT loop started.")
client.publish("homie/"+mqtt_client_name+"/state", 'online', qos=1, retain=True)


while True:
    time.sleep(1-math.modf(time.time())[0])  # make the loop run every second

client.disconnect()
client.loop_stop()
logger.info("Program stopped.")

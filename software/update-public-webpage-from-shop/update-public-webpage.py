#!/usr/bin/python3

import paho.mqtt.client as paho
import json
import time
#from datetime import datetime
import logging
import argparse
import traceback
import math
import sys
import re
import os
import mariadb #1st: sudo apt install libmariadb3 libmariadb-dev   2nd: pip install -Iv mariadb==1.0.7 
import signal #to catch interrupts and exit gracefully

logging.basicConfig(level=logging.WARNING,
                    format='%(asctime)-6s %(levelname)-8s  %(message)s')
logger = logging.getLogger("Update Public Webpage")

parser = argparse.ArgumentParser(description='Shop Controller.')
parser.add_argument("-v", "--verbosity",
                    help="increase output verbosity", default=0, action="count")
parser.add_argument("-b", "--mqtt-broker-host",
                    help="MQTT broker hostname. default=localhost", default="localhost")
args = parser.parse_args()
logger.setLevel(logging.WARNING-(args.verbosity * 10 if args.verbosity <= 2 else 20))

mqtt_client_name = "update-public-webpage"

conn = None
cur = None
def db_prepare():
  global conn, cur
  conn = mariadb.connect(
    user="user_shop_control",
    password="wlLvMOR4FStMEzzN",
    host="192.168.10.10",
    database="zeitlos")
  cur = conn.cursor()

def db_close():
  global conn, cur
  cur.close()
  conn.close()

products = {}
products_scales = {}
def get_all_data_from_db():
    global products, products_scales
    db_prepare()
    cur.execute("SELECT ProductID, ProductName, ProductDescription, PriceType, PricePerUnit, kgPerUnit FROM Products ") 
    for ProductID, ProductName, ProductDescription, PriceType, PricePerUnit, kgPerUnit in cur: 
        products[ProductID] = {"ProductID":ProductID, "ProductName":ProductName, "ProductDescription": ProductDescription, 
        "PriceType": PriceType, "PricePerUnit":PricePerUnit, "kgPerUnit":kgPerUnit}
    cur.execute("SELECT ProductID, ShelfName, ScaleHexStr FROM Products_Scales ") 
    for ProductID, ShelfName, ScaleHexStr in cur: 
        products_scales[ShelfName+"/"+ScaleHexStr] = ProductID
    logger.debug("products from db: {}".format(products))
    logger.debug("products_scales from db: {}".format(products_scales))
    db_close()

get_all_data_from_db()

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

shop_status = -1
shop_status_last_change_timestamp = time.time()

def on_message(client, userdata, message):
  global shop_status
  try:
    m = message.payload.decode("utf-8")
    logger.info("Topic: "+message.topic+" Message: "+m)

    if message.topic.lower() == "homie/shop_controller/shop_status":
      if len(m)>0:
        new_shop_status = int(m)
        logger.info(f"shop_status: {shop_status} new shop_status: {new_shop_status}")

        if (new_shop_status==15) and (shop_status!=15): #Wechsel zur 15: Kunder sicher nicht mehr im Laden
          logger.info("Start script upload.sh")
          os.system("/home/pi/zeitlos/software/update-public-webpage-from-shop/upload.sh")
          logger.info("started.")

        shop_status = new_shop_status
        shop_status_last_change_timestamp = time.time()

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


loop_var = True
def signal_handler(sig, frame):
  global loop_var
  logger.info('You pressed Ctrl+C! Preparing for graceful exit.')
  loop_var = False
signal.signal(signal.SIGINT, signal_handler)

while loop_var:
  time.sleep(1-math.modf(time.time())[0])  # make the loop run every second

client.disconnect()
client.loop_stop()
logger.info("Program stopped.")

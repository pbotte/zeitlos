#!/usr/bin/python3

import paho.mqtt.client as paho
import json
import time
from datetime import datetime
import logging
import argparse
import math
import sys
import re
import yaml  # pip3 install pyyaml

logging.basicConfig(level=logging.WARNING,
                    format='%(asctime)-6s %(levelname)-8s  %(message)s')
logger = logging.getLogger("Client Live Display")

parser = argparse.ArgumentParser(
    description='Shop Controller.')
parser.add_argument("-v", "--verbosity",
                    help="increase output verbosity", default=0, action="count")
parser.add_argument("-b", "--mqtt-broker-host",
                    help="MQTT broker hostname. default=localhost", default="localhost")
parser.add_argument("-s", "--door-qr-code-secret",
                    help="Prefix to secure door entry. THIS IS AN SECURITY RISK IF YOU LEAVE THIS UNCHANCED. default=DasGeheimnis2020", default="DasGeheimnis2020")
parser.add_argument("-t", "--watchdog-timeout",
                    help="timeout in seconds for the watchdog. default=1h", default=100*60*60, type=int)
args = parser.parse_args()
logger.setLevel(logging.WARNING-(args.verbosity *
                                 10 if args.verbosity <= 2 else 20))

logger.info("Watchdog timeout (seconds): "+str(args.watchdog_timeout))

mqtt_client_name = "shopController"


def on_connect(client, userdata, flags, rc):
    if rc == 0:
        logger.info("MQTT connected OK. Return code "+str(rc))
        client.subscribe("homie/+/state")
        client.subscribe("homie/+/status")
        client.subscribe("homie/+/+/withdrawal")
        client.subscribe("homie/"+mqtt_client_name+"/requestShopStatus")

        logger.debug("MQTT: Subscribed to all topics")
    else:
        logger.error("Bad connection. Return code="+str(rc))


def on_disconnect(client, userdata, rc):
    if rc != 0:
        logger.warning("Unexpected MQTT disconnection. Will auto-reconnect")


clientsToMonitor = {}
clientsMQTTPrettyNames = {'scale0x57383735393215170b03': 'Waage 1',
                          'unconfiguredPN5322MQTT': 'RFID Reader',
                          'unconfiguredClientLiveDisplay': 'Kundenanzeige',
                          'scale0x59363332393115051808': 'Waage 2',
                          'scale0x59363332393115171b11': 'Waage 3'}
cardID2ClientDetails = {'0x492F7CC1': {'modus': 1, 'name': 'Kunde Mustermann'},
                        '0x2DD5FF9': {'modus': 0, 'name': 'erzeuger Mustermann'}}
scaleWithdrawal = {}
shopStatus = 1   # 0 = waiting for clients, 1 = client in shop


data_scales = [
    {
        "SerialNumber": "0x57383735393215170b03",
        "DisplayRounding": 5,
        "GlobalOffset": 1899.45,
        "Offset": [41308, -239592, -8747, 26511],
        "Slope": [-0.004746168, 0.004798805, -0.004741381, 0.004679427],
        "Shelf": "shop-shelf-01",
        "ProductID": 0
    },
    {
        "SerialNumber": "0x59363332393115171b11",
        "DisplayRounding": 5,
        "GlobalOffset": 1913.963,
        "Offset": [54148.9, 140098.6, -147084.4, 155639.7],
        "Slope": [-0.004463, 0.004501, -0.004461, 0.004465],
        "Shelf": "shop-shelf-02",
        "ProductID": 1
    },
    {
        "SerialNumber": "0x59363332393115051808",
        "DisplayRounding": 1,
        "GlobalOffset": 1828.11,
        "Offset": [-63214.1, 186820.6, 475.1, 8388607.0],
        "Slope": [-0.00120699, 0.00106272, -0.00110287, 0],
        "Shelf": "shop-shelf-02",
        "ProductID": 2
    }
]
getScaleID = {'0x57383735393215170b03': 0,
              '0x59363332393115171b11': 1, '0x59363332393115051808': 2}

data_products = [
    {
        "ProductID": 0,
        "ProductName": "Mehl",
        "ProductDescription": "Aus Ingelheim.",
        "Picture": "/images/mehl.png",
        "ScaleID": 0,
        "Pricing": {"GrammsPerUnit": 1000, "PricePerUnit": 1.49, "Type": 1},
        "UnitsAtBegin": -1,
        "UnitsCurrent": 0
    },
    {
        "ProductID": 1,
        "ProductName": "Apfelmus",
        "ProductDescription": "Eigener Anbau.",
        "Picture": "/images/apfelmus.jpg",
        "ScaleID": 1,
        "Pricing": {"GrammsPerUnit": 800, "PricePerUnit": 2.49, "Type": 1},
        "UnitsAtBegin": -1,
        "UnitsCurrent": 0
    },
    {
        "ProductID": 2,
        "ProductName": "Äpfel",
        "ProductDescription": "Aus dem eigenen Anbau.",
        "Picture": "/images/pears.jpg",
        "ScaleID": 2,
        "Pricing": {"GrammsPerUnit": 1000, "PricePerUnit": 2.99, "Type": 0},
        "UnitsAtBegin": -1,
        "UnitsCurrent": 0
    }
]


def on_message(client, userdata, message):
    global WatchDogCounter
    global shopStatus
    global data_products
    m = message.payload.decode("utf-8")
    j = {}
    try:
        j = json.loads(m)
        logger.info("Topic: "+message.topic+" JSON:"+str(j))
    except:
        j['status'] = m
        #logger.error("error on converting MQTT message to JSON.")

    if ("homie/"+mqtt_client_name+"/requestShopStatus" == message.topic):
        if (m == '1'):
            setShopClientEntered()
        else:
            setShopClientLeft()

    try:
        msplit = re.split("/", message.topic)
        if len(msplit) == 3 and msplit[2].lower() == "state":
            clientsToMonitor[msplit[1]] = m
        if len(msplit) == 4 and msplit[3].lower() == "withdrawal":
            msplitScaleID = re.split("x", msplit[2])
            if msplitScaleID[0] == 'scale0':
                data_products[getScaleID['0x{}'.format(
                    msplitScaleID[1])]]['UnitsCurrent'] = j['mass']
                scaleWithdrawal[msplitScaleID[1]] = j
                logger.debug("scaleID (scaleWithdrawal) {}: {}".format(
                    msplitScaleID[1], j))

    except:
        logger.error("error in processing JSON message.")


client = paho.Client(mqtt_client_name)
client.on_connect = on_connect
client.on_message = on_message
client.on_disconnect = on_disconnect
# info: https://www.eclipse.org/paho/clients/python/docs/#callbacks
client.enable_logger(logger)
logger.info("Connecting to broker "+args.mqtt_broker_host)

# start with MQTT connection and set last will
logger.info("mqtt_client_name: {}".format(mqtt_client_name))
client.will_set("homie/"+mqtt_client_name+"/state",
                'offline', qos=1, retain=True)
client.connect(args.mqtt_broker_host)
client.loop_start()
logger.info("MQTT loop started.")
client.publish("homie/"+mqtt_client_name+"/state",
               'online', qos=1, retain=True)




WatchDogCounter = args.watchdog_timeout
LastCheckForDoorOpen = 0

actBasket = {"data": [], "total": 0}
client.publish("homie/"+mqtt_client_name+"/actualBasket",
               json.dumps(actBasket), qos=1, retain=True)


def setShopClientEntered():
    global shopStatus, data_products
    logger.info("Set Shop Status: Client entered")
    shopStatus = 1  # client enters the shop

    for v in data_products:
        v['UnitsAtBegin'] = v['UnitsCurrent']

    client.publish("homie/"+mqtt_client_name+"/shopStatus",
                    shopStatus, qos=1, retain=True)
    client.publish("homie/eingangschalten", '1',
                    qos=2, retain=False)  # send door open impuls

def setShopClientLeft():
    global shopStatus        
    logger.info("Set Shop Status: Client left")
    shopStatus = 0  # no client in shop
    client.publish("homie/"+mqtt_client_name+"/shopStatus",
                    shopStatus, qos=1, retain=True)

setShopClientLeft

while (WatchDogCounter > 0):

    if shopStatus == 1:  # client in shop
        WatchDogCounter = 10

    # post actual basket
    actBasketProducts = []
    actSumTotal = 0
    for v in data_products:
        if v["UnitsCurrent"] < v["UnitsAtBegin"]:
            tempPrice = (v["UnitsAtBegin"]-v["UnitsCurrent"]) * \
                v['Pricing']['PricePerUnit']
            if v['Pricing']['Type'] == 0:
                tempPrice = tempPrice / v['Pricing']['GrammsPerUnit']
            tempPrice = round(tempPrice, 2)
            if tempPrice > 0.05:
                tempUnit = 'Stk'
                if v['Pricing']['Type'] == 0:
                    tempUnit = 'g'
                actBasketProducts.append({"productName": v['ProductName'], "descr": v['ProductDescription'],
                                          "quantity": v["UnitsAtBegin"]-v["UnitsCurrent"], "unit": tempUnit,
                                          "price": tempPrice})
                actSumTotal += tempPrice
#    actBasket = {"data": actBasketProducts, "total": actSumTotal}
#    client.publish("homie/"+mqtt_client_name+"/actualBasket",
#                   json.dumps(actBasket), qos=1, retain=True)

#        client.publish("homie/"+mqtt_client_name +
#                       "/productsToDisplayOnShelf/{}/products".format(k), json.dumps(v), qos=1, retain=True)

    time.sleep(1-math.modf(time.time())[0])  # make the loop run every second
    WatchDogCounter -= 1

client.disconnect()
client.loop_stop()
logger.info("Program stopped.")

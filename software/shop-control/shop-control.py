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
import yaml  # pip3 install pyyaml
import mariadb #1st: sudo apt install libmariadb3 libmariadb-dev   2nd: pip install -Iv mariadb==1.0.7 

logging.basicConfig(level=logging.WARNING,
                    format='%(asctime)-6s %(levelname)-8s  %(message)s')
logger = logging.getLogger("Shop Controller")

parser = argparse.ArgumentParser(description='Shop Controller.')
parser.add_argument("-v", "--verbosity",
                    help="increase output verbosity", default=0, action="count")
parser.add_argument("-b", "--mqtt-broker-host",
                    help="MQTT broker hostname. default=localhost", default="localhost")
parser.add_argument("-t", "--timeout",
                    help="timeout in seconds. default=1h", default=100*60*60, type=int)
args = parser.parse_args()
logger.setLevel(logging.WARNING-(args.verbosity * 10 if args.verbosity <= 2 else 20))

mqtt_client_name = "shop_controller"

conn = mariadb.connect(
    user="user_shop_control",
    password="wlLvMOR4FStMEzzN",
    host="192.168.10.10",
    database="zeitlos")
cur = conn.cursor() 

products = {}
products_scales = {}
scales_widthdrawal = {}
def get_all_data_from_db():
    global products, products_scales
    cur.execute("SELECT ProductID, ProductName, ProductDescription, PriceType, PricePerUnit, kgPerUnit FROM Products ") 
    for ProductID, ProductName, ProductDescription, PriceType, PricePerUnit, kgPerUnit in cur: 
        products[ProductID] = {"ProductID":ProductID, "ProductName":ProductName, "ProductDescription": ProductDescription, 
        "PriceType": PriceType, "PricePerUnit":PricePerUnit, "kgPerUnit":kgPerUnit}
    cur.execute("SELECT ProductID, ShelfName, ScaleHexStr FROM Products_Scales ") 
    for ProductID, ShelfName, ScaleHexStr in cur: 
        products_scales[ShelfName+"/"+ScaleHexStr] = ProductID
    logger.debug("products from db: {}".format(products))
    logger.debug("products_scales from db: {}".format(products_scales))

get_all_data_from_db()
#Support for retrieval of data from scales. Put scales anmes e.g. shelf01/921a into this list
list_retrieve_scales = []

def on_connect(client, userdata, flags, rc):
    if rc == 0:
        logger.info("MQTT connected OK. Return code "+str(rc))
        client.subscribe("homie/+/+/withdrawal_units")
        client.subscribe("homie/"+mqtt_client_name+"/request_shop_status")
        client.subscribe("homie/shop_qr-scanner/qrcode_detected")
        client.subscribe("homie/"+mqtt_client_name+"/upload_all")
        client.subscribe("homie/"+mqtt_client_name+"/retrieve_all")

        logger.debug("MQTT: Subscribed to all topics")
    else:
        logger.error("Bad connection. Return code="+str(rc))


def on_disconnect(client, userdata, rc):
    if rc != 0:
        logger.warning("Unexpected MQTT disconnection. Will auto-reconnect")

shop_status = None
shop_status_descr = {0: "Geräte Initialisierung", 1: "Bereit, Kein Kunde im Laden", 2: "Kunde authentifiziert", 
    3: "Kunde im Laden", 4: "Einkauf finalisiert", 5: "Einkauf abgerechnet", 6: "Warten auf: Kunde verlässt Laden", 
    7: "Warten auf: Vorbereitung für nächsten Kunden", 8: "Technischer Fehler aufgetreten", 9: "Kunde benötigt Hilfe",
    10: "Laden geschlossen" }
stop_status_last_change_timestamp = 0

def set_shop_status(v):
    global shop_status
    global stop_status_last_change_timestamp
    if shop_status == v:
        return
    shop_status = v
    stop_status_last_change_timestamp = time.time()
    logger.info("Set Shop Status: {}".format(shop_status_descr[shop_status]))

    client.publish("homie/"+mqtt_client_name+"/shop_status", shop_status, qos=1, retain=True)
    client.publish("homie/"+mqtt_client_name+"/stop_status_last_change_timestamp", stop_status_last_change_timestamp, qos=1, retain=True)



actBasket = {"data": {}, "total": 0}


def on_message(client, userdata, message):
    global list_retrieve_scales
    try:
        m = message.payload.decode("utf-8")
        logger.info("Topic: "+message.topic+" Message: "+m)

        msplit = re.split("/", message.topic)
        if len(msplit) == 3 and msplit[2].lower() == "request_shop_status":
            set_shop_status(0)
        # products withdrawal
        if len(msplit) == 4 and msplit[3].lower() == "withdrawal_units":
            #product_id = products_scales[ msplit[1]+"/"+msplit[2] ]
            temp_units = int(m)
            if temp_units<0: temp_units=0
            if temp_units>1000: temp_units=1000 #set some limits, arbitrary
            scales_widthdrawal[msplit[1]+"/"+msplit[2]] = temp_units

            logger.info("scales_widthdrawal: {}".format( scales_widthdrawal ))

        #emulate with: mosquitto_pub -t 'homie/shop_qr-scanner/qrcode_detected' -m '0000116617B8FAF7AD'
        if message.topic.lower() == "homie/shop_qr-scanner/qrcode_detected":
            logger.info("qrcode read: {}".format( m ))
            if shop_status == 1: # "Bereit, Kein Kunde im Laden"
              set_shop_status(2)

        #mosquitto_pub -t 'homie/shop_controller/retrieve_all' -n
        if message.topic.lower() == "homie/"+mqtt_client_name+"/retrieve_all":
          list_retrieve_scales = list(products_scales.keys())
          logger.info("Start retrieve all with: {}".format(list_retrieve_scales))

	#mosquitto_pub -t 'homie/shop_controller/upload_all' -n
        if message.topic.lower() == "homie/"+mqtt_client_name+"/upload_all":
          logger.info("Start upload of settings to all scales.")
          client.publish("homie/shelf01/can-off-all", "0", qos=1, retain=False)
          for k,v in products_scales.items(): #{'shelf01/65c0': 1, 'shelf01/2438': 2, ...   | Products: {1: {'ProductID': 1, 'ProductName': 'Kürbis', 'ProductDescription': 'eigene Ernte', 'PriceType': 0, 'PricePerUnit': 1.9, 'kgPerUnit': 0.8}, 
            if v in products:
              logger.info("Sending data to scale: {}".format(k))
              client.publish("homie/"+k+"/scale_product_description/set", products[v]['ProductName'], qos=1, retain=False)
              client.publish("homie/"+k+"/scale_product_details_line1/set", products[v]['ProductDescription'], qos=1, retain=False)
              client.publish("homie/"+k+"/scale_product_details_line2/set", "", qos=1, retain=False)
              client.publish("homie/"+k+"/scale_product_mass_per_unit/set", products[v]['kgPerUnit'], qos=1, retain=False)
              client.publish("homie/"+k+"/scale_product_price_per_unit/set", products[v]['PricePerUnit'], qos=1, retain=False)
            else:
              logger.warning("Product ID {} not found. Assigned by scale: {}. Update assignment.".format(v, k))
          client.publish("homie/shelf01/can-on-all", "0", qos=1, retain=False)

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


set_shop_status(0)

last_actBasket = {} #to enable the feature: Send only on change
client.publish("homie/"+mqtt_client_name+"/actualBasket", json.dumps(actBasket), qos=1, retain=True)
client.publish("homie/"+mqtt_client_name+"/shop_overview/products", json.dumps(products), qos=1, retain=True)
client.publish("homie/"+mqtt_client_name+"/shop_overview/products_scales", json.dumps(products_scales), qos=1, retain=True)

#timeout für FSM
# muss noch umgesetzt werden
timeout_goto_shop_status = 8 # Wenn der Timeout auftritt, zu welchem Status gewechselt werden soll
timeout_duration_sec = 60 # Wenn die Zeit abgelaufen ist, dann dan wird shop_status = timeout_goto_shop_status. Bei <0 passiert nichts

while True:

    actBasketProducts = {}
    actSumTotal = 0
    actProductsCount = 0

    for k, v in scales_widthdrawal.items():
        if k in products_scales: # should always be true, unless error in db (assignment scales <-> products) 
            temp_product_id = products_scales[k]
            temp_product = products[temp_product_id]
            if products_scales[k] in actBasketProducts: #in case product is sold on several scales and already in basket
                actBasketProducts[temp_product_id]['withdrawal_units'] += v
                actBasketProducts[temp_product_id]['price'] = actBasketProducts[temp_product_id]['withdrawal_units'] * temp_product['PricePerUnit']
            else:
                temp_product['withdrawal_units'] = v
                temp_product['price'] = v* temp_product['PricePerUnit']
                actBasketProducts[temp_product_id] = temp_product
            actProductsCount += v
            actSumTotal += actBasketProducts[temp_product_id]['price']

            if actBasketProducts[temp_product_id]['withdrawal_units'] == 0:
                actBasketProducts.pop(temp_product_id, None) #Remove from list

    actBasket = {"data": actBasketProducts, "total": actSumTotal, "products_count": actProductsCount}
    if last_actBasket != actBasket: #change to basket? --> publish!
        client.publish("homie/"+mqtt_client_name+"/actualBasket", json.dumps(actBasket), qos=1, retain=True)
        last_actBasket = actBasket

    # Support for scale data retrieval
    if list_retrieve_scales:
      logger.debug("list_retrieve_scales: {}".format(list_retrieve_scales))
      # make sure to publish this not to fast multiple times in a row to allow the scales to answer
      client.publish("homie/"+list_retrieve_scales.pop()+"/retrieve", "0", qos=1, retain=False)


    ############################################################################
    # FSM
    ############################################################################
    next_shop_status = shop_status
    if shop_status == 0: #"Geräte Initialisierung"
        next_shop_status = 7
    elif shop_status == 1: #Bereit, kein Kunde im Laden
        pass # Wechsel zu 2 passiert in MQTT-onMessage
    elif shop_status == 2: #"Kunde authentifiziert"
        client.publish("homie/eingangschalten", '1', qos=2, retain=False)  # send door open impuls
        # Fehlend: Warten bis Türe geöffnet wird
        next_shop_status = 3
    elif shop_status == 3: #Kunde im Laden
        pass
    elif shop_status == 4: #"Einkauf finalisiert"
        pass
    elif shop_status == 5: #"Einkauf abgerechnet"
        pass
    elif shop_status == 6: #"Warten auf: Kunde verlässt Laden"
        pass
    elif shop_status == 7: #"Warten auf: Vorbereitung für nächsten Kunden"
        client.publish("homie/"+mqtt_client_name+"/prepare_for_next_customer", "1", qos=1, retain=False)
        if actProductsCount == 0: #no products withdrawn, all scales reset
          next_shop_status = 1
        else:
          logger.info("Der Laden kann nicht nicht freigegeben werden, da noch {} Produkt(e) nicht zurückgesetzt wurden.".format(actProductsCount))
    elif shop_status == 8: #"Technischer Fehler aufgetreten"
        pass
    elif shop_status == 9: #"Kunde benötigt Hilfe"
        pass
    elif shop_status == 10: #"Laden geschlossen"
        pass
    else: 
        logger.error("Unbekannter shop_status Wert.")

    set_shop_status(next_shop_status)


    time.sleep(1-math.modf(time.time())[0])  # make the loop run every second

client.disconnect()
client.loop_stop()
logger.info("Program stopped.")

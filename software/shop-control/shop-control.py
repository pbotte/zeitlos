#!/usr/bin/python3

import paho.mqtt.client as paho
import json
import time
from datetime import datetime
import logging
import argparse
import traceback
import hashlib
import math
import sys
import re
import yaml  # pip3 install pyyaml
import mariadb #1st: sudo apt install libmariadb3 libmariadb-dev   2nd: pip install -Iv mariadb==1.0.7 
import parse #pip install parse
import signal #to catch interrupts and exit gracefully

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
parser.add_argument("qr_secret_str", help="used to generate a true secret for QR codes. Needs to be the same for the webpage.", type=str)
args = parser.parse_args()
logger.setLevel(logging.WARNING-(args.verbosity * 10 if args.verbosity <= 2 else 20))

mqtt_client_name = "shop_controller"

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
scales_widthdrawal = {}
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
#Support for retrieval of data from scales. Put scales anmes e.g. shelf01/921a into this list
list_retrieve_scales = []

def on_connect(client, userdata, flags, rc):
    if rc == 0:
        logger.info("MQTT connected OK. Return code "+str(rc))
        client.subscribe("homie/+/+/withdrawal_units")
        client.subscribe("homie/"+mqtt_client_name+"/request_shop_status")
        client.subscribe("homie/"+mqtt_client_name+"/close_shop");
        client.subscribe("homie/shop_qr-scanner/qrcode_detected")
        client.subscribe("homie/"+mqtt_client_name+"/upload_all")
        client.subscribe("homie/"+mqtt_client_name+"/retrieve_all")
        client.subscribe("homie/shop-track/+/distance")
        client.subscribe("homie/door/#")

        logger.debug("MQTT: Subscribed to all topics")
    else:
        logger.error("Bad connection. Return code="+str(rc))


def on_disconnect(client, userdata, rc):
    if rc != 0:
        logger.warning("Unexpected MQTT disconnection. Will auto-reconnect")

shop_status = 0 # Needs to be different from 10, to make set_shop_status(10) later make work
shop_status_descr = {0: "Geräte Initialisierung", 1: "Bereit, Kein Kunde im Laden", 2: "Kunde authentifiziert/Waagen tara",
    3: "Kunde betritt/verlässt gerade den Laden", 4: "Möglicherweise: Einkauf finalisiert & Kunde nicht mehr im Laden",
    5: "Einkauf beendet und abgerechnet", 6: "ungenutzt",
    7: "Warten auf: Vorbereitung für nächsten Kunden", 8: "Technischer Fehler aufgetreten", 9: "Kunde benötigt Hilfe",
    10: "Laden geschlossen", 11: "Kunde möglicherweise im Laden", 12:"Kunde sicher im Laden", 13:"Fehler bei Authentifizierung",
    14: "Bitte Laden betreten", 15: "Kunde nicht mehr im Laden. Abrechnung wird vorbereitet." }
shop_status_timeout = {
    0: {'time':10,'next':8}, #Geräte Initialisierung
    1: None, #Bereit, Keine Kunde im Laden
    2: {'time':10,'next':8}, #Kunde authentifiziert
    3: {'time':60*10,'next':9}, #Kunde betritt/verlässt gerade den Laden
    4: {'time':5,'next':15}, #Möglicherweise: Einkauf finalisiert & Kunde nicht mehr im Laden
    5: {'time':60,'next':8}, # Einkauf beendet und abgerechnet
    6: None, # Zustand aktuell nicht genutzt
    7: {'time':30,'next':8}, #Warten auf: Vorbereitung für nächsten Kunden
    8: None, # Technischer Fehler aufgetreten
    9: None, # Kunde benötigt Hilfe
    10: None, # Laden geschlossen
    11: {'time': 5,'next':4}, # Kunde möglicherweise im Laden? Falls 5 Sek. kein Kunde im Laden -> Wechsel zu 4
    12: {'time':60*10,'next':9}, # Kunde sicher im Laden
    13: {'time': 3,'next':1}, # Fehler bei Authentifizierung
    14: {'time': 5,'next':7 }, #Bitte Laden betreten
    15: {'time': 60,'next': 8} #Sicher: Kunde nicht mehr im Laden. Abrechnung wird vorbereitet
    }
shop_status_last_change_timestamp = time.time()

def set_shop_status(v):
    global shop_status
    global shop_status_last_change_timestamp
    if shop_status == v:
        return
    shop_status = v
    shop_status_last_change_timestamp = time.time()
    logger.info("Set Shop Status: {}".format(shop_status_descr[shop_status]))

    client.publish("homie/"+mqtt_client_name+"/shop_status", shop_status, qos=1, retain=True)
    client.publish("homie/"+mqtt_client_name+"/shop_status_last_change_timestamp", shop_status_last_change_timestamp, qos=1, retain=True)



actualclientID = -1
actBasket = {"data": {}, "total": 0}
status_no_person_in_shop = None # if all readings from homie/shop-track/+/distance are > 2000, then False, else True
status_door_closed = None
last_reading_distances = {}

def on_message(client, userdata, message):
    global list_retrieve_scales
    global status_no_person_in_shop, last_reading_distances
    global status_door_closed
    global actualclientID
    try:
        m = message.payload.decode("utf-8")
        logger.info("Topic: "+message.topic+" Message: "+m)

        msplit = re.split("/", message.topic)
        if len(msplit) == 3 and msplit[2].lower() == "request_shop_status":
            if len(m) > 0:
               set_shop_status(int(m))
            else:
               set_shop_status(0)
        if len(msplit) == 3 and msplit[2].lower() == "close_shop":
            set_shop_status(10)

        # distance reading to know person presence
        if len(msplit) == 4 and msplit[1].lower() == "shop-track"  and msplit[3].lower() == "distance":
            last_reading_distances[msplit[2].lower()] = float(m)
            status_no_person_in_shop = all( value > 2000 for value in last_reading_distances.values()  ) #all returns true if all elements are true

        # products withdrawal
        if len(msplit) == 4 and msplit[3].lower() == "withdrawal_units":
            #product_id = products_scales[ msplit[1]+"/"+msplit[2] ]
            temp_units = int(m)
            if temp_units<-1000: temp_units=-1000 # set soem limits, arbitraryly choosen
            if temp_units>1000: temp_units=1000 #set some limits, arbitrary
            scales_widthdrawal[msplit[1]+"/"+msplit[2]] = temp_units

            logger.info("scales_widthdrawal: {}".format( scales_widthdrawal ))

        # QR Code scanned.
        #emulate with: mosquitto_pub -t 'homie/shop_qr-scanner/qrcode_detected' -m '1666703949 43 B8FAF7'
        # 3 numbers, separated with spaces: time.time(), User ID, md5-hash
        if message.topic.lower() == "homie/shop_qr-scanner/qrcode_detected":
            logger.info("qrcode read: {}".format( m ))
            if shop_status == 1: # "Bereit, Kein Kunde im Laden"
              r=parse.parse("{time:d} {id:d} {hash:w}", m) #definition see: https://pypi.org/project/parse/
              if r: #time, user id and hash in qr code?
                expected_sum = hashlib.md5("{}{}{}".format(args.qr_secret_str, r['time'], r['id']).encode('utf-8')).hexdigest()
                logger.info("HASH expected_sum computated: {}".format(expected_sum[:6]))
                if r['hash'] == expected_sum[:6]:
                  logger.info("hash in qr code read equals expected sum: {}".format(expected_sum[:6]))
                  if abs(time.time() - r['time']) < 10*60: #qrcode needs to be generated within a time windows of 10*60 seconds
                    actualclientID = r['id']
                    client.publish("homie/"+mqtt_client_name+"/actualclient/id", r['id'], qos=1, retain=True)
                    set_shop_status(2) # Authentifizierung war in Ordnung
                  else:
                    logger.warning("Time window of qr code not met.") # qr code too old or time not set correctly
                    set_shop_status(13) #Fehler bei Authentifizierung
                else:
                  logger.warning("hash in qr code not as expected.")
                  set_shop_status(13) #Fehler bei Authentifizierung
              else:
                set_shop_status(13) #Fehler bei Authentifizierung

        #mosquitto_pub -t 'homie/door/Pin0' -m 1
        # Door open/close message
        if message.topic.lower() == "homie/door/pin0":
          if m == "0": #Tür ist offen
            status_door_closed = False
          else:
            status_door_closed = True
          if (shop_status == 14) and (status_door_closed == False): # Kunde authentifiziert, und Tür geht auf
            client.publish("homie/fsr-control/innen/tuerschliesser/set", '0', qos=2, retain=False)  # send door open impuls = OFF
            set_shop_status(3) # Kunde betritt / verlässt gerade den Laden
          elif (shop_status == 3) and (status_door_closed == True): # Tür ist wieder zu
            set_shop_status(11) # Kunde möglicherweise im Laden
          elif (shop_status == 11) and (status_door_closed == False): # Tür wieder offen
            set_shop_status(3) # Kunde betritt / verlässt gerade den Laden
          elif (shop_status == 4) and (status_door_closed == False): #Möglicherweise Einkauf final / Kunde nicht mehr im Laden
            set_shop_status(3) # Kunde betritt / verlässt gerade den Laden
          elif (shop_status == 12) and (status_door_closed == False): #Kunde sicher im laden
            set_shop_status(3) # Kunde betritt / verlässt gerade den Laden

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
              time.sleep(0.05)
              client.publish("homie/"+k+"/scale_product_details_line1/set", products[v]['ProductDescription'], qos=1, retain=False)
              time.sleep(0.05)
              client.publish("homie/"+k+"/scale_product_details_line2/set", "Stueckpreis: {:.2f}EUR".format(products[v]['PricePerUnit']), qos=1, retain=False)
              time.sleep(0.05)
              client.publish("homie/"+k+"/scale_product_mass_per_unit/set", products[v]['kgPerUnit'], qos=1, retain=False)
              time.sleep(0.05)
              client.publish("homie/"+k+"/scale_product_price_per_unit/set", products[v]['PricePerUnit'], qos=1, retain=False)
              time.sleep(0.05)
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


set_shop_status(10) # Laden geschlossen. Sonst kann man den laden eröffnen durch Stromunterbrechung.

last_actBasket = {} #to enable the feature: Send only on change
client.publish("homie/"+mqtt_client_name+"/actualBasket", json.dumps(actBasket), qos=1, retain=True)
client.publish("homie/"+mqtt_client_name+"/shop_overview/products", json.dumps(products), qos=1, retain=True)
client.publish("homie/"+mqtt_client_name+"/shop_overview/products_scales", json.dumps(products_scales), qos=1, retain=True)

loop_var = True
def signal_handler(sig, frame):
  global loop_var
  logger.info('You pressed Ctrl+C! Preparing for graceful exit.')
  loop_var = False
signal.signal(signal.SIGINT, signal_handler)

while loop_var:
    actBasketProducts = {}
    actSumTotal = 0
    actProductsCount = 0

    for k, v in scales_widthdrawal.items():
        if k in products_scales: # should always be true, unless error in db (assignment scales <-> products) 
            temp_product_id = products_scales[k]
            temp_product = products[temp_product_id]
            temp_v = 0 if v<0 else v #no negative numbers of items in basket! Negative numbers only for actProductsCount
            if products_scales[k] in actBasketProducts: #in case product is sold on several scales and already in basket
                actBasketProducts[temp_product_id]['withdrawal_units'] += temp_v
                actBasketProducts[temp_product_id]['price'] = actBasketProducts[temp_product_id]['withdrawal_units'] * temp_product['PricePerUnit']
            else:
                temp_product['withdrawal_units'] = temp_v
                temp_product['price'] = temp_v * temp_product['PricePerUnit']
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
        pass # Wechsel zu 2 (OK) oder 13 (Fehler) passiert in MQTT-onMessage
    elif shop_status == 2: #"Kunde authentifiziert / Waagen tara wird ausgeführt
        client.publish("homie/"+mqtt_client_name+"/prepare_for_next_customer", "1", qos=1, retain=False) # Waagen tara ausführen
        if actProductsCount == 0: #no products withdrawn, all scales reset
          next_shop_status = 14 # Bitte Laden betreten
          client.publish("homie/fsr-control/innen/tuerschliesser/set", '1', qos=2, retain=False)  # send door open impuls
        else:
          logger.info("Der Laden kann nicht nicht freigegeben werden, da noch {} Produkt(e) nicht zurückgesetzt wurden.".format(actProductsCount))
    elif shop_status == 3: #Kunde betritt/verlässt gerade den Laden
        pass # Weiter gehts zu 11 in MQTT onMessage
    elif shop_status == 4: # Möglicherweise: Einkauf finalisiert / Kunde nicht mehr im Laden"
        #Tür==offen: Wechsel zu 3 über MQTT-Message
        if status_no_person_in_shop == False:
          next_shop_status = 12
    elif shop_status == 5: #"Einkauf beendet und abgerechnet"
        next_shop_status = 7
    elif shop_status == 6: # ungenutzter Zustand
        next_shop_status = 7
    elif shop_status == 7: #"Warten auf: Vorbereitung für nächsten Kunden"
        client.publish("homie/"+mqtt_client_name+"/actualclient/id", -1, qos=1, retain=True)
        client.publish("homie/fsr-control/innen/licht/set", '0', qos=1, retain=False)
        actualclientID = -1
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
    elif shop_status == 11: # Kunde möglichweise im Laden
        if (time.time()-shop_status_last_change_timestamp > 2.5): # Zur Vermeidung von Melde-Verzögerungen der Distanzsensoren erst nach einiger Zeit auswerten
          if status_no_person_in_shop == False: # Kunde ist im Laden
            next_shop_status = 12 # Kunde sicher im Laden
    elif shop_status == 12: # Kunde sicher im Laden
        pass # Tür==offen: Wechsel zu 3 über MQTT-Message
    elif shop_status == 13: # Fehler bei Authentifizierung
        pass # geht über Timeout weiter zu 1
    elif shop_status == 14: # Bitte Laden betreten
        client.publish("homie/fsr-control/innen/licht/set", '1', qos=1, retain=False)
        client.publish("homie/display-power-control-02/power/set", '1', qos=1, retain=False)
        # Tür offen in MQTT-Message: Wechsel zu next_shop_status = 3
    elif shop_status == 15: # Abrechnung wird vorbereitet
        # Abrechnung durchführen
        try:
          sql_str = "INSERT INTO `Invoices` (`ClientID`, `Products`) VALUES (?, ?); "
          actBasket_str = json.dumps(actBasket)
          logger.info("Executed the following SQL Str: {} with ({}, {})".format(sql_str, actualclientID, actBasket_str))
          db_prepare()
          try:
            cur.execute(sql_str, (actualclientID, actBasket_str))
            conn.commit()
            logger.info("Last Inserted ID: {}".format(cur.lastrowid))
          except mariadb.Error as e:
            logger.warning(f"Error while SQL INSERT: {e}")
          db_close()

          next_shop_status = 5 # Weiter zu: Einkauf beendet und abgerechnet
        except:
          next_shop_status = 8
          logger.warning("Errir while saving the basket in db")
    else:
        logger.error("Unbekannter shop_status Wert.")

    ########################
    # check for time out of actual state
    ########################
    if shop_status_timeout[shop_status] is not None:
      if (time.time()-shop_status_last_change_timestamp > shop_status_timeout[shop_status]['time']): #die Zeit für den aktuellen Zustand ist abgelaufen
        next_shop_status = shop_status_timeout[shop_status]['next']
        logger.info("Timeout des shop_status: {}. Daher nächster Status: {}".format(shop_status, next_shop_status))

    #### Setzen des nächsten Shop-Status
    set_shop_status(next_shop_status)


    time.sleep(1-math.modf(time.time())[0])  # make the loop run every second


set_shop_status(10) # Laden geschlossen

client.disconnect()
client.loop_stop()
logger.info("Program stopped.")

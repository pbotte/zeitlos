#!/usr/bin/python3

# ToDO: On entering: Save current scales readings to register
# ToDo: On new mass reading: update basket. Note: multiple scales can work together, weight the same product

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
import queue
import copy

import combined_scales_support #unterstützung von doppeltbreiten Waagen

logging.basicConfig(level=logging.WARNING, format='%(asctime)-6s %(levelname)-8s  %(message)s')
logger = logging.getLogger("Shop Controller")

parser = argparse.ArgumentParser(description='Shop Controller.')
parser.add_argument("-v", "--verbosity", help="increase output verbosity", default=0, action="count")
parser.add_argument("-b", "--mqtt-broker-host", help="MQTT broker hostname. default=localhost", default="localhost")
parser.add_argument("-t", "--timeout", help="timeout in seconds. default=1h", default=100*60*60, type=int)
args = parser.parse_args()
logger.setLevel(logging.WARNING-(args.verbosity * 10 if args.verbosity <= 2 else 20))

logger.info(f"{combined_scales_support.combined_scales_data_array=}")

mqtt_client_name = "shop_controller"
max_money_preauth = 100.00 #in Euros

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
scales_products = {}
products_scales = {} #inverse of scales_products for easier lookup
scales_mass_reference = {} #masses before client started shopping
scales_mass_actual = {}
def get_all_data_from_db():
    global products, scales_products, products_scales
    products = {}
    scales_products = {}
    products_scales = {}
    db_prepare()
    cur.execute("SELECT ProductID, ProductName, ProductDescription, PriceType, PricePerUnit, kgPerUnit, VAT, Supplier FROM Products ") 
    for ProductID, ProductName, ProductDescription, PriceType, PricePerUnit, kgPerUnit, VAT, Supplier in cur: 
        products[ProductID] = {"ProductID":ProductID, "ProductName":ProductName, "ProductDescription": ProductDescription, 
        "PriceType": PriceType, "PricePerUnit":PricePerUnit, "kgPerUnit":kgPerUnit, "VAT": VAT, "Supplier": Supplier}
    cur.execute("SELECT ProductID, ScaleID FROM Products_Scales GROUP BY ScaleID"); #Group By verhindert, falls in der Datenbank zwei Produkte für eine Waage eingetragen sind.
    for ProductID, ScaleID in cur:
        scales_products[ScaleID.lower()] = ProductID
        if ProductID in products_scales:
          products_scales[ProductID].append(ScaleID.lower())
        else:
          products_scales[ProductID] = [ScaleID.lower()]
    
    logger.debug(f"products from db: {products=}")
    logger.debug(f"scales_products from db: {scales_products=}")
    db_close()

#db operation: Einer Waage eine Produkt zuordnen. Zuvor_db_prepare() und anschließend db_close() aufrufen!
# Wenn die Routine mit act_product_id=="" aufgerufen wird, wird die Zuordnung lediglich gelöscht und kein
# neues Produkt zugeordnet
def set_product_id_to_scale(act_scale_id, act_product_id=""):
  for v in combined_scales_support.search_scale_and_convert_to_array(act_scale_id):
    #Bisherigen Eintrag löschen
    try:
      sql_str = "DELETE FROM `Products_Scales` WHERE `ScaleID` LIKE ?; "
      logger.info(f"Execute the following SQL Str: {sql_str} with ({v})")
      cur.execute(sql_str, (v, )) #the last comma here is super important, if only one elem provided
      conn.commit()
    except mariadb.Error as e:
      logger.warning(f"Error while SQL DELETE: {e}")

    #neue Produktzuordnung eintragen, nur wenn Zahl übergeben ist
    if act_product_id:
      try:
        sql_str = "INSERT INTO`Products_Scales`(`ProductID`, `ScaleID`) VALUES(?, ? ); "
        logger.info(f"Execute the following SQL Str: {sql_str} with ({int(act_product_id)}, {v})")
        cur.execute(sql_str, (int(act_product_id), v, )) #the last comma here is super important, if only one elem provided
        conn.commit()
        last_product_scale_id_inserted = cur.lastrowid
        logger.info(f"Last Inserted ID into Products_Scales: {last_product_scale_id_inserted}")
      except mariadb.Error as e:
        logger.warning(f"Error while SQL INSERT: {e}")
    else:
        logger.info(f"Waagenzuordnung wurde nur gelöscht und kein neuer Eintrag getätigt.")


get_all_data_from_db()

#global variable to store last values
tofcamshoptof_value = 0
pixels_above_reference = 0
def on_connect(client, userdata, flags, rc):
    if rc == 0:
        logger.info("MQTT connected OK. Return code "+str(rc))
        client.subscribe("homie/+/scales/+/mass") #eg homie/scale-shop-shelf02-0-1.2-1.0/scales/493037101F4B/mass
        client.subscribe("homie/"+mqtt_client_name+"/set_shop_status")
        client.subscribe("homie/"+mqtt_client_name+"/update_data_from_db")
        client.subscribe("homie/shop-track-collector/pixels-above-reference")
        client.subscribe("homie/tof-cam-shop-tof/value")
        client.subscribe("homie/public_webpage_viewer/message_input")
        client.subscribe("homie/public_webpage_supplier/+/cmd/#")
        client.subscribe("homie/door/#")
        client.subscribe("homie/cardreader/#")
        client.subscribe("homie/+/state") #eg homie/scale-shop-shelf01-0-1.5-1.0/state 1
        client.subscribe("homie/+/scales/+/touched") #zum Waagen auswählen beim Bestückenu und Kalibrieren
        client.subscribe("homie/"+mqtt_client_name+"/last_touched/reset") #um wieder neue Waagen auswählen zu können
        client.subscribe("homie/"+mqtt_client_name+"/last_touched/set_product_id") #Neues Produkt auf Waage setzen

        logger.debug("MQTT: Subscribed to all topics")

        client.publish("homie/"+mqtt_client_name+"/state", '1', qos=1, retain=True)

    else:
        logger.error("Bad connection. Return code="+str(rc))

def on_disconnect(client, userdata, rc):
    if rc != 0:
        logger.warning("Unexpected MQTT disconnection. Will auto-reconnect")

shop_status = 0 # Needs to be different from 10, to make set_shop_status(10) later make work
shop_status_descr = {
    0: "Geräte Initialisierung", 
    1: "Bereit, Kein Kunde im Laden. Kartenterminal aktiv ", 
    2: "Kunde authentifiziert/Waagen tara wird ausgeführt",
    3: "Kunde betritt/verlässt gerade den Laden", 
    4: "Möglicherweise: Einkauf finalisiert & Kunde nicht mehr im Laden",
    5: "Einkauf abgerechnet, Kassenbon-Anzeige", 
    6: "Einräumen durch Betreiber",
    7: "Warten auf: Vorbereitung für nächsten Kunden. Kartenterminal bereit?", 
    8: "Technischer Fehler aufgetreten", 
    9: "Kunde benötigt Hilfe",
    10: "Laden geschlossen", 
    11: "Kunde möglicherweise im Laden", 
    12: "Kunde sicher im Laden", 
    13: "Fehler bei Kartenterminal",
    14: "Bitte Laden betreten", 
    15: "Sicher: Kunde nicht mehr im Laden. Kartenterminal: buchen!",
    16: "Timeout Kartenterminal",
    17: "Warten auf: Kartenterminal Buchung erfolgreich",
    18: "Einräumen durch Betreiber, Waage ausgewählt",
    19: "Wartung der Technik",
    20: "Gesamtsumme zu hoch", # wenn der Kunde mehr als vorauthorisiert wurde, entnommen hat
    }
shop_status_timeout = {
    0: {'time':10,'next':8}, #Geräte Initialisierung
    1: {'time':60*5,'next':8}, #Bereit, Keine Kunde im Laden. Kartenterminal aktiv. Timeout da ein Timeout vom Terminal erwartet wird
    2: {'time':10,'next':8}, #Kunde authentifiziert/Waagen tara wird ausgeführt
    3: {'time':60*10,'next':9}, #Kunde betritt/verlässt gerade den Laden
    4: {'time':2,'next':15}, # Möglicherweise: Einkauf finalisiert & Kunde nicht mehr im Laden
                              # Falls die Sensoren nicht alles abdecken oder durch IR-Licht gestört werden, 
                              # dann hier einen größeren Zeit-Wert sicherheitshalber angeben.
    5: {'time':60,'next':7}, # Einkauf abgerechnet, Kassenbon-Anzeige
    6: None, # Einräumen durch Betreiber
    7: {'time':30,'next':8}, #Warten auf: Vorbereitung für nächsten Kunden
    8: None, # Technischer Fehler aufgetreten
    9: None, # Kunde benötigt Hilfe
    10: None, # Laden geschlossen
    11: {'time': 4,'next':4}, # Kunde möglicherweise im Laden? Falls 4 Sek. kein Kunde im Laden -> Wechsel zu 4
    12: {'time':60,'next':11}, # Kunde sicher im Laden. Zustand wird verlängert, sofern Kunde im Laden detektiert wird. Timeout, falls doch kein Kunde im Laden.
    13: {'time': 3,'next':7}, # Fehler bei Kartenterminal
    14: {'time': 15,'next':15}, # Bitte Laden betreten
    15: {'time': 60,'next': 8}, # Sicher: Kunde nicht mehr im Laden. Kartenterminal buchen!
    16: {'time': 120,'next': 8}, # Timeout Kartenterminal
    17: {'time': 30,'next': 8}, # Warten auf: Kartenterminal Buchung erfolgreich
    18: None, # Einräumen durch Betreiber, Waage ausgewählt
    19: None, # Wartung der Technik
    20: {'time': 60*5,'next': 9}, #Kunde hat mehr entnommen als vorauthorisiert
    }
shop_status_last_change_timestamp = time.time()

def confirm_shop_status():
    global shop_status_last_change_timestamp
    shop_status_last_change_timestamp = time.time()
    # Do not update this variable via MQTT to save ressources as it is not needed elsewhere
    # client.publish("homie/"+mqtt_client_name+"/shop_status_last_change_timestamp", shop_status_last_change_timestamp, qos=1, retain=True)
    logger.debug(f"Shop Status confirmed")

def set_shop_status(v):
    global shop_status
    global shop_status_last_change_timestamp
    global status_last_touched_shelf_str, status_last_touched_scale_str
    global shop_status_last_cycle

    shop_status_last_cycle = shop_status
    if shop_status == v:
        return

    if v == 6 and shop_status!=18:
      #nur 1x beim Wechsel in diesen Modus abspielen
      client.publish("homie/tts-shop-shelf02/say", "Laden im Wartungsmodus.", qos=1, retain=False)
    if v == 20:
      client.publish("homie/tts-shop-shelf02/say", f"Sehr geehrte Kundin, sehr geehrter Kunde. Sie haben für mehr als {max_money_preauth:.2f}€ Waren entnommen. Es freut uns sehr, dass unser Angebot Ihnen zusagt.", qos=1, retain=False)
      client.publish("homie/tts-shop-shelf02/say", f"Leider müssen wir Sie darum bitten uns, Produkte wieder zurück zulegen, da wir Ihre Karte nur bis zu {max_money_preauth:.2f}€ belasten können. ", qos=1, retain=False)
      client.publish("homie/tts-shop-shelf02/say", "Erst dann kann der Einkauf beendet werden. Betreten Sie gerne anschließend gleich wieder unseren Laden!", qos=1, retain=False)
      client.publish("homie/tts-shop-shelf02/say", "Sollten Sie noch Fragen haben, so klingeln Sie bitte oder schreiben uns.", qos=1, retain=False)
    if v == 0:
      client.publish("homie/tts-shop-shelf02/say", "Laden wird vorbereitet.", qos=1, retain=False)
    if v == 7:
      client.publish("homie/tts-shop-shelf02/say", "Laden ist bereit und wartet auf Kunden.", qos=1, retain=False)
    if v == 8:
      client.publish("homie/tts-shop-shelf02/say", "Ein technischer Fehler ist aufgetreten. Bitte kontaktieren Sie den Betreiber.", qos=1, retain=False)
    if v == 10:
      client.publish("homie/tts-shop-shelf02/say", "Laden geschlossen.", qos=1, retain=False)

    if v == 6:
      #immer abspielen, wenn in diesen Modus
      client.publish("homie/tts-shop-shelf02/say", f"Berühre eine Waage.", qos=1, retain=False)

    shop_status = v
    shop_status_last_change_timestamp = time.time()
    logger.info(f"Set Shop Status to {shop_status}: {shop_status_descr[shop_status]}")

    client.publish("homie/"+mqtt_client_name+"/shop_status", shop_status, qos=1, retain=True)
    client.publish("homie/"+mqtt_client_name+"/shop_status_last_change_timestamp", shop_status_last_change_timestamp, qos=1, retain=True)

    #Wenn Status gewechelt wird in einen shop_status != 18, dann sollen die Informationen über die ausgewählte Waage gelöscht werden und LED wieder ausgeschaltet
    if shop_status != 18 and status_last_touched_shelf_str and status_last_touched_scale_str: 
      for v in combined_scales_support.search_scale_and_convert_to_array(status_last_touched_scale_str):
        client.publish(f"homie/{status_last_touched_shelf_str}/cmd/scales/{v.upper()}/led", "0", qos=1, retain=False)
      status_last_touched_shelf_str = ""
      status_last_touched_scale_str = ""
      client.publish("homie/"+mqtt_client_name+"/last_touched/shelf_str", status_last_touched_shelf_str, qos=1, retain=True) #zurücksetzen
      client.publish("homie/"+mqtt_client_name+"/last_touched/scale_str", status_last_touched_scale_str, qos=1, retain=True) #zurücksetzen
      client.publish("homie/"+mqtt_client_name+"/last_touched/product_id", status_last_touched_scale_str, qos=1, retain=True) #zurücksetzen


cardreader_busy = False # set by MQTT messages from cardreader. When true, do not submit any task to cardreader and simply wait
cardreader_last_textblock = "" # MQTT messages from cardread typically in receipe style from homie/cardreader/text_block

actBasketCorrections = {} #only filled with data, when basket was corrected remotely via '.../cmd/basket/set_product_count'. Fille with {"ProductID": "CorrectValue", ...}
actBasket = {"data": {}, "total": 0, "products_count": 0, "corrections": actBasketCorrections} #data-field does already include the corrections from actBasketCorrections
status_no_person_in_shop = None # True if homie/shop-track-collector/pixels-above-reference == 0 and homie/tof-cam-shop-tof/value < Some_Threshold, else False
status_door_closed = None

# zum Abspeichern von Informationen aus: homie/scale-shop-shelf06-0-1.2.5.5-1.0/scales/4930370A3419/touched
status_last_touched_shelf_str = "" #scale-shop-shelf06-0-1.2.5.5-1.0
status_last_touched_scale_str = "" #4930370A3419

mqtt_queue=queue.Queue()
def on_message(client, userdata, message):
  global mqtt_queue
  try:
    mqtt_queue.put(message)
    m = message.payload.decode("utf-8")
    logger.debug("MQTT message received. Topic: "+message.topic+" Payload: "+m)
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
client.will_set("homie/"+mqtt_client_name+"/state", '0', qos=1, retain=True)
client.connect(args.mqtt_broker_host)
client.loop_start()
logger.info("MQTT loop started.")


set_shop_status(10) # Laden geschlossen. Sonst kann man den laden eröffnen durch Stromunterbrechung.

last_actBasket = {} #to enable the feature: Send only on change
def send_basket_products_scales_to_mqtt():
  client.publish("homie/"+mqtt_client_name+"/actualBasket", json.dumps(actBasket), qos=1, retain=True)

  client.publish("homie/"+mqtt_client_name+"/shop_overview/products", json.dumps(products), qos=1, retain=True)
  for k, v in products.items():
    for k2, v2 in v.items():
      client.publish(f"homie/{mqtt_client_name}/shop_overview/products/{k}/{k2.lower()}", v2, qos=0, retain=True)
    s = ''.join(str(v.values()))
    s = int(hashlib.sha256(s.encode('utf-8')).hexdigest(), 16) % 10**8 #make a 8 digit hash value
    client.publish(f"homie/{mqtt_client_name}/shop_overview/products/{k}/hash", s, qos=0, retain=True) #to support  refresh only on change
    if k in products_scales:
      client.publish(f"homie/{mqtt_client_name}/shop_overview/products/{k}/scales", json.dumps(products_scales[k]), qos=0, retain=True)
    else:
      client.publish(f"homie/{mqtt_client_name}/shop_overview/products/{k}/scales", '', qos=0, retain=True)  
  client.publish("homie/"+mqtt_client_name+"/shop_overview/products_scales", json.dumps(products_scales), qos=1, retain=True)
  client.publish("homie/"+mqtt_client_name+"/shop_overview/scales_products", json.dumps(scales_products), qos=1, retain=True)
  for k, v in scales_products.items():
    client.publish(f"homie/{mqtt_client_name}/shop_overview/scales_products/{k}", v, qos=0, retain=True)
send_basket_products_scales_to_mqtt()
print(products_scales)

loop_var = True
def signal_handler(sig, frame):
  global loop_var
  logger.info('You pressed Ctrl+C! Preparing for graceful exit.')
  loop_var = False
signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)


#to store all last +/+/state messages
MQTT_last_states = {}

shop_status_last_cycle = shop_status #shop_status_last_cycle is used for stuff which is only done the first time a status is reached
while loop_var:
    ###########################################################################
    # Process MQTT messages
    # important: process them here in the loop, not asyncron in call_back routine
    ###########################################################################

    while not mqtt_queue.empty():
      message = mqtt_queue.get()
      if message is None:
        continue
      logger.debug(f"Process queued MQTT message now: {str(message.payload.decode('utf-8'))}")

      try:
        m = message.payload.decode("utf-8")
        logger.debug("Topic: "+message.topic+" Message: "+m)

        msplit = re.split("/", message.topic)
        if len(msplit) == 3 and msplit[2].lower() == "set_shop_status":
            if len(m) > 0:
              set_shop_status(int(m))
            else:
              set_shop_status(0)

        #store last message contents for all +/+/state
        if len(msplit) == 3 and msplit[2].lower() == "state":
          temp_m = 0
          try:
            temp_m = int(m)
          except:
            logger.warning(f"State for {msplit[1]} was not numeric: {m}")
          MQTT_last_states[msplit[1]] = temp_m
          logger.debug(f"{MQTT_last_states=}")

        #Fernsteuerung durch public_wegpage_viewer / supplier.php
        if message.topic.lower() == "homie/public_webpage_viewer/message_input":
          if shop_status==10:
              if m == "1": #öffnen
                logger.info("public_webpage_viewer öffnet den Laden.")
                set_shop_status(0)
                client.publish("homie/display-power-control-shop-door/power/set", '1', qos=1, retain=False) #schalte das Display außen ein 
          if shop_status in (9, 1, 5, 16):
              if m == "0": #schließen
                logger.info("public_webpage_viewer schließt den Laden.")
                set_shop_status(10)
                client.publish("homie/display-power-control-shop-door/power/set", '0', qos=1, retain=False) #schalte das Display außen aus 
                client.publish("homie/display-power-control-shop-display01/power/set", '0', qos=1, retain=False)
                client.publish("homie/display-power-control-shop-display02/power/set", '0', qos=1, retain=False)
                client.publish("homie/fsr-control/innen/licht/set", '0', qos=1, retain=False)  # Licht aus
        
        #Fernsteuerung durch supplier_full.php
        if len(msplit) == 5 and msplit[1].lower() == "public_webpage_supplier" and msplit[3].lower() == "cmd" and msplit[4].lower() == "set_shop_status":
#          if not shop_status in (19,): #Bei bei techn. Wartung soll diese Funktion nicht unterstützt werden
            logger.info(f"set_shop_status supplier_full.php mit MQTT-topic und Parameter: {message.topic.lower()} {m}")
            try:
              v = int(m)
              set_shop_status(v)
            except:
              logger.warning(f"Fehler: Parameter {m} konnte nicht in integer umsetzt werden. Shop_Status nicht geändert.")
#          else:
#            logger.warning(f"Fehler: set_shop_status durch supplier_full.php mit MQTT-topic: {message.topic.lower()}. Kann jedoch nicht durchgeführt werden, da shop_status: {shop_status}")
        if len(msplit) == 5 and msplit[1].lower() == "public_webpage_supplier" and msplit[3].lower() == "cmd" and msplit[4].lower() == "open_door":
          if not shop_status in (19,): #Bei bei techn. Wartung soll diese Funktion nicht unterstützt werden
            logger.info(f"Türöffner aktiviert durch supplier_full.php mit MQTT-topic: {message.topic.lower()}")
            client.publish("homie/fsr-control/innen/tuerschliesser/set", '1', qos=2, retain=False)  # send door open impuls
            client.publish("homie/fsr-control/innen/licht/set", '1', qos=1, retain=False)  # Licht an
          else:
            logger.warning(f"Fehler: Türöffner durch supplier_full.php mit MQTT-topic: {message.topic.lower()}. Kann jedoch nicht durchgeführt werden, da shop_status: {shop_status}")
        if len(msplit) == 5 and msplit[1].lower() == "public_webpage_supplier" and msplit[3].lower() == "cmd" and msplit[4].lower() == "close_shop":
          if shop_status in (0,1,7,13,16,6,18,9): #nur wenn auf Kunden gewartet wird, darf geschlossen werden, oder beim/nach dem Einräumen und Kundenhilfe
            set_shop_status(10)
            logger.info(f"Laden wurde geschlossen durch supplier_full.php mit MQTT-topic: {message.topic.lower()}")
            client.publish("homie/fsr-control/innen/licht/set", '0', qos=1, retain=False)  # Licht aus
          else:
            logger.warning(f"Fehler: Laden schließen durch supplier_full.php mit MQTT-topic: {message.topic.lower()}. Kann jedoch nicht durchgeführt werden, da shop_status: {shop_status}")
        if len(msplit) == 5 and msplit[1].lower() == "public_webpage_supplier" and msplit[3].lower() == "cmd" and msplit[4].lower() == "open_shop":
          if shop_status in (6,18,10,9): #nur nach dem Einräumen und wenn Laden geschlossen und Kundenhilfe
            set_shop_status(0)
            client.publish("homie/display-power-control-shop-door/power/set", '1', qos=1, retain=False) #schalte das Display außen ein
            logger.info(f"Laden wurde geöffnet durch supplier_full.php mit MQTT-topic: {message.topic.lower()}")
          else:
            logger.warning(f"Fehler: Laden öffnen durch supplier_full.php mit MQTT-topic: {message.topic.lower()}. Kann jedoch nicht durchgeführt werden, da shop_status: {shop_status}")
        if len(msplit) == 5 and msplit[1].lower() == "public_webpage_supplier" and msplit[3].lower() == "cmd" and msplit[4].lower() == "start_assign":
          if not shop_status in (8,19): #Bei technischen Fehler soll diese Funktion nicht gegeben sein. Ebenfalls bei techn. Wartung nicht
            set_shop_status(6)
            logger.info(f"Produktzuordnung durch supplier_full.php mit MQTT-topic: {message.topic.lower()}")
          else:
            logger.warning(f"Fehler: Produktzuordnung durch supplier_full.php mit MQTT-topic: {message.topic.lower()}. Kann jedoch nicht durchgeführt werden, da shop_status: {shop_status}")

        #request update from db
        if len(msplit) == 3 and msplit[2].lower() == "update_data_from_db":
          get_all_data_from_db()
          send_basket_products_scales_to_mqtt()

        #eine Waage wurde gedrückt, Empfang von Nachrichten wie: homie/scale-shop-shelf06-0-1.2.5.5-1.0/scales/4930370A3419/touched
        if len(msplit) == 5 and msplit[2].lower() == "scales" and msplit[4].lower() == "touched":
          if shop_status == 6: #Einräum-Modus aktiv, noch keine Waage ausgewählt
            if m == "1":
              status_last_touched_shelf_str = msplit[1].lower() #scale-shop-shelf06-0-1.2.5.5-1.0
              status_last_touched_scale_str = msplit[3].lower() #4930370A3419
              logger.info(f"Auf dem Regal {status_last_touched_shelf_str} wurde die folgende Waage gedrückt: {status_last_touched_scale_str}")
              client.publish("homie/"+mqtt_client_name+"/last_touched/shelf_str", status_last_touched_shelf_str, qos=1, retain=True)
              client.publish("homie/"+mqtt_client_name+"/last_touched/scale_str", status_last_touched_scale_str, qos=1, retain=True)

              for v in combined_scales_support.search_scale_and_convert_to_array(status_last_touched_scale_str): #falls doppeltbreite Waagen, dann beide LEDs ein
                logger.info(f"Regal {status_last_touched_shelf_str} mit Waage {v} ausgewält und LED wird eingeschaltet.")
                client.publish(f"homie/{status_last_touched_shelf_str}/cmd/scales/{v.upper()}/led", "1", qos=1, retain=False)

              #produkt-waagen-zuordnung nachschlagen
              if status_last_touched_scale_str in scales_products:
                client.publish("homie/"+mqtt_client_name+"/last_touched/product_id", scales_products[status_last_touched_scale_str], qos=1, retain=True)
                client.publish("homie/tts-shop-shelf02/say", f"Hier liegt: {products[scales_products[status_last_touched_scale_str]]['ProductName']}.", qos=1, retain=False)
              else:
                client.publish("homie/tts-shop-shelf02/say", f"Dieser Waage ist noch kein Produkt zugeodnet.", qos=1, retain=False)

              set_shop_status(18)

        if message.topic.lower() == "homie/"+mqtt_client_name+"/last_touched/reset":
          if shop_status==18:
            set_shop_status(6) #reset der LED und der Variablen werden in dieser Routine durchgeführt
          else:
            logger.warning(f"Reset von last_touched nicht ausgeführt, da shop_status nicht == 18.")

        if ( (message.topic.lower() == "homie/"+mqtt_client_name+"/last_touched/set_product_id") or 
          (len(msplit) == 5 and msplit[1].lower() == "public_webpage_supplier" and msplit[3].lower() == "cmd" and msplit[4].lower() == "assign_product") ):
          if status_last_touched_shelf_str and status_last_touched_scale_str and shop_status == 18:
            if m.isdigit():
              m = int(m)
            else: 
              m = None
            
            db_prepare()
            set_product_id_to_scale(status_last_touched_scale_str, m)
            db_close()

            if m:
              if m in products:
                client.publish("homie/tts-shop-shelf02/say", f"{products[m]['ProductName']}. wurde zugeordnet", qos=1, retain=False)
              else:
                client.publish("homie/tts-shop-shelf02/say", f"Fehler: Waage wurde einem Produkt zugeordnet, welches jedoch nicht in Datenbank vorhanden ist.", qos=1, retain=False)
                logger.warning("Fehler: Waage wurde einem Produkt zugeordnet, welches jedoch nicht Datenbank vorhanden ist.")
            else:
              client.publish("homie/tts-shop-shelf02/say", "Kein Produkt mehr zugeodnet.", qos=1, retain=False)

            #Aktuelle Daten von DB einlesen und versenden
            logger.info("Lese die DB neu ein und verschicke sie per MQTT")
            get_all_data_from_db()
            send_basket_products_scales_to_mqtt()

            set_shop_status(6) #reset der LED und der Variablen werden in dieser Routine durchgeführt
          else:
            logger.warning(f"Produkt konnte nicht gesetzt werden, da die Variablen nicht gefüllt sind oder weil shop_status nicht 18 ist: {status_last_touched_shelf_str=} {status_last_touched_scale_str=} {shop_status=}")

        #Unterstützung, um über die Webseite supplier_full.php mehrere Waagen gleichzeitig mit Produkte zu besetzen
        #homie/public_webpage_supplier/lfr_akern/cmd/assign_multiple_products {"435339f11338":179,"49303700312d":2,"49303702261d":131}
        if (len(msplit) == 5 and msplit[1].lower() == "public_webpage_supplier" and msplit[3].lower() == "cmd" and msplit[4].lower() == "assign_multiple_products"):
          if shop_status in (6,18,):
            logger.info(f"Neue Produkt-Waagen-Zuordnung (assign_multiple_products) erhalten. Eintragen: {m}")
            t = json.loads(m)
            if len(t) >0:
              db_prepare()
              for k,v in t.items():
                logger.info(f"Eintragen von: {k=} {v=}")
                set_product_id_to_scale(k, v)
              db_close()

              #Aktuelle Daten von DB einlesen und versenden
              logger.info("Lese die DB neu ein und verschicke sie per MQTT")
              get_all_data_from_db()
              send_basket_products_scales_to_mqtt()
            else:
              logger.info("Es wurden keine Einträge übermittelt.")
            set_shop_status(6) #reset der LED und der Variablen werden in dieser Routine durchgeführt
          else:
            logger.warning(f"Produkte konnten nicht gesetzt werden, weil shop_status nicht 6 oder 18 ist: {shop_status=}")

        #Neues Produkt in Datenbank anlegen, gesendet von der Lieferanten-Webseite
        #homie/public_webpage_supplier/lfr_akern/cmd/create_product {"Supplier":"Hemmes", "ProductName":"Äpfel", "ProductDescription":"frisch vom Feld", "PricePerUnit":2.5, "kgPerUnit":1.1, "VAT":0.07}
        if (len(msplit) == 5 and msplit[1].lower() == "public_webpage_supplier" and msplit[3].lower() == "cmd" and msplit[4].lower() == "create_product"):
          if not shop_status in (19,): #nur weiter, falls Laden nicht in Technik-Wartung
            logger.info(f"Neues Produkt wird in Datenbank eingetragen: {m}")
            t = json.loads(m)
            if len(t) >0:
              db_prepare()
              try:
                sql_str = "INSERT INTO `Products` (`Supplier`, `ProductName`, `ProductDescription`, `PricePerUnit`, `kgPerUnit`, `VAT`) VALUES (?, ?, ?, ?, ?, ?); "
                logger.info(f"Execute the following SQL Str: {sql_str} with ({t=})")
                cur.execute(sql_str, (t["Supplier"], t["ProductName"], t["ProductDescription"], t["PricePerUnit"], t["kgPerUnit"], t["VAT"], )) #the last comma here is super important, if only one elem provided
                conn.commit()
                last_product_id_inserted = cur.lastrowid
                logger.info(f"Last Inserted ID into Products: {last_product_id_inserted}")
              except mariadb.Error as e:
                logger.warning(f"Error while SQL INSERT: {e}")
              db_close()

              #Aktuelle Daten von DB einlesen und versenden
              logger.info("Lese die DB neu ein und verschicke sie per MQTT")
              get_all_data_from_db()
              send_basket_products_scales_to_mqtt()
            else:
              logger.info("Es wurden keine Einträge übermittelt.")
          else:
            logger.warning(f"Neues Produkt konnte nicht eingetragen werden, da der Laden nicht bereit ist: {shop_status=}")


        #Bestehendes Produkt in Datenbank ändern, gesendet von der Lieferanten-Webseite
        #homie/public_webpage_supplier/lfr_gast/cmd/edit_product {"ProductName":"test","ProductDescription":"","PriceType":"0","PricePerUnit":"1.00","kgPerUnit":"0.500","VAT":"0.07","Supplier":"test"}
        if (len(msplit) == 5 and msplit[1].lower() == "public_webpage_supplier" and msplit[3].lower() == "cmd" and msplit[4].lower() == "edit_product"):
          if not shop_status in (19,2,3,4,9,11,12,14,15,17): #nur weiter, falls Laden nicht in Technik-Wartung, oder Kunde im Laden
            logger.info(f"Bestehendes Produkt ändern: {m}")
            t = json.loads(m)
            if len(t) >0:
              db_prepare()
              try:
                sql_str = "UPDATE `Products` SET `Supplier` = ?, `ProductName` = ?, `ProductDescription` = ?, `PriceType` = ?, `PricePerUnit` = ?, `kgPerUnit` = ?, `VAT` = ? WHERE `Products`.`ProductID` = ?; "
                logger.info(f"Execute the following SQL Str: {sql_str} with ({t=})")
                cur.execute(sql_str, (t["Supplier"], t["ProductName"], t["ProductDescription"], t["PriceType"], t["PricePerUnit"], t["kgPerUnit"], t["VAT"], t["ProductID"], )) #the last comma here is super important, if only one elem provided
                conn.commit()
                logger.info(f"Änderung erfolgreich.")
              except mariadb.Error as e:
                logger.warning(f"Error while SQL Update: {e}")
              db_close()

              #Aktuelle Daten von DB einlesen und versenden
              logger.info("Lese die DB neu ein und verschicke sie per MQTT")
              get_all_data_from_db()
              send_basket_products_scales_to_mqtt()
            else:
              logger.info("Es wurden keine Einträge übermittelt.")
          else:
            logger.warning(f"Bestehendes Produkt konnte nicht geändert werden, da der Laden nicht bereit ist oder ein Kunde einkäuft: {shop_status=}")

        #Produkt in Datenbank löschen, gesendet von der Lieferanten-Webseite, ProductID muss übergeben werden
        # wird nur ausgeführt, falls keiner Waage zugewiesen
        #homie/public_webpage_supplier/lfr_akern/cmd/delete_product 206
        if (len(msplit) == 5 and msplit[1].lower() == "public_webpage_supplier" and msplit[3].lower() == "cmd" and msplit[4].lower() == "delete_product"):
          if not shop_status in (19,): #nur weiter, falls Laden nicht in Technik-Wartung
            logger.info(f"Produkt in Datenbank löschen, ProduktID: {m=}")
            if m.isdigit():
              m = int(m)
            else: 
              m = None

            if m:
              #Test, ob ProductID keiner Waage zugewiesen
              res = False
              for k,v in scales_products.items():
                if v == m:
                  res = True #ist einer Waage zugeordnet

              if not res: #Falls keiner Waage zugeordnet
                db_prepare()
                try:
                  sql_str = "DELETE FROM Products WHERE `Products`.`ProductID` = ?; "
                  logger.info(f"Execute the following SQL Str: {sql_str} with ({m=})")
                  cur.execute(sql_str, (m, )) #the last comma here is super important, if only one elem provided
                  conn.commit()
                  logger.info(f"Produkt wurde gelöscht.")
                except mariadb.Error as e:
                  logger.warning(f"Error while SQL DELETE: {e}")
                db_close()

                #Aktuelle Daten von DB einlesen und versenden
                logger.info("Lese die DB neu ein und verschicke sie per MQTT")
                get_all_data_from_db()
                send_basket_products_scales_to_mqtt()
              else:
                  logger.warning("Konnte nicht gelöscht werden, da noch mind. einer Waage zugeordnet.")
            else:
              logger.warning("Es wurden keine nummerische ProductID übermittelt.")
          else:
            logger.warning(f"Produkt konnte nicht gelöscht werden, da der Laden nicht bereit ist: {shop_status=}")

        #Warenkorb korrigieren via Webpage
        #homie/public_webpage_supplier/lfr_akern/cmd/basket/set_product_count {"ProductID":247,"NewCount":"0"}
        if (len(msplit) == 6 and msplit[1].lower() == "public_webpage_supplier" and msplit[3].lower() == "cmd" and msplit[4].lower() == "basket" and msplit[5].lower() == "set_product_count"):
          logger.info(f"Warenkorb-Korrektur steht an: {m=}")
          t = json.loads(m)
          if len(t) >0:
            if "ProductID" in t and "NewCount" in t:
              temp_ProductID = int(t["ProductID"])
              temp_NewCount = int(t["NewCount"])
              actBasketCorrections[temp_ProductID] = temp_NewCount
              logger.info(f"Warenkorb-Korrektur: {actBasketCorrections}")
          else:
            logger.warning(f"Es wurden keine Daten übermittelt.")



        # tracker information to know immediate person presence
        if len(msplit) == 3 and msplit[1].lower() == "shop-track-collector" and msplit[2].lower() == "pixels-above-reference":
            pixels_above_reference = int(m)
        # tof camera information to know immediate person presence
        if len(msplit) == 3 and msplit[1].lower() == "tof-cam-shop-tof" and msplit[2].lower() == "value":
            tofcamshoptof_value = float(m)
        status_no_person_in_shop = True if tofcamshoptof_value < 100 and pixels_above_reference == 0 else False

        # products withdrawal
        # eg homie/scale-shop-shelf02-0-1.2-1.0/scales/493037101F4B/mass
        if len(msplit) == 5 and msplit[2].lower() == "scales" and msplit[4].lower() == 'mass':
            scales_mass_actual[msplit[3].lower()] = float(m)

        #mosquitto_pub -t 'homie/door/Pin1' -m 1
        # Door open/close message
        if message.topic.lower() == "homie/door/pin1":
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

        #Kartenlesegerät busy als globale Variable zur Verfügung stellen
        if message.topic.lower() == "homie/cardreader/busy":
          cardreader_busy = True if m == "1" else False
          logger.debug(f"cardreader busy variable set to {cardreader_busy}")
          if shop_status == 1 and cardreader_busy == False:
            # Timeout von Kartenlesegerät passiert, neu anstoßen:
            set_shop_status(16)

        # Receive receipes from Kartenlesegerät
        if message.topic.lower() == "homie/cardreader/text_block":
          cardreader_last_textblock = m
          logger.info(f"cardreader cardreader_last_textblock variable set to {cardreader_last_textblock}")

        #Ergebnis vom Kartenlesegerät zu Preauth
        if message.topic.lower() == "homie/cardreader/preauth_res":
          logger.info("Preauth-Ergebnis vom Kartenlesegerät eingegangen. Nur beachten, falls Shop-Status == 1")
          if shop_status == 1:
            try:
              m_json = json.loads(m)
              # m enthält JSON: return_code_completion==0: Erfolgreich Preauth gesetzt
              if "return_code_completion" in m_json:
                if m_json["return_code_completion"] == 0: # Erfolgreich
                  set_shop_status(2) #Kunde authentifiziert/Waagen tara wird ausgeführt
                elif m_json["return_code_completion"] == 1: # Timeout
                  set_shop_status(16) #Timeout Kartenterminal
                else:
                  logger.info(f"Kartenlesegerät gibt: {m_json['return_code_completion']}")
                  set_shop_status(13) #Irgendein Fehler vom Kartenlesegerät
              else:
                logger.warning("Kartenlesegerät Rückgabe enthält kein 'return_code_completion'.")
                set_shop_status(13) #Irgendein Fehler vom Kartenlesegerät
            except:
              logger.warning(f"Kartenlesegerät gibt kein JSON zurück, obwohl erwartet: {m=}")
              set_shop_status(13) #Irgendein Fehler vom Kartenlesegerät
          else:
            logger.warning(f"{shop_status=}, daher kein Wechsel zu Zustand 16.")

        #Ergebnis vom Kartenlesegerät zu Book
        if message.topic.lower() == "homie/cardreader/book_total_res":
          logger.info("Betrag buchen vom Preauth vom Kartenlesegerät eingegangen. Nur beachten, falls Shop-Status == 17")
          if shop_status == 17:
            try:
              m_json = json.loads(m)
              # Hier fehlt noch Code, der überprüft, ob es wirklich geklappt hat.
              logger.info("Betrag wurde erfolgreich der Karte belastet.")
              
              # prepare invoice_json to be sent for outside customer display
              p = []
              ab = actBasket["data"]
              for i in ab:
                v=ab[i]
                temp_VAT = 2 #standard / full VAT
                if v["VAT"] == 0.07: temp_VAT = 1 #reduced VAT
                if v["VAT"] == 0.0: temp_VAT = 0 #no VAT
                p.append([v["ProductName"], v["withdrawal_units"], v["PricePerUnit"], temp_VAT])
              a={'d': {"p":p, 'c': cardreader_last_textblock, 't':int(time.time())}}
              logger.info(f"Kassenbon: {a=}")
              client.publish(f"homie/{mqtt_client_name}/invoice_json", json.dumps(a), qos=1, retain=True)

              set_shop_status(5) #Anzeige des Belegs
            except:
              logger.warning(f"Kartenlesegerät gibt kein gültiges JSON zurück oder anderer Fehler: {m=}")
              set_shop_status(8) #Technischer Fehler
          else:
            logger.warning(f"{shop_status=}. Die MQTT-Nachricht kommt unerwartet, daher Fehler!")
            set_shop_status(8) #Technischer Fehler

      except Exception as err:
        traceback.print_tb(err.__traceback__)
    ############################################################################




    actBasketProducts = {}
    actSumTotal = 0
    actProductsCount = 0
    actProductsMasses = {}

    #Zuerst die gesamt Masse zu jedem Produkt bestimmen. Gleiche Produkte können auf mehreren Waagen stehen
    for k, temp_product_id in scales_products.items():
      if temp_product_id in products: # should always be true, unless error in db (assignment scales <-> products) 
        if (k in scales_mass_reference) and (k in scales_mass_actual): #Hat eine Waage einen Wert zurückgeliefert, auf dem das Produkt liegt?
          if isinstance(products[temp_product_id]['kgPerUnit'], (int, float)): #valid number? to prevent division by zero
            if products[temp_product_id]['kgPerUnit'] > -1.001: #mind. -1001g per product, to allow for deposit
              if temp_product_id in actProductsMasses:
                actProductsMasses[temp_product_id] += scales_mass_reference[k] - scales_mass_actual[k]
              else:
                actProductsMasses[temp_product_id] = scales_mass_reference[k] - scales_mass_actual[k]

    #Jetzt die Stückzahlen zu den Massen bestimmen
    actNumberOfDeposit = 0
    for temp_product_id, mass in actProductsMasses.items():
      temp_count = mass / products[temp_product_id]['kgPerUnit'] #double as return
      if not math.isnan(temp_count):
        temp_count = round(temp_count)

        # Warenkorb Korrekturen, die durch die Webseite kamen, berücksichtigen
        if temp_product_id in actBasketCorrections:
          temp_count = actBasketCorrections[temp_product_id]

        if temp_count<=0 or temp_count>100: #the 100 here has no deeper meaning
          pass
#          if temp_count !=0:  
#            logger.warning(f"Ungültige Warenanzahl erreicht: {temp_count=}")
        else:
          temp_product = copy.deepcopy(products[temp_product_id])
          temp_product['withdrawal_units'] = temp_count
          temp_product['price'] = temp_count * temp_product['PricePerUnit']
          actBasketProducts[temp_product_id] = temp_product

          actProductsCount += temp_count

          if temp_product['PriceType'] == 2:
            actNumberOfDeposit += temp_count

    #Add Deposit to basket
    if actNumberOfDeposit>0:
      depositProductID_In_DB = 250
      temp_product = copy.deepcopy(products[depositProductID_In_DB])
      temp_product['withdrawal_units'] = actNumberOfDeposit
      temp_product['price'] = actNumberOfDeposit * temp_product['PricePerUnit']
      actBasketProducts[depositProductID_In_DB] = temp_product
      #hint: do not increase actProductsCount

    for k, v in actBasketProducts.items():
      actSumTotal += v['price']

    actBasket = {"data": actBasketProducts, "total": actSumTotal, "products_count": actProductsCount, "corrections": actBasketCorrections}
    if last_actBasket != actBasket: #change to basket? --> publish!
        client.publish("homie/"+mqtt_client_name+"/actualBasket", json.dumps(actBasket), qos=1, retain=True)
        last_actBasket = actBasket


    ############################################################################
    # FSM
    ############################################################################
    next_shop_status = shop_status
    if shop_status == 0: #"Geräte Initialisierung"
        next_shop_status = 7
    elif shop_status == 1: #Bereit, kein Kunde im Laden
      #Überprüfung: ob alle systeme funktionieren. Dies passiert bei Schritt 1 und 7
      all_values_are_one = all(value == 1 for value in MQTT_last_states.values())
      if not all_values_are_one:
        logger.warning(f"There is minimum one sub system in state=0: {MQTT_last_states=}")
        next_shop_status = 8 #technischer Fehler!
      # Wechsel zu 16 (Falls Kartenleser Timeout), oder 2 (OK) passiert in MQTT-onMessage, Wechsel zu 13 als Standard-Timeout
    elif shop_status == 2: #"Kunde authentifiziert / Waagen tara wird ausgeführt
        #Waagen tara ausführen:
        actBasketCorrections = {} #Reset Warenkorb Korrekturen bei neuem Kunden
        scales_mass_reference = copy.deepcopy(scales_mass_actual) #always use deepcopy, see: https://stackoverflow.com/questions/2465921/how-to-copy-a-dictionary-and-only-edit-the-copy
        client.publish("homie/fsr-control/innen/tuerschliesser/set", '1', qos=2, retain=False)  # send door open impuls
        client.publish("homie/shop_controller/generic_pir/innen_licht", '{"v":1,"type":"Generic_PIR"}', qos=1, retain=False)
        client.publish("homie/display-power-control-shop-display01/power/set", '1', qos=1, retain=False)
        client.publish("homie/display-power-control-shop-display02/power/set", '1', qos=1, retain=False)
        next_shop_status = 14 # Bitte Laden betreten
    elif shop_status == 3: #Kunde betritt/verlässt gerade den Laden
        pass # Weiter gehts zu 11 in MQTT onMessage
    elif shop_status == 4: # Möglicherweise: Einkauf finalisiert / Kunde nicht mehr im Laden"
        if shop_status_last_cycle != shop_status: # Damit es nur 1x ausgeführt wird.
          client.publish("homie/tts-shop-shelf02/say", 'Kein Kunde mehr im Laden. Falls doch, dann melden sie uns bitte diesen Fehler.', qos=1, retain=False)
        #Tür==offen: Wechsel zu 3 über MQTT-Message
        if status_no_person_in_shop == False:
          next_shop_status = 12
    elif shop_status == 5: #"Kassenbonanzeige
        pass # geht über timout weiter zum nächsten Zustand
    elif shop_status == 6: # Einräumen durch Betreiber
        pass
    elif shop_status == 7: #"Warten auf: Vorbereitung für nächsten Kunden"
        cardreader_last_textblock = "" # this typically stores receipes from the card terminal, clear it for new customer
        scales_mass_reference = copy.deepcopy(scales_mass_actual) #Warenkorb zurücksetzen
        client.publish("homie/shop_controller/invoice_json", "", qos=1, retain=True)
        client.publish("homie/shop_controller/generic_pir/innen_licht", '{"v":0,"type":"Generic_PIR"}', qos=1, retain=False)
        
        #Überprüfung: ob alle systeme funktionieren. Dies passiert bei Schritt 1 und 7
        all_values_are_one = all(value == 1 for value in MQTT_last_states.values())
        if not all_values_are_one:
          logger.warning(f"There is minimum one sub system in state=0: {MQTT_last_states=}")
          #next_shop_status = 8 #technischer Fehler! #wird hier nicht aufgerufen, sondern auf das Timeout des Zustands vertraut.
        else:
          next_shop_status = 16
    elif shop_status == 8: #"Technischer Fehler aufgetreten"
        pass
    elif shop_status == 9: #"Kunde benötigt Hilfe"
        pass
    elif shop_status == 10: #"Laden geschlossen"
        pass
    elif shop_status == 11: # Kunde möglichweise im Laden
        if shop_status_last_cycle != shop_status: # Damit es nur 1x ausgeführt wird.
          client.publish("homie/tts-shop-shelf02/say", 'Willkommen in unserem Bauernladen.', qos=1, retain=False)
        if (time.time()-shop_status_last_change_timestamp > 1.5): # Zur Vermeidung von Melde-Verzögerungen der Distanzsensoren erst nach einiger Zeit auswerten
          if status_no_person_in_shop == False: # Kunde ist im Laden
            next_shop_status = 12 # Kunde sicher im Laden
    elif shop_status == 12: # Kunde sicher im Laden
        if shop_status_last_cycle != shop_status: # Damit es nur 1x ausgeführt wird.
          client.publish("homie/tts-shop-shelf02/say", "Sie können nun einkaufen.", qos=1, retain=False)
        if actSumTotal>max_money_preauth:
            set_shop_status(20) #Zustand: Zuviel im Warenkorb
        if status_no_person_in_shop == False: #Eine Person ist innen gefunden worden. 
            confirm_shop_status() # Diesen Zustand bestätigen, damit kein Timeout auftritt.
                                  # Diese Zeilen zusammen mit dem Timeout bewirken, dass falls ein Kunde den Laden bereits verlassen hat und die Elektronik
                                  # fehlerhafterweise DOCH eine Person detektiert hat, dass dies irgendwann (nach Ablauf des Timeouts) wieder korrigiert wird.
        #pass # Tür==offen: Wechsel zu 3 über MQTT-Message
    elif shop_status == 20: # Zuviel im Warenkorb
        if actSumTotal<=max_money_preauth:
            set_shop_status(12) #Zustand: Zuviel im Warenkorb
    elif shop_status == 13: # Fehler bei Authentifizierung
        pass # geht über Timeout weiter zu 1
    elif shop_status == 14: # Bitte Laden betreten
      pass
      # Tür offen in MQTT-Message: Wechsel zu next_shop_status = 3
    elif shop_status == 15: # Abrechnung wird vorbereitet
        # Abrechnung durchführen
        last_invoiceid_inserted = None
        try:
          sql_str = "INSERT INTO `Invoices` (`Products`, `ProductsCount`, `TotalAmount`) VALUES (?, ?, ?); "
          actBasket_str = json.dumps(actBasket)
          logger.info(f"Executed the following SQL Str: {sql_str} with ({actBasket_str})")
          db_prepare()
          try:
            cur.execute(sql_str, (actBasket_str, actBasket['products_count'], actBasket['total'], )) #the last comma here is super important, if only one elem provided
            conn.commit()
            last_invoiceid_inserted = cur.lastrowid
            logger.info(f"Last Inserted ID into Invoices: {last_invoiceid_inserted}")
          except mariadb.Error as e:
            logger.warning(f"Error while SQL INSERT: {e}")
          db_close()

          if last_invoiceid_inserted:
            db_prepare()
            for k,v in actBasket['data'].items():
              sql_str = "INSERT INTO `InvoiceProducts` (`InvoiceID`, `ProductID`, `Supplier`, `ProductName`, `ProductDescription`, `PriceType`, `PricePerUnit`, `kgPerUnit`, `WithdrawalUnits`, `Price`, `VAT`) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?); "
              logger.info(f"Executed the following SQL Str: {sql_str} with ({last_invoiceid_inserted}, {v})")
              try:
                cur.execute(sql_str, (last_invoiceid_inserted, v['ProductID'], v['Supplier'], v['ProductName'], v['ProductDescription'], v['PriceType'], 
                                      v['PricePerUnit'], v['kgPerUnit'], v['withdrawal_units'], v['price'], v['VAT'], )) #the last comma here is super important!!
                conn.commit()
                logger.info("Last Inserted ID into InvoiceProducts: {}".format(cur.lastrowid))
              except mariadb.Error as e:
                logger.warning(f"Error while SQL INSERT: {e}")
            db_close()

          # Book money from reservation
          total_money_tobook_incents_str = round(actBasket["total"]*100)
          client.publish("homie/cardreader/cmd/book", total_money_tobook_incents_str, qos=1, retain=False)

          next_shop_status = 17 # Weiter zu: Einkauf beendet und abgerechnet
        except:
          next_shop_status = 8
          logger.warning("Error while saving the basket in database.")
    elif shop_status == 16: # Timeout Kartenterminal
      if cardreader_busy == False:
        logger.info(f"Kartenlesegerät erhält wieder den Anstoß, eine Preauth durchzuführen.")
        client.publish("homie/cardreader/cmd/pre", f"{max_money_preauth*100:.0f}", qos=1, retain=False) #money in cents
        next_shop_status = 1
      else:
        logger.warning(f"Kein Pre-Auth an Kartenlesegerät gesendet, da {cardreader_busy=}. Warten.")
    elif shop_status == 17: # Warten auf: Kartenterminal Buchung erfolgreich
      pass # Rückmeldung Kartenlesegerät über MQTT-Message
    elif shop_status == 18: # Einräumen durch Betreiber, Waage ausgewählt
      pass
    else:
      logger.error(f"Unbekannter {shop_status=} Wert.")

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


# Terminating everything
logger.info(f"Terminating. Cleaning up.")

set_shop_status(10) # Laden geschlossen

client.publish("homie/"+mqtt_client_name+"/state", '0', qos=1, retain=True)

time.sleep(1) #to allow the published message to be delivered.

client.loop_stop()
client.disconnect()

logger.info("Program stopped.")

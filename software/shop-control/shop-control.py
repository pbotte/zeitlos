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

logging.basicConfig(level=logging.WARNING, format='%(asctime)-6s %(levelname)-8s  %(message)s')
logger = logging.getLogger("Shop Controller")

parser = argparse.ArgumentParser(description='Shop Controller.')
parser.add_argument("-v", "--verbosity", help="increase output verbosity", default=0, action="count")
parser.add_argument("-b", "--mqtt-broker-host", help="MQTT broker hostname. default=localhost", default="localhost")
parser.add_argument("-t", "--timeout", help="timeout in seconds. default=1h", default=100*60*60, type=int)
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
scales_products = {}
scales_mass_reference = {} #masses before client started shopping
scales_mass_actual = {}
def get_all_data_from_db():
    global products, scales_products
    db_prepare()
    cur.execute("SELECT ProductID, ProductName, ProductDescription, PriceType, PricePerUnit, kgPerUnit, VAT FROM Products ") 
    for ProductID, ProductName, ProductDescription, PriceType, PricePerUnit, kgPerUnit, VAT in cur: 
        products[ProductID] = {"ProductID":ProductID, "ProductName":ProductName, "ProductDescription": ProductDescription, 
        "PriceType": PriceType, "PricePerUnit":PricePerUnit, "kgPerUnit":kgPerUnit, "VAT": VAT}
    cur.execute("SELECT ProductID, ScaleID FROM Products_Scales GROUP BY ScaleID"); #Group By verhindert, falls in der Datenbank zwei Produkte für eine Waage eingetragen sind.
    for ProductID, ScaleID in cur:
        scales_products[ScaleID.lower()] = ProductID
    logger.debug(f"products from db: {products=}")
    logger.debug(f"scales_products from db: {scales_products=}")
    db_close()

get_all_data_from_db()

def on_connect(client, userdata, flags, rc):
    if rc == 0:
        logger.info("MQTT connected OK. Return code "+str(rc))
        client.subscribe("homie/+/scales/+/mass") #eg homie/scale-shop-shelf02-0-1.2-1.0/scales/493037101F4B/mass
        client.subscribe("homie/"+mqtt_client_name+"/set_shop_status")
        client.subscribe("homie/"+mqtt_client_name+"/update_data_from_db")
        client.subscribe("homie/shop-track-collector/pixels-above-reference")
        client.subscribe("homie/public_webpage_viewer/message_input")
        client.subscribe("homie/door/#")
        client.subscribe("homie/cardreader/#")

        logger.debug("MQTT: Subscribed to all topics")
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
    6: "ungenutzt",
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
    }
shop_status_timeout = {
    0: {'time':10,'next':8}, #Geräte Initialisierung
    1: {'time':120,'next':8}, #Bereit, Keine Kunde im Laden. Kartenterminal aktiv. Timeout da ein Timeout vom Terminal erwartet wird
    2: {'time':10,'next':8}, #Kunde authentifiziert/Waagen tara wird ausgeführt
    3: {'time':60*10,'next':9}, #Kunde betritt/verlässt gerade den Laden
    4: {'time':10,'next':15}, # Möglicherweise: Einkauf finalisiert & Kunde nicht mehr im Laden
                              # Falls die Sensoren nicht alles abdecken oder durch IR-Licht gestört werden, 
                              # dann hier einen größeren Zeit-Wert sicherheitshalber angeben.
    5: {'time':60,'next':7}, # Einkauf abgerechnet, Kassenbon-Anzeige
    6: None, # Zustand aktuell nicht genutzt
    7: {'time':30,'next':8}, #Warten auf: Vorbereitung für nächsten Kunden
    8: None, # Technischer Fehler aufgetreten
    9: None, # Kunde benötigt Hilfe
    10: None, # Laden geschlossen
    11: {'time': 5,'next':4}, # Kunde möglicherweise im Laden? Falls 5 Sek. kein Kunde im Laden -> Wechsel zu 4
    12: {'time':60*15,'next':9}, # Kunde sicher im Laden
    13: {'time': 3,'next':7}, # Fehler bei Kartenterminal
    14: {'time': 15,'next':15}, # Bitte Laden betreten
    15: {'time': 60,'next': 8}, # Sicher: Kunde nicht mehr im Laden. Kartenterminal buchen!
    16: {'time': 120,'next': 8}, # Timeout Kartenterminal
    17: {'time': 30,'next': 8}, # Warten auf: Kartenterminal Buchung erfolgreich
    }
shop_status_last_change_timestamp = time.time()

def set_shop_status(v):
    global shop_status
    global shop_status_last_change_timestamp
    if shop_status == v:
        return
    shop_status = v
    shop_status_last_change_timestamp = time.time()
    logger.info(f"Set Shop Status to {shop_status}: {shop_status_descr[shop_status]}")

    client.publish("homie/"+mqtt_client_name+"/shop_status", shop_status, qos=1, retain=True)
    client.publish("homie/"+mqtt_client_name+"/shop_status_last_change_timestamp", shop_status_last_change_timestamp, qos=1, retain=True)


cardreader_busy = False # set by MQTT messages from cardreader. When true, do not submit any task to cardreader and simply wait
cardreader_last_textblock = "" # MQTT messages from cardread typically in receipe style from homie/cardreader/text_block

actBasket = {"data": {}, "total": 0, "products_count": 0}
status_no_person_in_shop = None # True if homie/shop-track-collector/pixels-above-reference == 0, else False
status_door_closed = None

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
client.will_set("homie/"+mqtt_client_name+"/state", 'offline', qos=1, retain=True)
client.connect(args.mqtt_broker_host)
client.loop_start()
logger.info("MQTT loop started.")
client.publish("homie/"+mqtt_client_name+"/state", 'online', qos=1, retain=True)


set_shop_status(10) # Laden geschlossen. Sonst kann man den laden eröffnen durch Stromunterbrechung.

last_actBasket = {} #to enable the feature: Send only on change
def send_basket_products_scales_to_mqtt():
  client.publish("homie/"+mqtt_client_name+"/actualBasket", json.dumps(actBasket), qos=1, retain=True)
  client.publish("homie/"+mqtt_client_name+"/shop_overview/products", json.dumps(products), qos=1, retain=True)
  client.publish("homie/"+mqtt_client_name+"/shop_overview/scales_products", json.dumps(scales_products), qos=1, retain=True)
send_basket_products_scales_to_mqtt()

loop_var = True
def signal_handler(sig, frame):
  global loop_var
  logger.info('You pressed Ctrl+C! Preparing for graceful exit.')
  loop_var = False
signal.signal(signal.SIGINT, signal_handler)

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
                

        if len(msplit) == 3 and msplit[2].lower() == "update_data_from_db":
           get_all_data_from_db()
           send_basket_products_scales_to_mqtt()

        # tracker information to know immediate person presence
        if len(msplit) == 3 and msplit[1].lower() == "shop-track-collector" and msplit[2].lower() == "pixels-above-reference":
            status_no_person_in_shop = True if int(m) == 0 else False #all returns true if all elements are true

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
              logger.info("Betrag wurde erfolgreih der Karte belastet.")
              
              # prepare invoice_json to be sent for outside customer display
              p = []
              ab = actBasket["data"]
              for i in ab:
                v=ab[i]
                p.append([v["ProductName"], v["withdrawal_units"], v["PricePerUnit"], 1]) # TODO: variable VAT support: 0:0%, 1:7%, 2:19%
              a={'d': {"p":p, 'c': cardreader_last_textblock, 't':int(time.time())}}
              logger.info(f"Kassenbon: {a=}")
              client.publish("homie/shop_controller/invoice_json", json.dumps(a), qos=1, retain=True)

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

    for k, temp_product_id in scales_products.items():
      if temp_product_id in products: # should always be true, unless error in db (assignment scales <-> products) 
        if (k in scales_mass_reference) and (k in scales_mass_actual): #Hat eine Waage einen Wert zurückgeliefert, auf dem das Produkt liegt?
          if isinstance(products[temp_product_id]['kgPerUnit'], (int, float)): #valid number? to prevent division by zero
            if products[temp_product_id]['kgPerUnit'] > 0.001: #mind. 1g per product
              temp_product = copy.deepcopy(products[temp_product_id])
              temp_count = (scales_mass_reference[k] - scales_mass_actual[k]) / temp_product['kgPerUnit'] #double as return
              if not math.isnan(temp_count):
                temp_count = round(temp_count)
                if temp_count<0: temp_count=0 #no negative numbers of items in basket! Negative numbers only for actProductsCount
                if temp_count>100: 
                  temp_count=100 # set some arbitrarily choosen limits
                  logger.warning("Warenanzahllimit erreicht.")

                if scales_products[k] in actBasketProducts: #in case product is sold on several scales and already in basket
                    actBasketProducts[temp_product_id]['withdrawal_units'] += temp_count
                    actBasketProducts[temp_product_id]['price'] = actBasketProducts[temp_product_id]['withdrawal_units'] * temp_product['PricePerUnit']
                else:
                    temp_product['withdrawal_units'] = temp_count
                    temp_product['price'] = temp_count * temp_product['PricePerUnit']
                    actBasketProducts[temp_product_id] = temp_product
                actProductsCount += temp_count
                if actBasketProducts[temp_product_id]['withdrawal_units'] == 0:
                  actBasketProducts.pop(temp_product_id, None) #Remove from list
    
    for k, v in actBasketProducts.items():
      actSumTotal += v['price']

    actBasket = {"data": actBasketProducts, "total": actSumTotal, "products_count": actProductsCount}
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
       pass
       # Wechsel zu 16 (Falls Kartenleser Timeout), oder 2 (OK) passiert in MQTT-onMessage, Wechsel zu 13 als Standard-Timeout
    elif shop_status == 2: #"Kunde authentifiziert / Waagen tara wird ausgeführt
        #Waagen tara ausführen:
        scales_mass_reference = copy.deepcopy(scales_mass_actual) #always use deepcopy, see: https://stackoverflow.com/questions/2465921/how-to-copy-a-dictionary-and-only-edit-the-copy
        client.publish("homie/fsr-control/innen/tuerschliesser/set", '1', qos=2, retain=False)  # send door open impuls
        client.publish("homie/shop_controller/generic_pir/innen_licht", '{"v":1,"type":"Generic_PIR"}', qos=1, retain=False)
        client.publish("homie/display-power-control-shop-display01/power/set", '1', qos=1, retain=False)
        client.publish("homie/display-power-control-shop-display02/power/set", '1', qos=1, retain=False)
        next_shop_status = 14 # Bitte Laden betreten
    elif shop_status == 3: #Kunde betritt/verlässt gerade den Laden
        pass # Weiter gehts zu 11 in MQTT onMessage
    elif shop_status == 4: # Möglicherweise: Einkauf finalisiert / Kunde nicht mehr im Laden"
        #Tür==offen: Wechsel zu 3 über MQTT-Message
        if status_no_person_in_shop == False:
          next_shop_status = 12
    elif shop_status == 5: #"Kassenbonanzeige
        pass # geht über timout weiter zum nächsten Zustand
    elif shop_status == 6: # ungenutzter Zustand
        next_shop_status = 7
    elif shop_status == 7: #"Warten auf: Vorbereitung für nächsten Kunden"
        cardreader_last_textblock = "" # this typically stores receipes from the card terminal, clear it for new customer
        scales_mass_reference = copy.deepcopy(scales_mass_actual) #Warenkorb zurücksetzen
        client.publish("homie/shop_controller/invoice_json", "", qos=1, retain=True)
        client.publish("homie/shop_controller/generic_pir/innen_licht", '{"v":0,"type":"Generic_PIR"}', qos=1, retain=False)
        next_shop_status = 16
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
       pass
        # Tür offen in MQTT-Message: Wechsel zu next_shop_status = 3
    elif shop_status == 15: # Abrechnung wird vorbereitet
        # Abrechnung durchführen
        try:
          sql_str = "INSERT INTO `Invoices` (`Products`) VALUES (?); "
          actBasket_str = json.dumps(actBasket)
          logger.info(f"Executed the following SQL Str: {sql_str} with ({actBasket_str})")
          db_prepare()
          try:
            cur.execute(sql_str, (actBasket_str,)) #the last comma here is super important!!
            conn.commit()
            logger.info("Last Inserted ID: {}".format(cur.lastrowid))
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
        client.publish("homie/cardreader/cmd/pre", "5000", qos=1, retain=False)
        next_shop_status = 1
      else:
        logger.warning(f"Kein Pre-Auth an Kartenlesegerät gesendet, da {cardreader_busy=}. Warten.")
    elif shop_status == 17: # Warten auf: Kartenterminal Buchung erfolgreich
      pass # Rückmeldung Kartenlesegerät über MQTT-Message
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


set_shop_status(10) # Laden geschlossen

client.disconnect()
client.loop_stop()
logger.info("Program stopped.")

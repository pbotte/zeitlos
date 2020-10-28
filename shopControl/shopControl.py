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
import urllib.request
from hashlib import sha256

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
#        client.subscribe("homie/"+mqtt_client_name+"/+/set")
        client.subscribe("homie/+/state")
        client.subscribe("homie/+/cardread")
        # eg homie/scale0x59363332393115051808/status
        client.subscribe("homie/+/status")
        # eg homie/scale0x59363332393115051808/withdrawal
        client.subscribe("homie/+/withdrawal")
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
status = {'modus': 0, 'cardID': ''}  # modus=0 Verkäufer, =1=Käufer-Modus
scaleInfo = {}
scaleWithdrawal = {}
shopStatus = 0   # 0 = waiting for clients, 1 = client in shop


def on_message(client, userdata, message):
    global WatchDogCounter
    global shopStatus
    m = message.payload.decode("utf-8")
    j = {}
    try:
        j = json.loads(m)
        logger.info("Topic: "+message.topic+" JSON:"+str(j))
    except:
        j['status'] = m
        #logger.error("error on converting MQTT message to JSON.")

    if ("homie/"+mqtt_client_name+"/requestShopStatus" == message.topic):
        shopStatus = 0 #client enters the shop
        client.publish("homie/"+mqtt_client_name+"/shopStatus",
            shopStatus, qos=1, retain=True)

    try:
        msplit = re.split("/", message.topic)
        if len(msplit) == 3 and msplit[2].lower() == "state":
            clientsToMonitor[msplit[1]] = m
        # From RFID Card Reader
        if len(msplit) == 3 and msplit[2].lower() == "cardread":
            status['modus'] = 1
            status['cardID'] = j['cardUID']
            if status['cardID'] in cardID2ClientDetails:
                status['modus'] = cardID2ClientDetails[status['cardID']]['modus']

            WatchDogCounter = args.watchdog_timeout
        if len(msplit) == 3 and msplit[2].lower() == "status":
            msplitScaleID = re.split("x", msplit[1])
            if msplitScaleID[0] == 'scale0':
                scaleInfo[msplitScaleID[1]] = j
                logger.debug("scaleID {}: {}".format(msplitScaleID[1], j))
        if len(msplit) == 3 and msplit[2].lower() == "withdrawal":
            msplitScaleID = re.split("x", msplit[1])
            if msplitScaleID[0] == 'scale0':
                scaleWithdrawal[msplitScaleID[1]] = j
                logger.debug("scaleID (scaleWithdrawal) {}: {}".format(
                    msplitScaleID[1], j))

        if len(msplit) == 4 and msplit[3].lower() == "set":
            if (msplit[2] == "status"):
                # Do something
                pass
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

client.publish("homie/"+mqtt_client_name+"/shopStatus",
               shopStatus, qos=1, retain=True)


WatchDogCounter = args.watchdog_timeout
LastCheckForDoorOpen = 0


while (WatchDogCounter > 0):
    LastHTTPRequest = {}
    if (time.time() - LastCheckForDoorOpen > 1) and (shopStatus == 0): #waiting for clients
        try:
            response = urllib.request.urlopen('http://dorfladen.imsteinert.de/status.php', timeout=1)
            text = response.read().decode('utf-8') # a `str`; this step can't be used if data is binary
            LastHTTPRequest = json.loads(text)
            if (abs(time.time() - LastHTTPRequest['time']) > 10): #time diff between server and local shop control not larger than 10 seconds
                logger.warning('timestamp diff too large: {} seconds'.format(time.time() - LastHTTPRequest['time']) )
            else:
                hashValid = False
                for x in range(30): # check the last 30 seconds
                    tempCode = sha256( '{}{}'.format(args.door_qr_code_secret, math.floor(time.time()) - x).encode('utf-8') ).hexdigest()
                    if (LastHTTPRequest['code'] == tempCode ):
                        hashValid = True
                #logger.info('Hashcode ({}) valid: {}'.format(LastHTTPRequest['code'], hashValid))
                if hashValid:
                    logger.info('Hashcode ({}) valid: {}'.format(LastHTTPRequest['code'], hashValid))
                    shopStatus = 1 #client enters the shop
                    client.publish("homie/"+mqtt_client_name+"/shopStatus",
                                shopStatus, qos=1, retain=True)
                    client.publish("homie/eingangschalten", '1', qos=2, retain=False) # send door open impuls

            WatchDogCounter = 10
        except:
            logger.error("error in processing HTTP Request.")
        LastCheckForDoorOpen = time.time()
    
    if shopStatus == 1: #client in shop
        WatchDogCounter = 10

    filename = 'index.html'

    statusStr = ""
    for s, v in clientsToMonitor.items():
        if s in clientsMQTTPrettyNames:
            s = clientsMQTTPrettyNames[s]
        statusStr += "<tr><td>{}</td><td>".format(s)
        if v == "online":
            statusStr += '<font color="green">OK</font>'
        else:
            statusStr += '<font color="red">FEHLER</font>'
        statusStr += "</td></tr>"
    statusStr = '<table width="100%">'+statusStr+'</table>'

    cardStr = "Modus: Verkäufer. "
    if status['modus'] == 1:
        cardStr = 'Modus: Käufer.'
    cardStr += "<br>"
    if status['cardID'] in cardID2ClientDetails:
        cardStr += "Kundenname: {}".format(
            cardID2ClientDetails[status['cardID']]['name'])
    else:
        if status['cardID'] != "":
            cardStr += "Karte nicht registriert. ({})".format(status['cardID'])

    scaleInfoStr = "{}".format(scaleInfo)
    scaleInfoStr = ""
    for s, v in scaleInfo.items():
        scaleInfoStr += "{}: {} <br>".format(
            v['details']['ProductName'], v['details']['ProductDescription'])
        if s in scaleWithdrawal:
            if scaleWithdrawal[s]['pricingType'] == 0:
                scaleInfoStr += "{}g = {:.2f}€".format(
                    scaleWithdrawal[s]['mass'], scaleWithdrawal[s]['price'])
            if scaleWithdrawal[s]['pricingType'] == 1:
                scaleInfoStr += "{}x = {:.2f}€".format(
                    scaleWithdrawal[s]['mass'], scaleWithdrawal[s]['price'])
        scaleInfoStr += "<br>"

    time.sleep(1-math.modf(time.time())[0]) # make the loop run every second
    WatchDogCounter -= 1

client.disconnect()
client.loop_stop()
logger.info("Program stopped.")

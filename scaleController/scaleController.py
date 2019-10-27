#!/usr/bin/python3

import paho.mqtt.client as paho 
import json
import time
from datetime import datetime
import serial
import logging
import argparse
import sys
import re
import os
import yaml #pip3 install pyyaml

logging.basicConfig(level=logging.WARNING,
                    format='%(asctime)-6s %(levelname)-8s  %(message)s')
logger = logging.getLogger("enocean receiver")

parser = argparse.ArgumentParser(
    description='MQTT EnOcean Receiver from serial devices.')
parser.add_argument("-v", "--verbosity",
                    help="increase output verbosity", default=0, action="count")
parser.add_argument("-b", "--mqtt-broker-host",
                    help="MQTT broker hostname. default=localhost", default="localhost")
parser.add_argument("-t", "--watchdog-timeout",
                    help="timeout in seconds for the watchdog. default=1h", default=100*60*60, type=int)
parser.add_argument("serial_device_name",
                    help="Serial port used, eg /dev/ttyUSB0", type=str)
args = parser.parse_args()
logger.setLevel(logging.WARNING-(args.verbosity *
                                 10 if args.verbosity <= 2 else 20))

logger.info("Watchdog timeout (seconds): "+str(args.watchdog_timeout))
logger.info('Use the following Serial-Device: '+str(args.serial_device_name))


def SendMsgToController(fCmdType, fDataList=None):
    if fDataList is None:
        fDataList = []
    if isinstance(fDataList, str):
        fDataList = [ord(x) for x in list(fDataList)]
    if not isinstance(fDataList, list):
        logger.error("Serial.write(): Data is not in list form. Nothing send.")
        return
    myListLength = len(fDataList)
    aList = [0x5a, 0xa5] # Start Sequence
    aList.extend( [ (fCmdType>>8)&0xff, fCmdType&0xff ] ) #add cmd type bytes
    aList.extend( [ (myListLength>>8)&0xff, myListLength&0xff ] ) #add data length bytes
    aList.extend( fDataList )
    aList.append( sum(aList)%256 ) # calculate checksum
    logger.info("Serial.write(): Writing to following bytes {}".format(list(aList)))
    ser.write(bytearray(aList))


def on_connect(client, userdata, flags, rc):
    if rc==0:
        logger.info("MQTT connected OK. Return code "+str(rc) )
        client.subscribe("homie/"+mqtt_client_name+"/+/set")
        logger.debug("MQTT: Subscribed to all topics")
    else:
        logger.error("Bad connection. Return code="+str(rc))

def on_disconnect(client, userdata, rc):
    if rc != 0:
        logger.warning("Unexpected MQTT disconnection. Will auto-reconnect")

def on_message(client, userdata, message):
    t = datetime.now()
    t = time.mktime(t.timetuple()) + t.microsecond / 1E6
    m = message.payload.decode("utf-8")

    j = json.loads(m)
    logger.info("Topic: "+message.topic+" JSON:"+str(j))
    msplit = re.split("/", message.topic)
    if len(msplit) == 4 and msplit[3].lower() == "set":
        if (msplit[2]=="type"):
          SendMsgToController(2,"Gemuese")
        if (msplit[2]=="refresh"):
          SendMsgToController(3)
        if (msplit[2]=="reset"):
          SendMsgToController(0)
        if (msplit[2]=="nr"):
          SendMsgToController(4)

mqtt_client_name = "test"

client = paho.Client(mqtt_client_name)
client.on_message = on_message
client.on_connect = on_connect
client.on_disconnect = on_disconnect
client.enable_logger(logger) # info: https://www.eclipse.org/paho/clients/python/docs/#callbacks
logger.info("Conncting to broker "+args.mqtt_broker_host)
client.connect(args.mqtt_broker_host)
client.loop_start()
logger.info("MQTT loop started.")

def ESPCRC(fDaten):
    u8CRC = 0
    for x in fDaten:
        u8CRC += x
    return u8CRC % 256

def bytearray_2_str(fba) -> str:
    return '0x'+''.join("{:02x}".format(x) for x in fba)

def resetArduino():
  ser = serial.Serial(args.serial_device_name, 1200, timeout=0)
  ser.close()
  time.sleep(1)

#Connect normally
ser = serial.Serial(args.serial_device_name, 115200, timeout=0)

WatchDogCounter = args.watchdog_timeout
charSet = bytearray()
scaleProperties = {'ProductName':None, 'SerialNumber':None, "FirmwareVersion":None}

FSMState = 0 #0=start
LastFSMStateChange = time.time() #change to time.time(), when FSMState updates

while (WatchDogCounter > 0):
    newFSMState=FSMState
    if (FSMState == 0): # Start: Ask for serial number
        newFSMState=1
        SendMsgToController(1) #Ask for serial number
    elif (FSMState == 1): #Wait for serial number return
        #Receiving the value will set to FSMState==2
        pass
    elif (FSMState == 2): # Start: Ask for Firmware number
        #Load configuration:
        ConfigFile = "/home/pi/zeitlos/config/scaleCalibrations/{}.yml".format(scaleProperties["SerialNumber"])
        if not os.path.exists(ConfigFile):
            logger.warning("config file {} does not exist. Using default.".format(ConfigFile) )
        else:
            logger.info("Reading config file {}".format(ConfigFile) )
            with open(ConfigFile, 'r') as ymlfile:
                cfg = yaml.full_load(ymlfile) # see https://github.com/yaml/pyyaml/wiki/PyYAML-yaml.load(input)-Deprecation
                print(cfg)

        newFSMState=3
        SendMsgToController(2) #Ask for Firmware Version
    elif (FSMState == 3): #Wait for Firmware Version return
        #Receiving the value will set to FSMState==10
        pass
    elif (FSMState == 10): #Transfer: ProductName
        SendMsgToController(102, "Spinat") #ProductName
        newFSMState=11
    elif (FSMState == 11): #Transfer:  ProductDescription
        SendMsgToController(103, "Aus dem eigenen Anbau.") #ProductDescription
        newFSMState=100 #Set up complete
    elif (FSMState==100):
        SendMsgToController(100) #FullDisplay Update
        logger.info("Initialisation complete.")
        newFSMState=101
    elif (FSMState==101):
        newFSMState=101
        pass
    else:
        newFSMState=0
        logger.error("Invalid FSM State. Will reset.")

    while ser.inWaiting() > 0:
        charSet += ser.read()
    while len(charSet) > 0 and charSet[0] != 0x5a:
        logger.warning("Serial.read(): Deleted (no 0x5a start): (int) "+str(charSet.pop(0)) )

    # [Start Sequence] [Command Byte, 2bytes] [Number of data bytes, 2bytes] [Data bytes] [Checksum byte]
    if len(charSet) >= 7: #Paket with length of 0 data bytes
        pCmd, pDataLength = charSet[2]*256+charSet[3], charSet[4]*256+charSet[5]

        if len(charSet) >= pDataLength+7: #Paket fully received
            pFullDataCRC = charSet[6+pDataLength]
            pData = charSet[6:6+pDataLength]
            if ESPCRC(charSet[0:6+pDataLength]) == pFullDataCRC:  # Data CRC ok
                WatchDogCounter = args.watchdog_timeout
                t = datetime.now()
                t = time.mktime(t.timetuple()) + t.microsecond / 1E6

                logger.debug("Serial.read(): pCmd: "+str(pCmd)+" Data: "+bytearray_2_str(pData))
                # list() converts bytearray into array of int
                t = datetime.now()
                t = time.mktime(t.timetuple()) + t.microsecond / 1E6
                client.publish("homie/"+mqtt_client_name+"/messages", json.dumps(
                    {"pCmd": pCmd, "data": list(pData), "time": t},
                    sort_keys=True), qos = 1)
                if (pCmd==1) and (FSMState==1): # Serial number received
                    scaleProperties['SerialNumber'] = bytearray_2_str(pData)
                    logger.info("scaleProperties: {}".format(scaleProperties))
                    newFSMState=2
                if (pCmd==2) and (FSMState==3): #Firmware Version received
                    scaleProperties['FirmwareVersion'] = bytearray_2_str(pData)
                    logger.info("FirmwareVersion: {}".format(scaleProperties))
                    newFSMState=10
            else:
                logger.warning("Serial.read(): CRC NOT ok. Read ({}), calculated ({}), Cmd ({}) pDataLength ({})".format(
                    pFullDataCRC, ESPCRC(charSet[0:6+pDataLength]), pCmd, pDataLength) )
                print(list(pData))

            # Delete the processed data and propare for next paket to receive
            charSet=charSet[pDataLength+7:]
    
    if (time.time() - LastFSMStateChange > 5) and (FSMState != 101): # 101 is the ground state
        newFSMState = 0
        logger.error("No response from micro controller for more than 5 second. Last FSMState: {}. Reset FSM state.".format(FSMState))

    if (newFSMState != FSMState):
        FSMState = newFSMState
        LastFSMStateChange=time.time()


    time.sleep(.01)
    WatchDogCounter -= 1

ser.close()

client.disconnect()
client.loop_stop()
logger.info("Program stopped.")

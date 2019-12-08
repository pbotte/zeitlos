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
import struct #to unpack 4 bytes to int
import numpy as np # for variance

logging.basicConfig(level=logging.WARNING,
                    format='%(asctime)-6s %(levelname)-8s  %(message)s')
logger = logging.getLogger("scale controller")

parser = argparse.ArgumentParser(
    description='MQTT scale controller.')
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

class measurementValue:
    def __init__(self, maxLength=1):
        self.data = []
        self.maxLength = maxLength
    def add(self, data):
        self.data.append(data)
        if len(self.data) > self.maxLength:
            del(self.data[0])
    def avg(self):
        return sum(self.data)/len(self.data)

scaleReadings = [measurementValue(10) for i in range(4)]


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
    logger.debug("Serial.write(): Writing the following bytes {}".format(list(aList)))
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
          #SendMsgToController(100) # FullUpdate
          SendMsgToController(101) #Partial Update
        if (msplit[2]=="stop"):
          SendMsgToController(10000) #Please Log In Msg
        if (msplit[2]=="reset"):
          SendMsgToController(0)
        if (msplit[2]=="nr"):
          SendMsgToController(4)

mqtt_client_name = "unconfiguredScale"

client = paho.Client() #mqtt_client_name)
client.on_message = on_message
client.on_connect = on_connect
client.on_disconnect = on_disconnect
client.enable_logger(logger) # info: https://www.eclipse.org/paho/clients/python/docs/#callbacks
logger.info("Connecting to broker "+args.mqtt_broker_host)

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
scaleProperties = {'system':{'SerialNumber':None, "FirmwareVersion":None}, 
                   'details':{
                       'ProductName': 'Produktbeschreibung', 
                       'ProductDescription': 'Keine Beschreibung.',
                       'Pricing':{ 'Type': 0, 'GrammsPerUnit':100, 'PricePerUnit': 1.0  },
                       'Calibration': {'Offset': [0, 0, 0, 0],
                        'Slope':[1, 1, 1, 1],
                        'GlobalOffset': 0,
                        'DisplayRounding': 1
                       }
                   } }

FSMState = 0 #0=start
LastFSMStateChange = time.time() #change to time.time(), when FSMState updates

numberMessagesRecv = 0
timeLastPriceUpdate = time.time()
lastMassDisplayed = None

while (WatchDogCounter > 0):
    newFSMState=FSMState
    if (FSMState == 0): # Start: Ask for serial number
        newFSMState=1
        SendMsgToController(1) #Ask for serial number
    elif (FSMState == 1): #Wait for serial number return
        #Receiving the value will set to FSMState==2
        pass
    elif (FSMState == 2): # Start: Ask for Firmware number
        #start with MQTT connection and set last will
        mqtt_client_name = "scale{}".format(scaleProperties['system']['SerialNumber'])
        logger.info("mqtt_client_name: {}".format(mqtt_client_name))
        client.will_set("homie/"+mqtt_client_name+"/state", 'offline', qos=1, retain=True)
        client.connect(args.mqtt_broker_host)
        client.loop_start()
        logger.info("MQTT loop started.")
        client.publish("homie/"+mqtt_client_name+"/state", 'online', qos=1, retain=True)

        #Load configuration:
        ConfigFile = "/home/pi/zeitlos/config/scaleCalibrations/{}.yml".format(scaleProperties['system']["SerialNumber"])
        if not os.path.exists(ConfigFile):
            logger.warning("config file {} does not exist. Using default.".format(ConfigFile) )
        else:
            logger.info("Reading config file {}".format(ConfigFile) )
            with open(ConfigFile, 'r') as ymlfile:
                scaleProperties['details'] = yaml.full_load(ymlfile) # see https://github.com/yaml/pyyaml/wiki/PyYAML-yaml.load(input)-Deprecation
                logger.info("Data read: {}".format(scaleProperties['details']))

        newFSMState=3
        SendMsgToController(2) #Ask for Firmware Version
    elif (FSMState == 3): #Wait for Firmware Version return
        #Receiving the value will set to FSMState==10
        pass
    elif (FSMState == 10): #Transfer: ProductName
        #First display the status
        client.publish("homie/"+mqtt_client_name+"/status", json.dumps(scaleProperties,
            sort_keys=True), qos = 1, retain=True)

        SendMsgToController(102, scaleProperties['details']['ProductName']) #ProductName
        newFSMState=11
    elif (FSMState == 11): #Transfer:  ProductDescription
        SendMsgToController(103, scaleProperties['details']['ProductDescription']) #ProductDescription
        newFSMState=12
    elif (FSMState == 12): #Transfer:  PricePerUnit
        tempStr = "{:d}g".format(scaleProperties['details']['Pricing']['GrammsPerUnit'])
        if (scaleProperties['details']['Pricing']['Type'] == 1):
            tempStr = "Stk"
        elif (scaleProperties['details']['Pricing']['GrammsPerUnit'] == 1):
            tempStr = "g"
        elif (scaleProperties['details']['Pricing']['GrammsPerUnit'] == 1000):
            tempStr = "kg"
        SendMsgToController(106, "{:.2f}EUR/{}".format(scaleProperties['details']['Pricing']['PricePerUnit'], tempStr)) #PricePerUnit
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
        logger.error("Invalid FSM State. Reset FSM state to 0.")

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
                numberMessagesRecv += 1
                logger.debug("Serial.read(): pCmd: "+str(pCmd)+" Data: "+bytearray_2_str(pData))
                # list() converts bytearray into array of int
                #client.publish("homie/"+mqtt_client_name+"/messages", json.dumps(
                #    {"pCmd": pCmd, "data": list(pData), "time": time.time()},
                #    sort_keys=True), qos = 1)
                if (pCmd==1) and (FSMState==1): # Serial number received
                    scaleProperties['system']['SerialNumber'] = bytearray_2_str(pData)
                    logger.info("scaleProperties: {}".format(scaleProperties['system']['SerialNumber']))
                    newFSMState=2
                elif (pCmd==2) and (FSMState==3): #Firmware Version received
                    scaleProperties['system']['FirmwareVersion'] = bytearray_2_str(pData)
                    logger.info("FirmwareVersion: {}".format(scaleProperties['system']['FirmwareVersion']))
                    newFSMState=10
                elif (pCmd==200):
                    logger.error("Scale reported scale read error.")
                elif (pCmd==1000):
                    logger.error("eink paper init failed.")
                elif (pCmd==201):
                    for i in range(4): #for all 4 gauges
                        data = pData[0+4*i:4+4*i]
                        #print(list('%02x' % b for b in data)) # Show hex values of data.
                        # Convert to 4 byte signed integer data interpreting data as being in 
                        # little-endian byte order.
                        value=struct.unpack("<i", bytearray(data))[0]
                        #print(hex(value))
                        valueCalibrated = (value-scaleProperties['details']['Calibration']['Offset'][i])* \
                            scaleProperties['details']['Calibration']['Slope'][i]
                        scaleReadings[i].add(valueCalibrated)
                    scaleSum = sum([i.avg() for i in scaleReadings])-scaleProperties['details']['Calibration']['GlobalOffset']
                    # Hide some accuracy which isnt in the hardware:
                    scaleSum = round(scaleSum/scaleProperties['details']['Calibration']['DisplayRounding'])*scaleProperties['details']['Calibration']['DisplayRounding']

                    scaleVar = np.std( [sum([i.data[j] for i in scaleReadings]) for j in range(len(scaleReadings[0].data)) ] ) #std deriv. of last 10 sums

                    #Perform Partial Display Update
                    if (scaleVar < 10) and (time.time()-timeLastPriceUpdate>=2):
                        if ( (lastMassDisplayed is None) or (abs(round(scaleSum-lastMassDisplayed)) > 0) ):
                            lastMassDisplayed = scaleSum
                            tempMass = 0 #can be gramms or pieces
                            tempMassStr = "?"
                            tempPrice = 0
                            tempPriceStr = "?"
                            if (scaleProperties['details']['Pricing']['Type'] == 0): #price per gramm
                                tempMass = scaleSum
                                tempMassStr = "{:7.0f}g".format(scaleSum)
                                tempPrice = round(scaleSum)/scaleProperties['details']['Pricing']['GrammsPerUnit']*scaleProperties['details']['Pricing']['PricePerUnit']
                                tempPriceStr = "{:7.2f}".format(tempPrice)
                            elif (scaleProperties['details']['Pricing']['Type'] == 1): #price per piece
                                tempMass = round(scaleSum / scaleProperties['details']['Pricing']['GrammsPerUnit'])
                                tempMassStr = "{:5d}Stk".format(tempMass)
                                tempPrice = tempMass*scaleProperties['details']['Pricing']['PricePerUnit']
                                tempPriceStr = "{:7.2f}".format(tempPrice)
                            SendMsgToController(104, tempMassStr)
                            SendMsgToController(105, "{}E".format(tempPriceStr))
                            timeLastPriceUpdate = time.time()
                            SendMsgToController(101) #Partial Update

                            client.publish("homie/"+mqtt_client_name+"/withdrawal", json.dumps({'pricingType': scaleProperties['details']['Pricing']['Type'], 
                                'mass': tempMass, 'price': tempPrice},
                                        sort_keys=True), qos = 1, retain=True)

                    #logger.debug("Gauge values: {}".format([i.data[0] for i in scaleReadings]))
                    logger.debug("Gauge Avg: {} ({:.3f} +- {:.3f}) individual: {}".format(scaleSum, sum([i.avg() for i in scaleReadings]), scaleVar, [round(i.avg(),3) for i in scaleReadings]))
                else:
                    logger.warning("Serial.read(): Cmd ({}) pDataLength ({}) Data {}".format(
                        pCmd, pDataLength, list(pData)))
            else:
                logger.warning("Serial.read(): CRC NOT ok. Read ({}), calculated ({}), Cmd ({}) pDataLength ({})".format(
                    pFullDataCRC, ESPCRC(charSet[0:6+pDataLength]), pCmd, pDataLength) )
                logger.warning("Full pData: {}".format(list(pData)))

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

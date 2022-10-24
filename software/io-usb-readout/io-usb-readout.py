#!/usr/bin/env python3

import json
import time
import serial
import paho.mqtt.client as paho
import argparse
import traceback
import logging


logging.basicConfig(level=logging.WARNING,
                    format='%(asctime)-6s %(levelname)-8s  %(message)s')
logger = logging.getLogger("raspberry pico io readout")

parser = argparse.ArgumentParser(
    description='raspi pico io readout')
parser.add_argument("-v", "--verbosity",
                    help="increase output verbosity", default=0, action="count")
parser.add_argument("-b", "--mqtt-broker-host",
                    help="MQTT broker hostname. default=localhost", default="localhost")
parser.add_argument("-p", "--mqtt-broker-port", default=1883, type=int)
parser.add_argument("-t", "--watchdog-timeout",
                    help="timeout in seconds for the watchdog. default=10 sec", default=200, type=int)
parser.add_argument("mqtt_client_name",
                    help="MQTT client name. Needs to be unique in the MQTT namespace, eg shop-track.", type=str)
parser.add_argument("serial_device_name",
                    help="Serial port used, eg /dev/ttyACM0", type=str)
args = parser.parse_args()
logger.setLevel(logging.WARNING-(args.verbosity *
                                 10 if args.verbosity <= 2 else 20))

logger.info("MQTT client name: "+args.mqtt_client_name)
logger.info("Watchdog timeout (seconds): "+str(args.watchdog_timeout))
logger.info('Use the following Serial-Device: '+str(args.serial_device_name))


def on_connect(client, userdata, flags, rc):
  if rc == 0:
    logger.info("MQTT connected OK. Return code"+str(rc))
  else:
    logger.error("Bad connection. Return code="+str(rc))


def on_disconnect(client, userdata, rc):
  if rc != 0:
    logger.warning("Unexpected MQTT disconnection. Will auto-reconnect")


client= paho.Client(args.mqtt_client_name)
client.on_connect = on_connect
client.on_disconnect = on_disconnect
client.enable_logger(logger)
logger.info("Conncting to broker "+args.mqtt_broker_host)
client.will_set(topic='homie/'+args.mqtt_client_name+'/$state',payload='disconnect',qos=1,retain=True)
client.connect(args.mqtt_broker_host, keepalive=60, port=args.mqtt_broker_port)
client.publish(topic='homie/'+args.mqtt_client_name+'/$state',payload='ready',qos=1,retain=True)
client.loop_start()
logger.info("MQTT loop started.")

ser = serial.Serial(args.serial_device_name, 115200, timeout=1.0)

lastdata = {}

WatchDogCounter = args.watchdog_timeout
while (WatchDogCounter > 0):
  WatchDogCounter -= 1

  if ser.inWaiting() > 0:
    line = ser.readline()   # readline = read a '\n' terminated line
    if (len(line) > 0):
      try:
        data = json.loads(line)
        logger.debug("Actual Reading: {}".format(data))
        for k, v in data.items():
          if k not in lastdata:
            lastdata[k] = None
          if lastdata[k] != data[k]:
            client.publish("homie/"+args.mqtt_client_name+"/"+k, v, qos = 1, retain=True)
            lastdata[k] = v

        WatchDogCounter = args.watchdog_timeout

      except Exception as e:
        print("serial read line: "+line )
        print("exception occoured: %s" % str(e))

  time.sleep(.01)

#Programm beenden
ser.close()

client.loop_stop()
client.disconnect()
logger.info("Programm stopped.")

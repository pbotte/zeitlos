#!/usr/bin/env python3

import json
import time
import serial
import paho.mqtt.client as paho
import argparse
import traceback
import logging
import collections, statistics


logging.basicConfig(level=logging.WARNING,
                    format='%(asctime)-6s %(levelname)-8s  %(message)s')
logger = logging.getLogger("single VL53L1 readout via raspberry pico")

parser = argparse.ArgumentParser(
    description='MQTT VL53L1 readout')
parser.add_argument("-v", "--verbosity",
                    help="increase output verbosity", default=0, action="count")
parser.add_argument("-b", "--mqtt-broker-host",
                    help="MQTT broker hostname. default=localhost", default="localhost")
parser.add_argument("-p", "--mqtt-broker-port", default=1883, type=int)
parser.add_argument("-t", "--watchdog-timeout",
                    help="timeout in seconds for the watchdog. default=10 sec", default=20, type=int)
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

def send_data(act_v=None):
  global last_dist_during_transfer
  last_dist_during_transfer = act_distance_avg
  logger.info("Summarizing Reading: {}+-{}".format(act_distance_avg, act_distance_stdev))
#  client.publish("homie/shop-track/"+sn+"/data", json.dumps(
 #                   {"v": act_distance_avg, 'Dv': act_distance_stdev, 'reading_stack':list(readings_stack), "time": time.time()},
  #                   sort_keys=True), qos = 1)
  if act_v:
    client.publish("homie/shop-track/"+sn+"/distance", act_v, qos=1, retain=True)
  else:
    client.publish("homie/shop-track/"+sn+"/distance", act_distance_avg, qos=1, retain=True)

#readout data stack
readings_stack = collections.deque(maxlen=5)
lastTransfer = 0
lastTransfer_due_change = 0
last_dist_during_transfer = 0
act_distance_avg = 0
act_distance_stdev = 0
sn = 0 # serialnumber from device

WatchDogCounter = args.watchdog_timeout
while (WatchDogCounter > 0):
  WatchDogCounter -= 1

  if ser.inWaiting() > 0:
    line = ser.readline()   # readline = read a '\n' terminated line
    if (len(line) > 0):
      try:
        data = json.loads(line)
        readings_stack.append(data['v'])
        sn = data['sn'] #get serial number from device
        logger.debug("Actual Reading: {}".format(data))
#        client.publish('homie/'+args.mqtt_client_name+'/actreading', json.dumps(data), qos=1, retain=True)

        if (len(readings_stack)>2): #some reading has to be in the stack
          act_distance_avg = statistics.mean(list(readings_stack))
          act_distance_stdev = statistics.stdev(list(readings_stack))

#          if abs(last_dist_during_transfer-data['v']) > 50: # of it changes by more than a certain threshold
          if abs(last_dist_during_transfer-act_distance_avg) > 200: #distance in mm
            if (time.time() - lastTransfer_due_change) >= 0.9:
              lastTransfer_due_change = time.time()
#              send_data(data['v'])
              send_data()
        WatchDogCounter = args.watchdog_timeout

      except Exception as e:
        print( "serial read line: "+line )
        print( "exception occoured: %s" % str(e))

  #submit data only every 10 second(s)
  if (time.time() - lastTransfer) >= 10:
    if (len(readings_stack)>2):
      lastTransfer = time.time()
      send_data()

  time.sleep(.01)

#Programm beenden
ser.close()

client.loop_stop()
client.disconnect()
logger.info("Programm stopped.")

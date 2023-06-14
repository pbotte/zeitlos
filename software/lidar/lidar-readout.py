#!/usr/bin/python3

import paho.mqtt.client as paho
import json
import time
import logging
import argparse
import traceback
import math
import re
import signal #to catch interrupts and exit gracefully
import queue
import sdnotify # to call systemd-notify


logging.basicConfig(level=logging.WARNING,
                    format='%(asctime)-6s %(levelname)-8s  %(message)s')
logger = logging.getLogger("Lidar readout")

parser = argparse.ArgumentParser(description='Lidar readout')
parser.add_argument("instance", help="Lidar consecutive instance number")
parser.add_argument("-v", "--verbosity",
                    help="increase output verbosity", default=0, action="count")
parser.add_argument("-b", "--mqtt-broker-host",
                    help="MQTT broker hostname. default=localhost", default="localhost")
parser.add_argument("-t", "--timeout",
                    help="timeout in seconds. default=1h", default=100*60*60, type=int)
args = parser.parse_args()
logger.setLevel(logging.WARNING-(args.verbosity * 10 if args.verbosity <= 2 else 20))

mqtt_client_name = "lidar_readout_"+args.instance


def on_connect(client, userdata, flags, rc):
    if rc == 0:
        logger.info("MQTT connected OK. Return code "+str(rc))
        client.subscribe("homie/cardreader/#")

        logger.debug("MQTT: Subscribed to all topics")
    else:
        logger.error("Bad connection. Return code="+str(rc))


def on_disconnect(client, userdata, rc):
    if rc != 0:
        logger.warning("Unexpected MQTT disconnection. Will auto-reconnect")


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

#client.publish("homie/"+mqtt_client_name+"/shop_overview/products_scales", json.dumps(products_scales), qos=1, retain=True)

loop_var = True
def signal_handler(sig, frame):
  global loop_var
  logger.info('You pressed Ctrl+C! Preparing for graceful exit.')
  loop_var = False
signal.signal(signal.SIGINT, signal_handler)

# Inform systemd that we've finished our startup sequence...
n = sdnotify.SystemdNotifier()
n.notify("READY=1")
count = 1 #some watchdog counter


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
        if len(msplit) == 3 and msplit[2].lower() == "close_shop":
           pass
        #    set_shop_status(10)


        # QR Code scanned.
        #emulate with: mosquitto_pub -t 'homie/shop_qr-scanner/qrcode_detected' -m '1666703949 43 B8FAF7'
        # 3 numbers, separated with spaces: time.time(), User ID, md5-hash
        if message.topic.lower() == "homie/shop_qr-scanner/qrcode_detected":
            logger.info("qrcode read: {}".format( m ))


      except Exception as err:
        traceback.print_tb(err.__traceback__)
    ############################################################################


    #inform systemd via sdnotify we are still alive
    n.notify("STATUS=Count is {}".format(count))
    n.notify("WATCHDOG=1")
    count += 1



    time.sleep(1-math.modf(time.time())[0])  # make the loop run every second



client.disconnect()
client.loop_stop()
logger.info("Program stopped.")

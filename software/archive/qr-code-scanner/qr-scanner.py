#!/usr/bin/python3

# reinstall:
# sudo apt install -y python3-opencv python3-pip python3-zbar python3-picamera
# pip3 install pyzbar imutils paho-mqtt

import time

time_last_debug_picture_saved = 0
time_last_debug_picture_saved_fixed_name = 0
time_script_started = time.time() #to terminate script after some time to prevent possible hang up of hard or software


import cv2
from pyzbar import pyzbar
import imutils
from imutils.video import VideoStream
import paho.mqtt.client as paho
import hashlib
import json
import argparse
import requests #pip3 install requests
import logging
from pathlib import Path
import numpy as np
import sdnotify # to call systemd-notify


logging.basicConfig(format="%(asctime)-15s %(levelname)-8s  %(message)s")
logger = logging.getLogger("QR-Code Scanner")

parser = argparse.ArgumentParser(description='QR Code Scanner')
parser.add_argument("-v", "--verbosity", help="increase output verbosity", default=0, action="count")
parser.add_argument("-b", "--mqtt-broker-host", help="MQTT broker hostname", default="localhost")
parser.add_argument("--save-debug-pictures", help="store every 10 sec a picture under /dev/shm/ ", action='store_true')
parser.add_argument("--save-last-debug-picture", help="store every 5 sec a picture under /dev/shm/last.png - This helps adjusting the focus.", action='store_true')
args = parser.parse_args()
logger.setLevel(logging.WARNING-(args.verbosity*10 if args.verbosity <=2 else 20) )

logger.info("Verbosity min. at info level.")

mqtt_client_name = "shop_qr-scanner"

def on_connect(client, userdata, flags, rc):
    if rc == 0:
        logger.info("MQTT connected OK. Return code "+str(rc))
        client.subscribe("homie/"+mqtt_client_name+"/requestShopStatus")

        logger.debug("MQTT: Subscribed to all topics")
    else:
        logger.error("Bad connection. Return code="+str(rc))


def on_disconnect(client, userdata, rc):
    if rc != 0:
        logger.warning("Unexpected MQTT disconnection. Will auto-reconnect")

def on_message(client, userdata, message):
    m = message.payload.decode("utf-8")
    logger.info("Topic: "+message.topic+" Message: "+m)


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


# initialize video stream
video_width = 1920
video_height = 1440

vs = VideoStream(usePiCamera = True, resolution=(video_width, video_height)  ).start()
logger.debug("wait for camera to adapt")
time.sleep(1)
last_frame = vs.read()

logger.info("Script completed initialisation.")
continue_loop = True

# Inform systemd that we've finished our startup sequence...
n = sdnotify.SystemdNotifier()
n.notify("READY=1")
count = 1 #some watchdog counter

while continue_loop:
  time.sleep(0.5) #spend soem time to make the CPU not heating up too much

  # read from camera
  frame = vs.read()
  logger.debug("picture taken")

  #check, whether camera still alive - START
  loop_diff_test = cv2.subtract(frame, last_frame)
  result = not np.any(loop_diff_test)
  if result is True:
    logger.error("picture comparision shows: picture is NOT different comparend to last loop. This means, our camera connection is broken. Terminating.")
    continue_loop = False
  else:
    logger.debug("picture comparision shows: picture is different comparend to last loop. Good, our camera is still alive.")
    last_frame = frame.copy()
  # check, wether camera still alive - STOP

  frame_small = imutils.resize(frame, width=540)
  frame_gray = cv2.cvtColor(frame_small, cv2.COLOR_BGR2GRAY)

  if args.save_debug_pictures and (time.time() - time_last_debug_picture_saved >= 10):
    cv2.imwrite("/dev/shm/time_{}.png".format(round(time.time())), frame_small) #for debug reasons
    time_last_debug_picture_saved = time.time()
    logger.info("debug picture saved")
  if args.save_last_debug_picture and (time.time() - time_last_debug_picture_saved_fixed_name >= 5):
    cv2.imwrite("/dev/shm/last.png", frame_small) #for debug reasons
    time_last_debug_picture_saved_fixed_name = time.time()
    logger.info("debug picture with fixed name saved")

  logger.debug("start searching for qr-codes")
  barcodes = pyzbar.decode(frame_gray)

  for barcode in barcodes: #for each barcode found
    client.publish("homie/"+mqtt_client_name+"/qrcode_detected", barcode.data.decode("utf-8"), qos=1, retain=False)
    logger.info("{}".format(barcode.data.decode("utf-8")) )

  #inform systemd via sdnotify we are still alive
  n.notify("STATUS=Count is {}".format(count))
  n.notify("WATCHDOG=1")
  count += 1

#  if count > 100: time.sleep(100)

cv2.destroyAllWindows()
vs.stop()

client.disconnect()
client.loop_stop()

logger.info("Script terminated. Total runtime: {:.2f} min".format( (time.time()-time_script_started)/60 ) )

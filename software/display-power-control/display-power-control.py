#!/usr/bin/python3

import paho.mqtt.client as paho
import time
import logging
import argparse
import queue, traceback
import math
import re
import os
import socket
import signal

logging.basicConfig(level=logging.WARNING, format='%(asctime)-6s %(levelname)-8s  %(message)s')
logger = logging.getLogger("Display power control")

parser = argparse.ArgumentParser(description='Display power control for Wayland')
parser.add_argument("-v", "--verbosity", help="increase output verbosity", default=0, action="count")
parser.add_argument("-b", "--mqtt-broker-host", help="MQTT broker hostname. default=localhost", default="localhost")
args = parser.parse_args()
logger.setLevel(logging.WARNING-(args.verbosity * 10 if args.verbosity <= 2 else 20))

debug = True if args.verbosity>1 else False

mqtt_client_name = f"display-power-control-{socket.gethostname()}"

def on_connect(client, userdata, flags, rc):
    if rc == 0:
        logger.info("MQTT connected OK. Return code "+str(rc))
        client.subscribe("homie/"+mqtt_client_name+"/power/set")
        logger.debug("MQTT: Subscribed to all topics")
    else:
        logger.error("Bad connection. Return code="+str(rc))

def on_disconnect(client, userdata, rc):
    if rc != 0:
        logger.warning("Unexpected MQTT disconnection. Will auto-reconnect")

last_power_status = None

#get current HDMI display status
def check_power_status():
  global last_power_status
  stream = os.popen('XDG_RUNTIME_DIR=/run/user/1000 WAYLAND_DISPLAY="wayland-1" wlr-randr')
  output = stream.read().strip()
  logger.debug(f"return value of wlr-randr: {output}")
  act_state = 1 if 'current' in output else 0
  if last_power_status != act_state:
    logger.info(f"detected new power state: {act_state}")
    last_power_status = act_state
    client.publish("homie/"+mqtt_client_name+"/power", act_state, qos=1, retain=True)

mqtt_queue=queue.Queue()
def on_message(client, userdata, message):
  global mqtt_queue
  try:
    mqtt_queue.put(message)
    m = message.payload.decode("utf-8")
    logger.debug("MQTT message received. Topic: "+message.topic+" Payload: "+m)
  except Exception as err:
    traceback.print_tb(err.__traceback__)


##############################################################################
main_loop_var = True
def signal_handler(sig, frame):
    global main_loop_var
    logger.info(f"Program terminating. (this takes 1 second)")

    main_loop_var = False
#    sys.exit(0)

signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)
##############################################################################


client = paho.Client(paho.CallbackAPIVersion.VERSION1, mqtt_client_name)
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
client.publish("homie/"+mqtt_client_name+"/state", '1', qos=1, retain=True)


last_check = 0
last_change = time.time()
while main_loop_var: 
  while not mqtt_queue.empty():
    message = mqtt_queue.get()
    if message is None:
      continue
    logger.debug(f"Process queued MQTT message now: {str(message.payload.decode('utf-8'))}")

    try:
      m = message.payload.decode("utf-8")
    except Exception as err:
      traceback.print_tb(err.__traceback__)
    logger.debug("Topic: "+message.topic+" Message: "+m)

    msplit = re.split("/", message.topic)

    if message.topic.lower() == "homie/"+mqtt_client_name+"/power/set":
        cmd_str = '--on' if m=='1' else '--off'                  #nomal mode
        cmd_str = '--on --transform 270' if m=='1' else '--off'  #display rotated vertically


        stream = os.popen('XDG_RUNTIME_DIR=/run/user/1000 WAYLAND_DISPLAY="wayland-1" wlr-randr --output HDMI-A-1 '+cmd_str)
        output = stream.read().strip()
        logger.info(f"power_status of HDMI-1 changed with parameter: {cmd_str}")

        if m=='1':
          #make chromium fullscreen again
          stream = os.popen('sleep 2 && XDG_RUNTIME_DIR=/run/user/1000 WAYLAND_DISPLAY="wayland-1" wtype -k F11')
          output = stream.read().strip()
          logger.info(f"send key stroke F11 to make chromium fullscreen again")

        last_change = time.time()

  # perform regular status checks every 10 seconds OR
  # with 1Hz if last change is less thant 10 seconds ago
  if (time.time()-last_check > 10) or (time.time()-last_change < 10): 
    if time.time()-last_change > 1: #last change needs to be min 1 seconds ago! To avoid flickering
      logger.debug("start check power status")
      check_power_status()
      last_check = time.time()

  time.sleep(0.1) #save some power
#  time.sleep(1-math.modf(time.time())[0])  # make the loop run every 1 second



# Terminating everthing
logger.info(f"Terminating. Cleaning up.")

# send state=0
client.publish(f"homie/{mqtt_client_name}/state", '0', qos=1, retain=True)

time.sleep(1) #to allow the published message to be delivered.

client.loop_stop()
client.disconnect()

logger.info("Program stopped.")

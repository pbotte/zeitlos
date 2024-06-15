#!/usr/bin/python3

import paho.mqtt.client as paho
import time
import logging
import argparse
import queue, traceback
import re
import os
import socket
from gtts import gTTS

logging.basicConfig(level=logging.WARNING, format='%(asctime)-6s %(levelname)-8s  %(message)s')
logger = logging.getLogger("TTS")

parser = argparse.ArgumentParser(description='Text to speach')
parser.add_argument("-v", "--verbosity", help="increase output verbosity", default=0, action="count")
parser.add_argument("-b", "--mqtt-broker-host", help="MQTT broker hostname. default=localhost", default="localhost")
args = parser.parse_args()
logger.setLevel(logging.WARNING-(args.verbosity * 10 if args.verbosity <= 2 else 20))

debug = True if args.verbosity>1 else False

mqtt_client_name = f"tts-{socket.gethostname()}"

def on_connect(client, userdata, flags, rc):
    if rc == 0:
        logger.info("MQTT connected OK. Return code "+str(rc))
        client.subscribe("homie/"+mqtt_client_name+"/say")
        logger.debug("MQTT: Subscribed to all topics")

        client.publish("homie/"+mqtt_client_name+"/state", '1', qos=1, retain=True)

    else:
        logger.error("Bad connection. Return code="+str(rc))

def on_disconnect(client, userdata, rc):
    if rc != 0:
        logger.warning("Unexpected MQTT disconnection. Will auto-reconnect")

def say_text(text):
  if text:
    logger.info(f"say: {text}")
    client.publish("homie/"+mqtt_client_name+"/speaking", '1', qos=1, retain=True)
    tts = gTTS(text, lang='de')
    tts.save('/run/shm/output.mp3')
    logger.info(f"Execute the following: /usr/bin/mpg123 -o alsa /dev/shm/output.mp3")
    os.system('/usr/bin/mpg123 -o alsa /dev/shm/output.mp3')
    client.publish("homie/"+mqtt_client_name+"/speaking", '0', qos=1, retain=True)


mqtt_queue=queue.Queue()
def on_message(client, userdata, message):
  global mqtt_queue
  try:
    mqtt_queue.put(message)
    m = message.payload.decode("utf-8")
    logger.debug("MQTT message received. Topic: "+message.topic+" Payload: "+m)
  except Exception as err:
    traceback.print_tb(err.__traceback__)


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

while True: 
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

    if message.topic.lower() == "homie/"+mqtt_client_name+"/say":
      say_text(m)
      


  time.sleep(0.1) #save some power
#  time.sleep(1-math.modf(time.time())[0])  # make the loop run every 1 second

client.disconnect()
client.loop_stop()
logger.info("Program stopped.")

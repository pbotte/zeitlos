#!/usr/bin/python3

import paho.mqtt.client as paho
import json
import time
import logging
import argparse
import traceback
import re
import signal #to catch interrupts and exit gracefully
import queue
import sdnotify # to call systemd-notify
import subprocess


logging.basicConfig(level=logging.WARNING,
                    format='%(asctime)-6s %(levelname)-8s  %(message)s')
logger = logging.getLogger("Lidar readout")

parser = argparse.ArgumentParser(description='Lidar readout')
parser.add_argument("instance", help="Lidar consecutive instance number")
parser.add_argument("-v", "--verbosity",
                    help="increase output verbosity", default=0, action="count")
parser.add_argument("-b", "--mqtt-broker-host",
                    help="MQTT broker hostname. default=localhost", default="localhost")
args = parser.parse_args()
logger.setLevel(logging.WARNING-(args.verbosity * 10 if args.verbosity <= 2 else 20))

mqtt_client_name = "lidar_readout_"+args.instance


def on_connect(client, userdata, flags, rc):
    if rc == 0:
        logger.info("MQTT connected OK. Return code "+str(rc))
        #client.subscribe("homie/cardreader/#")

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
# press twice CTRL+C to all kill readout
def signal_handler(sig, frame):
  global loop_var
  logger.info('You pressed Ctrl+C! Preparing for graceful exit.')
  if not loop_var:
    kill_external_readout("-9")
  else:
    logger.info("Hint: Press 2nd time Ctrl+C to also terminate forcefully external readout.")
  loop_var = False
signal.signal(signal.SIGINT, signal_handler)

# Inform systemd that we've finished our startup sequence...
n = sdnotify.SystemdNotifier()
n.notify("READY=1")
count = 1 #some watchdog counter


##################################################

pattern = r"theta: (.*?) Dist: (.*?) Q: (\d*)"
pattern_start = r"S  theta: (.*?) Dist: (.*?) Q: (\d*)"

data = []


last_notify = time.time()
scan_data_counter = 0

def kill_external_readout(param="-15"):
  logger.info("killall started.")
  try:
    command = ["/usr/bin/killall", param, "ultra_simple"]
    subprocess.run(command)
    logger.info("killall called.")
  finally:
    pass
  logger.info("killall done.")

kill_external_readout()

try:
  command = ["/home/pi/rplidar_sdk/output/Linux/Release/ultra_simple", "--channel", "--serial",  "/dev/ttyUSB0", "115200"]
  process = subprocess.Popen(command, stdout=subprocess.PIPE, universal_newlines=True)
  logger.info("subprocess started.")

  #####################################################

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

#    logger.debug("started readline")
    line = process.stdout.readline()
#    logger.debug("read line: ", line)
    if not line:
        logger.warning("readline empty")
        loop_var = False
    else:
      matches = re.findall(pattern_start, line.strip())
      if len(matches) > 0: #start gefunden
        scan_data_counter += 1
        client.publish("homie/"+mqtt_client_name+"/data", json.dumps(data), qos=1)
        logger.info(f"data packet #{scan_data_counter} sent. New data incoming...")
        data = []
      else:
        matches = re.findall(pattern, line.strip())

      if len(matches) > 0:
        if float(matches[0][1]) > 0: #if distance >0
          data.append([float(matches[0][0]), float(matches[0][1]), int(matches[0][2]) ])


      if time.time()-last_notify > 1:
        #inform systemd via sdnotify we are still alive
        n.notify("STATUS=Count is {}".format(count))
        n.notify("WATCHDOG=1")
        count += 1
        last_notify = time.time()


#    time.sleep(0.001)
#    time.sleep(1-math.modf(time.time())[0])  # make the loop run every second

finally:
    process.terminate()



client.disconnect()
client.loop_stop()
logger.info("Program stopped.")

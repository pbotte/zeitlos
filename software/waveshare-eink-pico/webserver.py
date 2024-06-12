from flask import Flask, send_file, make_response
import threading
import time
import numpy as np
from PIL import Image
import io

import json
import logging
import argparse
import queue, traceback
import paho.mqtt.client as paho
import signal
import sys
import re

import generate_img

#-----
logging.basicConfig(level=logging.WARNING, format='%(asctime)-6s %(levelname)-8s  %(message)s')
logger = logging.getLogger("Shop eink Server")

parser = argparse.ArgumentParser(description='Shop eink Server')
parser.add_argument("-v", "--verbosity", help="increase output verbosity", default=0, action="count")
parser.add_argument("-b", "--mqtt-broker-host", help="MQTT broker hostname. default=localhost", default="localhost")
args = parser.parse_args()
logger.setLevel(logging.WARNING-(args.verbosity * 10 if args.verbosity <= 2 else 20))

debug = True if args.verbosity>1 else False

mqtt_client_name = "shop-eink-server"
#-----

def on_connect(client, userdata, flags, rc):
    if rc == 0:
        logger.info("MQTT connected OK. Return code "+str(rc))
        client.subscribe("homie/shop_controller/shop_overview/products")
#        client.subscribe(f"homie/{mqtt_client_name}/reference")
#        client.subscribe(f"homie/{mqtt_client_name}/reference/set")
        client.subscribe("homie/shop_controller/shop_status")
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


#connect to MQTT broker
client = paho.Client(mqtt_client_name)
client.on_message = on_message
client.on_connect = on_connect
client.on_disconnect = on_disconnect
client.enable_logger(logger) #info: https://www.eclipse.org/paho/clients/python/docs/#callbacks
logger.info("connecting to broker: "+args.mqtt_broker_host+". If it fails, check whether the broker is reachable. Check the -b option.")

# start with MQTT connection and set last will
logger.info(f"mqtt_client_name: {mqtt_client_name}")
client.will_set(f"homie/{mqtt_client_name}/state", '0', qos=1, retain=True)
client.connect(args.mqtt_broker_host)
client.loop_start() #start loop to process received messages in separate thread
logger.debug("MQTT loop started.")
client.publish(f"homie/{mqtt_client_name}/state", '1', qos=1, retain=True)

##############################################################################
def signal_handler(sig, frame):
    logger.info(f"Program terminating.")

    client.loop_stop()
    client.disconnect()

    time.sleep(0.1) #to allow all MQTT to be send

    sys.exit(0)

signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)
##############################################################################

product_reference = {}



############################################################


app = Flask(__name__)

@app.route('/')
def serve_image():
    return send_file('price_tag_with_image.png', mimetype='image/png')

@app.route('/grayscale')
def serve_grayscale_image():
    # Create a grayscale image stored in a NumPy array
    array = np.random.randint(0, 256, (100, 100), dtype=np.uint8)  # Example grayscale image
    array = generate_img.generate_image()

    image = Image.fromarray(array)

    
    # Save the image to a BytesIO object
    img_io = io.BytesIO()
    image.save(img_io, 'PNG')
    img_io.seek(0)
    
    return send_file(img_io, mimetype='image/png')

@app.route('/products')
def products():
    return f"{product_reference}"

@app.route('/get')
def product_file():
    return generate_img.get_product_file(1)

def start_flask():
#    app.run(host='0.0.0.0', port=80)
    from waitress import serve
    serve(app, host="0.0.0.0", port=8090)

if __name__ == "__main__":
    # Start Flask server in a separate thread
    server_thread = threading.Thread(target=start_flask, daemon=True)
    server_thread.start()

    # Main loop
    try:
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

                if message.topic.lower() == f"homie/shop_controller/shop_overview/products":
                    logger.info("product overview received")
                    product_reference = json.loads(m)

                if message.topic.lower() == f"homie/{mqtt_client_name}/reference":
                    logger.info("reference received")
                    values_reference = json.loads(m)






            time.sleep(0.1)  # Sleep for a while to simulate work
    except KeyboardInterrupt:
        print("Shutting down...")


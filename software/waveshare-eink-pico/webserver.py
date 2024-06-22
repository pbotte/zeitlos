#!/usr/bin/python3
#
# start with: python webserver.py -v
# navigate to http://localhost:8090
# sub calls for image like: http://localhost:8090/getimage?productid=1
#           for output as file: http://localhost:8090/getfile?productid=1

from flask import Flask, send_file, request, render_template_string, abort
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

#will be used for /getconfig
status_last_touched_scale_str = ""

mqtt_client_name = "shop-eink-server"
#-----

def on_connect(client, userdata, flags, rc):
    if rc == 0:
        logger.info("MQTT connected OK. Return code "+str(rc))
        client.subscribe("homie/shop_controller/shop_overview/products")
        client.subscribe("homie/shop_controller/shop_overview/scales_products")
#        client.subscribe(f"homie/{mqtt_client_name}/reference/set")
        client.subscribe("homie/shop_controller/shop_status")
        client.subscribe("homie/+/scales/+/touched") #zum Waagen auswählen beim Bestückenu und Kalibrieren
        logger.debug("MQTT: Subscribed to all topics")
        client.publish(f"homie/{mqtt_client_name}/state", '1', qos=1, retain=True)

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

##############################################################################
main_loop_var = True
def signal_handler(sig, frame):
    global main_loop_var
    logger.info(f"Program terminating. Sending correct /state ... (this takes 1 second)")

    main_loop_var = False

signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)
##############################################################################

product_reference = {}
scales_products_assignment = {}



############################################################


app = Flask(__name__)

@app.route('/')
def home():
    html_content = """
    <!doctype html>
    <html lang="en">
      <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1, shrink-to-fit=no">
        <title>eink server</title>
      </head>
      <body>
        <h1>Commands available</h1>
        <p>1: <a href="/getimage">/getimage</a></p>
        <p>2: <a href="/products">/products</a></p>
        <p>3: <a href="/assignment">/assignment</a></p>
        <p>4: <a href="/getconfig">/getconfig?id=einkID</a></p>
      </body>
    </html>
    """
    return render_template_string(html_content)
#    return send_file('price_tag_with_image.png', mimetype='image/png')

@app.route('/getimage')
def serve_grayscale_image():
    output_format = request.args.get('o', None) #call with &0=1 to get output for eink, otherwise as PNG

    product_id = request.args.get('productid', None)
    scale_id = request.args.get('scaleid', None)
    if scale_id: scale_id=scale_id.lower()

    product_id_via_scale_id = None
    if scale_id and scale_id in scales_products_assignment:
        product_id_via_scale_id = scales_products_assignment[scale_id]
    logger.info(f"/getimage request with:{output_format=} {product_id=} {scale_id=} {product_id_via_scale_id=}")

    if not product_id: 
        product_id = product_id_via_scale_id
    product_id = str(product_id) # of variable is int, make it a string for lookup in product_reference

    if not product_id in product_reference: 
        array = generate_img.generate_image("Product ID not found", 
                                        price=0,
                                        description=f"Product ID '{product_id}' not provided or product does not exist. Call with GET parameters productid or scaleid",
                                        supplier="",
                                        bottom_text="" )
    #    abort(400, "Product ID not provided or product does not exist. Call with GET parameters productid or scaleid")
    else:
        def extract_number_before_g(text):
            match = re.search(r'(\d+)\s*g', text)
            if match:
                return int(match.group(1))/1000
            match = re.search(r'(\d+)\s*kg', text)
            if match:
                return int(match.group(1))
            return None
        product_mass_in_kg = extract_number_before_g(product_reference[product_id]['ProductName'])
        if not product_mass_in_kg: 
            product_mass_in_kg = extract_number_before_g(product_reference[product_id]['ProductDescription'])
        logger.info(f"{product_mass_in_kg=} {product_reference[product_id]['kgPerUnit']=}")
        bottom_text = ""
        if product_mass_in_kg: 
           bottom_text= f"{(product_mass_in_kg*1000):.0f}g    {(product_reference[product_id]['PricePerUnit']/product_mass_in_kg):.2f} €/kg".replace(".",",")

        array = generate_img.generate_image(product_reference[product_id]['ProductName'], 
                                            price=product_reference[product_id]['PricePerUnit'],
                                            description=product_reference[product_id]['ProductDescription'],
                                            supplier=product_reference[product_id]['Supplier'],
                                            bottom_text=bottom_text )
    #, PriceType, PricePerUnit, kgPerUnit, VAT, 

    #output as text for eink display
    if output_format:
        return generate_img.process_image_to_string(array)

    #if not, then output as png
    image = Image.fromarray(array)

    # Save the image to a BytesIO object
    img_io = io.BytesIO()
    image.save(img_io, 'PNG')
    img_io.seek(0)
    
    return send_file(img_io, mimetype='image/png')

@app.route('/products')
def products():
    product_id = request.args.get('productid', None)
    product_id = str(product_id)
    if product_id and product_id in product_reference:
        return f"{product_reference[product_id]}"
    else:
        return f"{product_reference}"

@app.route('/assignment')
def assignment():
    scale_id = request.args.get('id', '')
    if scale_id:
        if scale_id in scales_products_assignment:
            return f"{scales_products_assignment[scale_id]}"
        else:
            abort(400, 'Scale without product.') 
    else:
        return f"{scales_products_assignment}"

#the eink display requests this, after a button is pressed. the last touched scale will be returned.
@app.route('/getconfig')
def getconfig():
    eink_id = request.args.get('id', '')
    if eink_id:
        if status_last_touched_scale_str:
            return status_last_touched_scale_str
        else:
            abort(400, 'No scale touched yet.') 
    else:
        return "No eink id as GET parameter id provided."


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

                if message.topic.lower() == f"homie/shop_controller/shop_overview/products":
                    logger.info("product overview received")
                    product_reference = json.loads(m)

                if message.topic.lower() == f"homie/shop_controller/shop_overview/scales_products":
                    logger.info("products to scales assignment received")
                    scales_products_assignment = json.loads(m)

                if message.topic.lower() == f"homie/{mqtt_client_name}/reference":
                    logger.info("reference received")
                    values_reference = json.loads(m)

                #eine Waage wurde gedrückt, Empfang von Nachrichten wie: homie/scale-shop-shelf06-0-1.2.5.5-1.0/scales/4930370A3419/touched
                if len(msplit) == 5 and msplit[2].lower() == "scales" and msplit[4].lower() == "touched":
                    if m == "1":
                        status_last_touched_scale_str = msplit[3].lower() #4930370A3419
                        logger.info(f"Auf dem Regal wurde die folgende Waage gedrückt: {status_last_touched_scale_str}")






            time.sleep(0.1)  # Sleep for a while to simulate work
    except KeyboardInterrupt:
        print("Shutting down...")


# Terminating everything
logger.info(f"Terminating. Cleaning up.")

# send state=0
client.publish(f"homie/{mqtt_client_name}/state", '0', qos=1, retain=True)

time.sleep(1) #to allow the published message to be delivered.

client.loop_stop()
client.disconnect()

logger.info("Program stopped.")

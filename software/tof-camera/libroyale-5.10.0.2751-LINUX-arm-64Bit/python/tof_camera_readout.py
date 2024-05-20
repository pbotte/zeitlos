#!/usr/bin/python3

import argparse
try:
    from roypypack import roypy  # package installation
except ImportError:
    import roypy  # local installation
import time
import queue
from sample_camera_info import print_camera_info
from roypy_sample_utils import CameraOpener, add_camera_opener_options, select_use_case
from roypy_platform_utils import PlatformHelper

import paho.mqtt.client as paho
import logging, argparse
import socket
import queue, traceback
import re

import sys
import collections

import numpy as np
import matplotlib.pyplot as plt

tof_data_queue = collections.deque(maxlen=20)
tof_data_base = None
v_std = None


logging.basicConfig(format="%(asctime)-15s %(levelname)-8s  %(message)s")
logger = logging.getLogger("TOF camera Readout")

parser = argparse.ArgumentParser(description='TOF camera Readout.')
parser.add_argument("-v", "--verbosity", help="increase output verbosity", default=0, action="count")
parser.add_argument("-b", "--mqtt-broker-host", help="MQTT broker hostname", default="localhost")

parser.add_argument ("--code", default=None, help="access code")
parser.add_argument ("--rrf", default=None, help="play a recording instead of opening the camera")
parser.add_argument ("--cal", default=None, help="load an alternate calibration file (requires level 2 access)")
parser.add_argument ("--raw", default=False, action="store_true", help="enables raw data output (requires level 2 access)")

args = parser.parse_args()
logger.setLevel(logging.WARNING-(args.verbosity*10 if args.verbosity <=2 else 20) )

debug = True if args.verbosity>1 else False
mqtt_client_name = f"tof-cam-{socket.gethostname()}"

logger.info(f"This is the MQTT-Client-ID: {mqtt_client_name}")
#######################################################################
# MQTT functions
def on_connect(client, userdata, flags, rc):
  if rc==0:
    logger.info("MQTT connected OK. Return code "+str(rc) )
    client.subscribe("homie/"+mqtt_client_name+"/cmd/#")
    client.subscribe("homie/shop_controller/shop_status")
    logger.info("MQTT: Success, subscribed to all topics")
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
client = paho.Client(paho.CallbackAPIVersion.VERSION1, mqtt_client_name)
client.on_message=on_message
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



class MyEventListener(roypy.PythonEventListener):
    def __init__(self):
        super(MyEventListener, self).__init__()

    def onEventPython(self, severity, description, type):
        print("Event : Severity : ", severity, " Description : ", description, " Type : ", type)

class MyListener(roypy.IDepthDataListener):
    def __init__(self, q):
        super(MyListener, self).__init__()
        self.queue = q
        self.figSetup = False

    def onNewData(self, data):
        #this is slower
        #zvalues = []
        #for i in range(data.getNumPoints()):
        #    zvalues.append(data.getZ(i))
        #zarray = np.asarray(zvalues)
        #p = zarray.reshape (-1, data.width)

        #faster retrieval of points by using numpy.i
        pc = data.npoints ()
        p = pc[:,:,2]
        self.queue.put(p)

    def paint (self, data):
        """Called in the main thread, with data containing one of the items that was added to the
        queue in onNewData.
        """
        # create a figure and show the raw data
        if not self.figSetup:
            self.fig = plt.figure(1)
            self.im = plt.imshow(data)

            plt.show(block = False)
            plt.draw()
            self.figSetup = True
        else:
            self.im.set_data(data)
            self.fig.canvas.draw()
        # this pause is needed to ensure the drawing for
        # some backends
        plt.pause(0.001)


np.set_printoptions(threshold=sys.maxsize)


platformhelper = PlatformHelper()
#parser = argparse.ArgumentParser (usage = __doc__)
#add_camera_opener_options (parser)
options = parser.parse_args()
opener = CameraOpener (options)
cam = opener.open_camera ()

print_camera_info (cam)
print("isConnected", cam.isConnected())
print("getFrameRate", cam.getFrameRate())

#    curUseCase = select_use_case(cam) #select dialog
curUseCase = "Long_Range_5FPS"

print ("Using a live camera")

# we will use this queue to synchronize the callback with the main
# thread, as drawing should happen in the main thread
q = queue.Queue()
l = MyListener(q)
cam.registerDataListener(l)

print ("Setting use case : " + curUseCase)
cam.setUseCase(curUseCase)

cam.startCapture()

while True: #time.time() < t_end:
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

        #Setze die Referenz, wenn kein Kunde im Laden ist.
        if (len(msplit) == 4 and msplit[2].lower() == "cmd" and msplit[3].lower() == "set_zero") or \
            (message.topic.lower() == "homie/shop_controller/shop_status" and int(m) == 2):
            logger.info("Via MQTT set_zero or shop_status == 2 received: Setting reference.")
            if len(tof_data_queue) < 8:
                logger.warning("Zu wenig Daten bisher empfangen.")
            else:
                #average over all arrays:, see https://stackoverflow.com/questions/18461623/average-values-in-two-numpy-arrays
                avg = np.array([ i for i in list(tof_data_queue)])
                v = np.mean( avg, axis=0 ) # if you want to ignore nan, use: np.nanmean
                v_std = np.std( avg, axis=0 ) # if you want to ignore nan, use: np.nanmean
#                print(v_std)

                #print(np.argwhere(v_std > 0.01))
                v_std[v_std > 0.01] = 0
                v_std[v_std != 0] = 1
#                l.paint(v_std)
                print()

                tof_data_base = np.copy(v)


    try:
        # try to retrieve an item from the queue.
        # this will block until an item can be retrieved
        # or the timeout of 1 second is hit
        logger.debug(f"Number of images in driver queue: {len(q.queue)}")
        if len(q.queue) == 0:
            item = q.get(True, 1)
        else:
            for i in range (0, len (q.queue)):
                item = q.get(True, 1)
    except queue.Empty:
        # this will be thrown when the timeout is hit
        break
    else:
        tof_data_queue.append(item)

    if len(tof_data_queue) < 8:
        logger.info(f"Anzahl Einträge zur Mittelung: {len(tof_data_queue)}. Noch keine Ausgabe via MQTT, mind. 8 nötig.")
    else:
        if tof_data_base is None:
            logger.debug(f"Noch keine Referenz vorhanden. Daher keine weitere Berechnung.")
        else:
    #        l.paint(item)
            nv = (tof_data_base - item)
            #logger.info(f"{np.sum(nv)}")
            nv = (tof_data_base - item) * v_std
            nv[nv < 0.1] = 0
            logger.info(f"Difference: {np.sum(nv)}")
            client.publish(f"homie/{mqtt_client_name}/value", np.sum(nv), qos=0)

#                l.paint(v_std)
        #l.paint(nv)

cam.stopCapture()

client.publish(f"homie/{mqtt_client_name}/state", '0', qos=1, retain=True)

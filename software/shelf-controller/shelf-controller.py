#!/usr/bin/python3

import serial
import time
import re
import struct
import logging, argparse
import json
import paho.mqtt.client as paho
import queue, traceback
import signal
import sys
import collections, statistics
import math
import socket
import os

logging.basicConfig(format="%(asctime)-15s %(levelname)-8s  %(message)s")
logger = logging.getLogger("Shelf Readout")

parser = argparse.ArgumentParser(description='Shelf Readout.')
parser.add_argument("-v", "--verbosity", help="increase output verbosity", default=0, action="count")
parser.add_argument("-b", "--mqtt-broker-host", help="MQTT broker hostname", default="localhost")
parser.add_argument("serial_device_name", help="eg /dev/ttyUSB0", type=str)
args = parser.parse_args()
logger.setLevel(logging.WARNING-(args.verbosity*10 if args.verbosity <=2 else 20) )

debug = True if args.verbosity>1 else False



#######################################################################

def send_and_recv(str_to_send, echo_out = False, print_return = False):
    logger.debug(f"<<{str_to_send}")
    ser.write(str_to_send.encode() + b'\n')

    out = ser.readline().decode().strip()
    if out != '' and print_return:
        logger.debug(f">>{out}")

    # analyse output
    # Define the regular expression pattern to capture the relevant parts
    pattern = r'^([rw])\s+((?:[A-Fa-f0-9]{2}\s+){1,})$'

    # Use the regular expression to match the input string
    match = re.match(pattern, out+"\n")

    ret_val = []
    command = None
    if match:
        # Extract the captured groups
        command = match.group(1)     # 'r' or 'w'
        hex_numbers = match.group(2).split()   # Split numbers separated by spaces

        # Convert numbers to integers (base 16) and print the results
        #print(f"Command: {command}")
        #print("Hex Numbers:")
        for number in hex_numbers:
            decimal_number = int(number, 16)
            ret_val = ret_val + [decimal_number]
            #print(decimal_number)
    else:
        logger.warning(f"Invalid data from serial: {out}")

    return (command, ret_val)


def bin_search():
    # MAC addresses scan range
    min = 0x0
    max = 0xffff_ffff_ffff

    l = min
    r = max
    i = 0
    while i<52:
        m = l + (r-l)//2

        #print(f"i: {i} {l:014_X} {m:014_X} {r:014_X}")
        str_to_send = f"w0003{m:#014X}".replace("0X","")
        #print(str_to_send)
        send_and_recv(str_to_send)

        str_to_send = f"r0801"
        #print(str_to_send)

        res = send_and_recv(str_to_send)
        #print(res)

        if res[1][1] == 0x00:
            if r-l<=1: return m #Ausgabe, falls 0 gesucht wurde
            r = m
        else:
            if r-l<=1: return r #Ausgabe aller anderen Adressen
            l = m+1

        i+=1

    return False #nichts gefunden. Waage während des Suchlaufs kaputtgegangen?

#get usb path of device
usb_path_device = "unknown"
last_dev = os.popen(f'udevadm info /{args.serial_device_name} | grep DEVLINKS').read()
regex = r"-usb-[0-9:\.]+-port0"
matches = re.finditer(regex, last_dev, re.MULTILINE)
for matchnum, match in enumerate(matches): #only one match should be found
  s=match.group()
  usb_path_device = s.replace(":","-").replace("-usb-","").replace("-port0","")
mqtt_client_name = f"scale-{socket.gethostname()}-{usb_path_device}"
#mqtt_client_name = f"scale-{socket.gethostname()}-{args.serial_device_name.replace('/','-')}"

logger.info(f"This is the MQTT-Client-ID: {mqtt_client_name}")
#######################################################################
# MQTT functions
def on_connect(client, userdata, flags, rc):
  if rc==0:
    logger.info("MQTT connected OK. Return code "+str(rc) )
    client.subscribe("homie/"+mqtt_client_name+"/cmd/#")
    client.subscribe(f"homie/{mqtt_client_name}/cmd/scales/+/led")
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

#Global information on all scales
anzahl_waagen = 0
waagen = {} #index: i2c_add   eg: 9: {'mac': "493037D20E1B", 'address': 9, 'slope': 1, 'zero':0, 'state': 0, ...},}
LUT_MAC_2_I2C_ADD = {} #LUT to get I2C address from MAC address
shop_status = 0

##############################################################################
def signal_handler(sig, frame):
    logger.info(f"Program terminating. Sending correct /state for all {anzahl_waagen} scales... (this takes 1 second)")

    for w in waagen.items():
        client.publish(f"homie/{mqtt_client_name}/scales/{waagen[w[0]]['mac']}/state", 0, qos=0, retain=True)
        waagen[w[0]]['state'] = 0

    time.sleep(1) #to allow the published message to be delivered.

    client.loop_stop()
    client.disconnect()

    ser.close()

    sys.exit(0)

signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)
##############################################################################


ser = serial.Serial(port=args.serial_device_name, baudrate=115200, timeout=1 )
#ser.isOpen()

# Waagen Neustart
send_and_recv("w0000")
logger.info("Warte auf Waagen, bis sie den Neustart ausgeführt haben. 8 Sekunden ...")
time.sleep(8)

##alle LEDs an
send_and_recv("w0005")
time.sleep(0.9)
#Antwort bit setzen
send_and_recv("w0001")
time.sleep(.1)
#alle LEDs aus
send_and_recv("w0004")
time.sleep(.1)

def search_waagen():
    #Antwort bit setzen
    send_and_recv("w0001")
    time.sleep(.1)

    global anzahl_waagen, waagen
    weiter_suchen = True
    anzahl_waagen = 0
    waagen = {} #9: {'mac': "4930_37D2_0E1B", 'address': 9, 'slope': 1, 'zero':0},}
    while weiter_suchen:
        #test, ob noch waagen ohne neue I2C Adresse
        logger.info(f"Suche weitere Waagen. ")
        m = 0xffff_ffff_ffff
        str_to_send = f"w0003{m:#014X}".replace("0X","")
        send_and_recv(str_to_send)

        str_to_send = f"r0801"
        res = send_and_recv(str_to_send)
        logger.info(f"Rückgabewerte der Suche: {res}")

        weiter_suchen = True if res[1][0] > 0 else False

        if weiter_suchen: #welche haben sich gemeldet
            anzahl_waagen += 1
            neue_i2c_adresse = anzahl_waagen + 8 #ab Adresse 9 geht's los

            res2 = bin_search()
            logger.info(f"Waage mit MAC {res2:014_X} gefunden.")
            waagen[neue_i2c_adresse] = {'mac': f"{res2:012X}", 'i2c_address': neue_i2c_adresse, 'slope': 1, 
                                        'zero':0, 'state':0, 
                                        'stack': collections.deque(maxlen=10), #if maxlen is changed, check later for touch functionality that it still works
                                        'touched': 0,
                                        'last_mass_submitted': None, 'last_mass_submitted_time': None, 'last_touched_time': 0}
            LUT_MAC_2_I2C_ADD[f"{res2:012X}"] = neue_i2c_adresse

            logger.info(f"Setze Wagge (Suchlauf {anzahl_waagen}): {res2:014_X} auf I2C Adresse {neue_i2c_adresse:02X}")
            res2 = send_and_recv(f"w0002{res2:012X}{neue_i2c_adresse:02X}")
            logger.debug(f"Rückgabewert Schreiben I2C Adresse: {res2}")

            client.publish(f"homie/{mqtt_client_name}/scales/{waagen[neue_i2c_adresse]['mac']}/state", 0, qos=0, retain=True)
            client.publish(f"homie/{mqtt_client_name}/scales/{waagen[neue_i2c_adresse]['mac']}/i2c_address", neue_i2c_adresse, qos=0, retain=True)

            time.sleep(0.5) # wait for electronics to set new i2c address

            #read MAC, LED, BUILD_NUMBER and HARDWARE_REV
            #set: prepare for next read
            send_and_recv(f"w{neue_i2c_adresse:02X}01")
            res4 = send_and_recv(f"r{neue_i2c_adresse:02X}0D") #read 13 characters from bus
            if (res4[1][0] == 13): #13 characters expected
                logger.info(f"Gefundene Eigenschaften: MAC: {res4[1][1:7]}, LED: {res4[1][7]}, BUILD: {res4[1][8:12]}, Hardware: {res4[1][12:14]}")
                BUILD_VERSION = (res4[1][8]<<24)+(res4[1][9]<<16)+(res4[1][10]<<8)+(res4[1][11])
                HARDWARE_REV = (res4[1][12]<<8) + res4[1][13]
                client.publish(f"homie/{mqtt_client_name}/scales/{waagen[neue_i2c_adresse]['mac']}/firmware_version", BUILD_VERSION, qos=0, retain=True)
                client.publish(f"homie/{mqtt_client_name}/scales/{waagen[neue_i2c_adresse]['mac']}/hardware_version", HARDWARE_REV, qos=0, retain=True)
            else:
                logger.warning(f"Falsche Anzahl an Bytes zurück erhalten: {res4[1][0]}")

            #Read out offset from scale: 4 single bytes (address 5..8)
            r=[]
            for i in range(5,8+1):
              res7 = send_and_recv(f"w{neue_i2c_adresse:02X}060{i}") # prepare to read 1 byte from address 0x07
              logger.debug(f"Prepare to Read Return {res7=}")
              res5 = send_and_recv(f"r{neue_i2c_adresse:02X}01") # read 1 byte
              logger.debug(f"Read this byte from address 0x0{i}: {res5=}")
              r.append(res5[1][1])
            logger.debug(f"Gesamt gelesen: {r=}")
            v=struct.unpack('<f',bytearray(r))[0]  #unpack returns: (-524945,), get the right value with [0]
            waagen[neue_i2c_adresse]['zero'] = v
            client.publish(f"homie/{mqtt_client_name}/scales/{waagen[neue_i2c_adresse]['mac']}/zero_raw", v, qos=0, retain=True)


            #Read out slope from scale: 4 single bytes (address 1..4)
            r=[]
            for i in range(1,4+1):
              res7 = send_and_recv(f"w{neue_i2c_adresse:02X}060{i}") # prepare to read 1 byte from address 0x07
              logger.debug(f"Prepare to Read Return {res7=}")
              res5 = send_and_recv(f"r{neue_i2c_adresse:02X}01") # read 1 byte
              logger.debug(f"Read this byte from address 0x0{i}: {res5=}")
              r.append(res5[1][1])
            logger.debug(f"Gesamt gelesen: {r=}")
            v=struct.unpack('<f',bytearray(r))[0]  #unpack returns: (-7.092198939062655e-05,), get the right value with [0]
            if math.isnan(v): v=-4.632391446259352e-05 #set to default value for 4*50kg scales if value is not set (==nan)
            waagen[neue_i2c_adresse]['slope'] = v
            client.publish(f"homie/{mqtt_client_name}/scales/{waagen[neue_i2c_adresse]['mac']}/slope", v, qos=0, retain=True)


            send_and_recv(f"w{neue_i2c_adresse:02X}00") #set back normal read mode

            #individuelle LED kurz an
            res3 = send_and_recv(f"w{neue_i2c_adresse:02X}03")
            logger.debug(f"Rückgabewert Schreiben I2C LED an: {res3}")
            #time.sleep(0.5)
            #individuelle LED wieder aus
            #res3 = send_and_recv(f"w{neue_i2c_adresse:02X}02")
            #logger.info(f"Rückgabewert Schreiben I2C LED aus: {res3}")
            
            if anzahl_waagen % 8==0: #nicht mehr als 8 LEDS gleichzeitig an, da Strom für Controller zu hoch
              time.sleep(0.5)
              #alle LEDs aus
              send_and_recv("w0004")
              logger.info(f"Switch off all LEDs to limit the current drawn by the shelf controller. This is repeated for every 8 scales found.")

    logger.info(f"gefundene Waagen Anzahl: {anzahl_waagen}")
    logger.info(f"gefundene Waagen: {waagen}")
    logger.info(f"{LUT_MAC_2_I2C_ADD=}")
    time.sleep(1)

    #alle LEDs aus
    send_and_recv("w0004")    

search_waagen()

#test string is float?
def is_float(element: any) -> bool:
    if element is None: 
        return False
    try:
        float(element)
        return True
    except ValueError:
        return False

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
        if len(msplit) == 4 and msplit[2].lower() == "cmd" and msplit[3].lower() == "leds":
            if m == "1":
                logger.info("Per MQTT empfangen: Setze alle LEDs an.")
                send_and_recv("w0005")
            else:
                logger.info("Per MQTT empfangen: Setze alle LEDs aus.")
                send_and_recv("w0004")
        
        if len(msplit) == 4 and msplit[2].lower() == "cmd" and msplit[3].lower() == "restart":
            logger.info("Per MQTT empfangen: Alle Waagen neustarten.")
            send_and_recv("w0000") # Waagen Neustart
            logger.info("Warte 8 Sekunden, bis alle Waagen den Neustart sicher ausgeführt haben.")

        if len(msplit) == 4 and msplit[2].lower() == "cmd" and msplit[3].lower() == "search":
            logger.info("Per MQTT empfangen: Neuer Waagen scan.")
            search_waagen()

        if len(msplit) == 4 and msplit[2].lower() == "cmd" and msplit[3].lower() == "set_zero":
            logger.info("Per MQTT empfangen: set_zero")
            for w in waagen.items():
                waagen[w[0]]['zero'] = statistics.mean(list(waagen[w[0]]['stack']))
                logger.info(f"Waage {w[1]['mac']} Zero gesetzt auf: {waagen[w[0]]['zero']}")

                #write single bytes to scale
                v=struct.pack('<f', waagen[w[0]]['zero']) #returns eg: b'o\xfd\xf7\xff'
                for i,x in enumerate(v):
                    res6 = send_and_recv(f"w{w[0]:02X}05{i+5:02X}{x:02X}") # write 1 byte to address i+5
                    logger.info(f"Write Return (address {i+5}, value: {x}) {res6=}")
                client.publish(f"homie/{mqtt_client_name}/scales/{w[1]['mac']}/zero_raw", waagen[w[0]]['zero'], qos=0, retain=True)


        if len(msplit) == 6 and msplit[2].lower() == "cmd" and msplit[3].lower() == "scales" and msplit[5].lower() == "set_zero":
            logger.info(f"Per MQTT empfangen: set_zero einer individuellen Waage {msplit[4].upper()} setzen")
            if msplit[4].upper() in LUT_MAC_2_I2C_ADD:
                i2c_address = LUT_MAC_2_I2C_ADD[msplit[4].upper()]
                waagen[i2c_address]['zero'] = statistics.mean(list(waagen[i2c_address]['stack']))
                logger.info(f"Waage {waagen[i2c_address]['mac']} Zero gesetzt auf: {waagen[i2c_address]['zero']}")

                #write single bytes to scale
                v=struct.pack('<f', waagen[i2c_address]['zero']) #returns eg: b'o\xfd\xf7\xff'
                for i,x in enumerate(v):
                    res6 = send_and_recv(f"w{i2c_address:02X}05{i+5:02X}{x:02X}") # write 1 byte to address i+5
                    logger.info(f"Write Return (address {i+5}, value: {x}) {res6=}")
                client.publish(f"homie/{mqtt_client_name}/scales/{waagen[i2c_address]['mac']}/zero_raw", waagen[i2c_address]['zero'], qos=0, retain=True)
            else:
                logger.warning(f"MAC not in local list: {msplit[4].upper()}")

        if len(msplit) == 6 and msplit[2].lower() == "cmd" and msplit[3].lower() == "scales" and msplit[5].lower() == "set_slope":
            logger.info(f"Per MQTT empfangen: individuelle Steigung der Waage {msplit[4].upper()} setzen: {m} kg")
            if msplit[4].upper() in LUT_MAC_2_I2C_ADD:
                i2c_address = LUT_MAC_2_I2C_ADD[msplit[4].upper()]

                if is_float(m):
                    # slope in kg / raw ticks
                    waagen[i2c_address]['slope'] = float(m) / (
                        statistics.mean(list(waagen[i2c_address]['stack'])) - waagen[i2c_address]['zero']
                        )
                    logger.info(f"Mittelwert: {statistics.mean(list(waagen[i2c_address]['stack']))} Differenz zur 0: {statistics.mean(list(waagen[i2c_address]['stack'])) - waagen[i2c_address]['zero']} Steigung: {waagen[i2c_address]['slope']}")

                    #write single bytes to scale
                    v=struct.pack('<f', waagen[i2c_address]['slope']) #returns eg: b'\xf4\xbb\x94\xb8'
                    for i,x in enumerate(v):
                        res6 = send_and_recv(f"w{i2c_address:02X}05{i+1:02X}{x:02X}") # write 1 byte to address i+1
                        logger.info(f"Write Return {res6=}")
                    client.publish(f"homie/{mqtt_client_name}/scales/{waagen[i2c_address]['mac']}/slope", waagen[i2c_address]['slope'], qos=0, retain=True)
                else:
                    logger.warning(f"Value passed: '{m}' is no float.")
            else:
                logger.warning(f"MAC not in local list: {msplit[4].upper()}")

        if len(msplit) == 6 and msplit[2].lower() == "cmd" and msplit[3].lower() == "scales" and msplit[5].lower() == "led":
            logger.info(f"Per MQTT empfangen: individuelle LED von Waage {msplit[3].upper()} on/off: {m}")
            if msplit[4].upper() in LUT_MAC_2_I2C_ADD:
                i2c_address = LUT_MAC_2_I2C_ADD[msplit[4].upper()]
                if m == "1":
                    res3 = send_and_recv(f"w{i2c_address:02X}03")
                else:
                    res3 = send_and_recv(f"w{i2c_address:02X}02")
                logger.info(f"Rückgabewert Schreiben I2C LED an: {res3}")
            else:
                logger.warning(f"MAC not in local list: {msplit[4].upper()}")

        if message.topic.lower() == "homie/shop_controller/shop_status":
            shop_status = int(m)


            

    # Poll all scales for raw readings
    for w in waagen.items():
        i2c_address = w[1]['i2c_address']
        res = send_and_recv(f"r{i2c_address:02X}04")
        state_okay = 1 if res[1][0] == 4 else 0
        if state_okay == 1:
            v = struct.unpack('<l',bytes(res[1][1:5]))[0]
            logger.debug(f"Read i2c address 0x{i2c_address:02X}\t raw value: {v}")
            if debug:
                client.publish(f"homie/{mqtt_client_name}/scales/{waagen[w[0]]['mac']}/raw", v, qos=0, retain=False)
            waagen[w[0]]['stack'].append(v)

            #######################################################################
            # calculate mass and submit if change large enough
            v_mean = statistics.mean(list(waagen[w[0]]['stack'])[-4:]) #get the last 4 readings
            mass = ( v_mean - waagen[w[0]]['zero'] ) * waagen[w[0]]['slope']
            #submit only, when change is larger than 0.05kg OR every 10 seconds OR 5seconds after the last touch
            if (waagen[w[0]]['last_mass_submitted'] is None) or \
                (abs(mass-waagen[w[0]]['last_mass_submitted']) > 0.05) or \
                (waagen[w[0]]['last_mass_submitted_time'] is None) or \
                ((time.time()-waagen[w[0]]['last_mass_submitted_time']) > 10 ) or \
                ((time.time()-waagen[w[0]]['last_touched_time']) < 5):
                client.publish(f"homie/{mqtt_client_name}/scales/{waagen[w[0]]['mac']}/mass", mass, qos=0, retain=True)            
                waagen[w[0]]['last_mass_submitted'] = mass
                waagen[w[0]]['last_mass_submitted_time'] = time.time()

            #######################################################################
            # check for touch functionality start
            if (len(waagen[w[0]]['stack'])>8): #some reading has to be in the stack
                # check the last 3 readings and compare to the first in stack.
                # mean(new)-mean(old) > 10*std-dev
                act_distance_avg_new = statistics.mean(list(waagen[w[0]]['stack'])[-3:])
                act_distance_stdev = statistics.stdev(list(waagen[w[0]]['stack'])[:-4])
                act_distance_avg_old = statistics.mean(list(waagen[w[0]]['stack'])[:-4])

                if act_distance_stdev<50: act_distance_stdev=50 #to avoid too small std deviations
                act_touched = 1 if abs(act_distance_avg_new - act_distance_avg_old) > act_distance_stdev*10 else 0
                
                if waagen[w[0]]['touched'] != act_touched:
                    logger.info(f"touched changed to {act_touched} for i2c address 0x{i2c_address:02X} mac {waagen[w[0]]['mac']}: New: {act_distance_avg_new:.1f} Diff: {(act_distance_avg_new-act_distance_avg_old):.1f} Std: {act_distance_stdev:.1f}")
                    client.publish(f"homie/{mqtt_client_name}/scales/{waagen[w[0]]['mac']}/touched", act_touched, qos=0, retain=False)
                    waagen[w[0]]['touched'] = act_touched
                    waagen[w[0]]['last_touched_time'] = time.time()

                    if not shop_status in (6,18,): #not during scale products assignment state
                        if act_touched == 1:
                            send_and_recv(f"w{i2c_address:02X}03")
                        else:
                            send_and_recv(f"w{i2c_address:02X}02")
            # check for touch functionality end
            #######################################################################

        else:
            logger.warning(f"Fehler beim Lesen, Anzahl der gelesenen Bytes ist nicht 4. I2C address 0x{i2c_address:02X}, return: {res}")
        
        if state_okay != waagen[w[0]]['state']:
            client.publish(f"homie/{mqtt_client_name}/scales/{waagen[w[0]]['mac']}/state", state_okay, qos=0, retain=True)
            waagen[w[0]]['state'] = state_okay

    time.sleep(0.1)


client.loop_stop()
client.disconnect()

ser.close()

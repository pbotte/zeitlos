#!/usr/bin/python3

import time
import can
import json
import paho.mqtt.client as paho
import logging, argparse
import traceback
import re
import sys

logging.basicConfig(format="%(asctime)-15s %(levelname)-8s  %(message)s")
logger = logging.getLogger("Shelf-Controller")

parser = argparse.ArgumentParser(description='CANbus Regal-Controller.')
parser.add_argument("-v", "--verbosity", help="increase output verbosity", default=0, action="count")
parser.add_argument("-b", "--mqtt-broker-host", help="MQTT broker hostname", default="localhost")
parser.add_argument("-c", "--channel", help="Channel name, eg can0", type=str, default="can0")
parser.add_argument("-i", "--interface", help="Interface name, eg socketcan", type=str, default="socketcan")
parser.add_argument("--bitrate", help="Bitrate to use for the CAN bus.", type=int, default=125000)
parser.add_argument("mqtt_client_name", help="MQTT client name. Needs to be unique in the MQTT namespace, eg shelf01.", type=str)
args = parser.parse_args()
logger.setLevel(logging.WARNING-(args.verbosity*10 if args.verbosity <=2 else 20) )


def on_connect(client, userdata, flags, rc):
  if rc==0:
    logger.info("MQTT connected OK. Return code "+str(rc) )
    client.subscribe("homie/"+args.mqtt_client_name+"/#")
    logger.info("MQTT: Success, subscribed to all topics")
  else:
    logger.error("Bad connection. Return code="+str(rc))

def on_disconnect(client, userdata, rc):
  if rc != 0:
    logger.warning("Unexpected MQTT disconnection. Will auto-reconnect")

def on_message(client, userdata, message):
  try:
    m = message.payload.decode("utf-8")
    logger.debug("received:"+str(m)+" "+message.topic)
    msplit = re.split("/", message.topic)

    #write
    #mosquitto_pub -t 'homie/shelf01/7B87/scale_product_details_line1/set' -m hallohallohallohallohallohallohallohallohallohallohallo
    if len(msplit) == 5 and msplit[4].lower() == "set" and int(msplit[2],16) in range(0xffff+1):
      scale_id = int(msplit[2],16)
      logger.debug("Message accepted")
      #eg: homie/shelf01/0315/scale_product_description/set
      act_pos = 0
      can_msg_len = 6 #only the data portion. if data len>6 -> multiple messages
      mcu_eeprom_data_dict = {"scale_product_description":{"len":50,"start":0xa},
        "scale_product_details_line1": {"len":50,"start":0x3c},
        "scale_product_details_line2": {"len":50,"start":0x6e} }
      if msplit[3].lower() in mcu_eeprom_data_dict:
        #send CAN bus message to 0x0006.... (....=scale id) with [length0], [length1], [bytes...]
        mem_pos_start = mcu_eeprom_data_dict[msplit[3].lower()]["start"]  #start memory address in MCU, eg 0x0a for scale_product_description
        data_str = str(m) #prepare string to be submitted
        data_str = [ord(i) for i in list(data_str)]
        data_str = data_str[0:mcu_eeprom_data_dict[msplit[3].lower()]["len"]] +[0] #limit length  + terminating 0x0
        while act_pos < len(data_str):
          #write 6 bytes to scale eeprom
          msg = can.Message(arbitration_id=0x00070000+scale_id, data=[(mem_pos_start+act_pos)&0xff,((mem_pos_start+act_pos)&0xff00)>>8]+data_str[act_pos:act_pos+can_msg_len], is_extended_id=True)
          bus.send(msg)
          time.sleep(0.001) # wait for message to be send
          act_pos += can_msg_len

    #read
    #mosquitto_pub -t 'homie/shelf01/7B87/scale_product_details_line1/get' -m 0
    if len(msplit) == 5 and msplit[4].lower() == "get" and int(msplit[2],16) in range(0xffff+1):
      scale_id = int(msplit[2],16)
      logger.debug("Message accepted")
      #eg: homie/shelf01/0315/scale_product_description/set
      act_pos = 0
      can_msg_len = 8 #if data len>8 -> multiple messages
      mcu_eeprom_data_dict = {"scale_product_description":{"len":50,"start":0xa},
        "scale_product_details_line1": {"len":50,"start":0x3c},
        "scale_product_details_line2": {"len":50,"start":0x6e} }
      if msplit[3].lower() in mcu_eeprom_data_dict:
        #send CAN bus message to 0x0006.... (....=scale id) with [length0], [length1], [bytes...]
        mem_pos_start = mcu_eeprom_data_dict[msplit[3].lower()]["start"]  #start memory address in MCU, eg 0x0a for scale_product_description
        while act_pos < mcu_eeprom_data_dict[msplit[3].lower()]["len"]:
          #write 3 bytes to bus to request data
          if act_pos+can_msg_len > mcu_eeprom_data_dict[msplit[3].lower()]["len"]:
            can_msg_len = mcu_eeprom_data_dict[msplit[3].lower()]["len"] - act_pos
          msg = can.Message(arbitration_id=0x00060000+scale_id, 
            data=[(mem_pos_start+act_pos)&0xff,((mem_pos_start+act_pos)&0xff00)>>8, can_msg_len], 
            is_extended_id=True)
          bus.send(msg)
          time.sleep(0.01) # wait for message to be send
          act_pos += can_msg_len



  except Exception as err:
    traceback.print_tb(err.__traceback__)

#open can bus
bus = can.interface.Bus(channel=args.channel, bustype=args.interface, bitrate=args.bitrate)
#connect to MQTT broker
client= paho.Client(args.mqtt_client_name)

debug = True if args.verbosity>1 else False

client.on_message=on_message
client.on_connect = on_connect
client.on_disconnect = on_disconnect
client.enable_logger(logger) #info: https://www.eclipse.org/paho/clients/python/docs/#callbacks
logger.info("connecting to broker: "+args.mqtt_broker_host+". If it fails, check whether the broker is reachable. Check the -b option.")
client.connect(args.mqtt_broker_host)
client.loop_start() #start loop to process received messages in separate thread
logger.debug("MQTT Loop started.")

loop_variable = True
while loop_variable:

  message = bus.recv()
  #client.publish("homie/"+args.mqtt_client_name+"/3320/product-description", "Äpfel", qos=1, retain=True)
  #print(message)

  #if args.verbosity>0:
  #  time.sleep(1-time.time() % 1) #every second, even if the processing before took longer
  #else:
  time.sleep(0.025)
  

client.loop_stop()
client.disconnect()

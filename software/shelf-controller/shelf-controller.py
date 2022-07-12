#!/usr/bin/python3

import time
import can
import json
import paho.mqtt.client as paho
import logging, argparse
import traceback
import re
import sys
import struct

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


mcu_eeprom_data_dict_float = {"scale_product_mass_per_unit":{"start":0xcc},
        "scale_calibration_slope": {"start":0xd0} }
mcu_eeprom_data_dict_long = {
        "scale_calibration_zero_in_raw": {"start":0xd4} }
mcu_eeprom_data_dict_str = {"scale_product_description":{"len":50,"start":0xa},
        "scale_product_details_line1": {"len":50,"start":0x3c},
        "scale_product_details_line2": {"len":50,"start":0x6e} }

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

    #reset all scales: cansend can0 11000000#42fabeef
    # mosquitto_pub -m 0 -t homie/shelf01/reset-all
    if len(msplit) == 3 and msplit[2].lower() == "reset-all":
      msg = can.Message(arbitration_id=0x11000000, data=[0x42,0xfa,0xbe,0xef], is_extended_id=True)
      bus.send(msg)
    #send continously can msg off / on: cansend can0 12000000# | cansend can0 13000000#
    # mosquitto_pub -m 0 -t homie/shelf01/can-off-all
    if len(msplit) == 3 and msplit[2].lower() == "can-off-all":
      msg = can.Message(arbitration_id=0x12000000, data=[], is_extended_id=True)
      bus.send(msg)
    # mosquitto_pub -m 0 -t homie/shelf01/can-on-all
    if len(msplit) == 3 and msplit[2].lower() == "can-on-all":
      msg = can.Message(arbitration_id=0x13000000, data=[], is_extended_id=True)
      bus.send(msg)

    #reset individual scale
    # cansend can0 00007b87#42fabeef
    # mosquitto_pub -m 0 -t homie/shelf01/7b87/reset
    # To update firmware via CAN: pio run && npx mcp-can-boot-flash-app -p m1284p -m 0x3320 -f .pio/build/atmega1284p/firmware.hex -R 00003320#42fabeef
    if len(msplit) == 4 and msplit[3].lower() == "reset":
      scale_id = int(msplit[2],16)
      msg = can.Message(arbitration_id=0x0+scale_id, data=[0x42,0xfa,0xbe,0xef], is_extended_id=True)
      bus.send(msg)

    #retrieve individual scale
    # cansend can0 00063320#
    if len(msplit) == 4 and msplit[3].lower() == "retrieve":
      scale_id = int(msplit[2],16)
      msg = can.Message(arbitration_id=0x60000+scale_id, data=[], is_extended_id=True)
      bus.send(msg)

    #write float
    if len(msplit) == 5 and msplit[4].lower() == "set" and int(msplit[2],16) in range(0xffff+1):
      scale_id = int(msplit[2],16)
      #eg: homie/shelf01/0315/scale_product_mass_per_unit/set
      act_pos = 0
      can_msg_len = 4 #because float has 4 bytes
      if msplit[3].lower() in mcu_eeprom_data_dict_float:
        #send CAN bus message to 0x0006.... (....=scale id) with [length0], [length1], [bytes...]
        mem_pos_start = mcu_eeprom_data_dict_float[msplit[3].lower()]["start"]  #start memory address in MCU, eg 0x0a for scale_product_description
        hex_str=struct.pack('<f', float(m))
        data_str = [i for i in hex_str]
        data_str = [mem_pos_start&0xff, (mem_pos_start>>8)] + data_str # add first to bytes, where to store in eeprom
        #write 6 bytes to scale eeprom
        msg = can.Message(arbitration_id=0x00070000+scale_id, data=data_str, is_extended_id=True)
        bus.send(msg)



    #write string
    #mosquitto_pub -t 'homie/shelf01/7B87/scale_product_details_line1/set' -m hallohallohallohallohallohallohallohallohallohallohallo
    if len(msplit) == 5 and msplit[4].lower() == "set" and int(msplit[2],16) in range(0xffff+1):
      scale_id = int(msplit[2],16)
      #eg: homie/shelf01/0315/scale_product_description/set
      act_pos = 0
      can_msg_len = 6 #only the data portion. if data len>6 -> multiple messages
      if msplit[3].lower() in mcu_eeprom_data_dict:
        #send CAN bus message to 0x0006.... (....=scale id) with [length0], [length1], [bytes...]
        mem_pos_start = mcu_eeprom_data_dict_str[msplit[3].lower()]["start"]  #start memory address in MCU, eg 0x0a for scale_product_description
        data_str = str(m) #prepare string to be submitted
        data_str = [ord(i) for i in list(data_str)]
        data_str = data_str[0:mcu_eeprom_data_dict_str[msplit[3].lower()]["len"]] +[0] #limit length  + terminating 0x0
        while act_pos < len(data_str):
          #write 6 bytes to scale eeprom
          msg = can.Message(arbitration_id=0x00070000+scale_id, data=[(mem_pos_start+act_pos)&0xff,((mem_pos_start+act_pos)&0xff00)>>8]+data_str[act_pos:act_pos+can_msg_len], is_extended_id=True)
          bus.send(msg)
          time.sleep(0.001) # wait for message to be send
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
eeprom_storage = [None] * 256
while loop_variable:

  message = bus.recv()
  logger.debug("CAN received: {}".format(message))

  if ( (message.arbitration_id>>16) & 0xff) == 9:
    sender_id = (message.arbitration_id&0xffff)
    eeprom_pos = (message.data[1]<<8) + message.data[0]
#    logger.debug("sender id: {} eeprom_pos: {}".format(sender_id, eeprom_pos) )
    for i in range(6):
      if eeprom_pos+i < 256: #currently only the lower bytes in eeprom are supported. This can later be extended
        eeprom_storage[eeprom_pos+i] = message.data[2+i]
#    logger.debug("{}".format(eeprom_storage))
    if eeprom_pos> 250: #when last message is send from MCU
      client.publish("homie/"+args.mqtt_client_name+"/{:02x}/eeprom".format(sender_id), "{}".format(eeprom_storage), qos=1, retain=False)
      for i in mcu_eeprom_data_dict_float:
        start_address = mcu_eeprom_data_dict_float[i]["start"]
        logger.debug("{}: {} {} {} ".format(i, start_address, eeprom_storage[start_address:start_address+4], struct.unpack('<f',bytes(eeprom_storage[start_address:start_address+4] ))[0]  ))
      for i in mcu_eeprom_data_dict_long:
        start_address = mcu_eeprom_data_dict_long[i]["start"]
        logger.debug("{}: {} {} {} ".format(i, start_address, eeprom_storage[start_address:start_address+4], struct.unpack('<l',bytes(eeprom_storage[start_address:start_address+4] ))[0]  ))


#  if args.verbosity>0:
  #  time.sleep(1-time.time() % 1) #every second, even if the processing before took longer
  #else:
#    time.sleep(0.025)


client.loop_stop()
client.disconnect()

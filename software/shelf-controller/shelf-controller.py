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
        "scale_calibration_slope": {"start":0xd0},
        "scale_product_price_per_unit": {"start":0xd8} }
mcu_eeprom_data_dict_sgn_long = {
        "scale_calibration_zero_in_raw": {"start":0xd4} }
mcu_eeprom_data_dict_str = {"scale_product_description":{"len":50,"start":0xa},
        "scale_product_details_line1": {"len":50,"start":0x3c},
        "scale_product_details_line2": {"len":50,"start":0x6e} }

def on_connect(client, userdata, flags, rc):
  if rc==0:
    logger.info("MQTT connected OK. Return code "+str(rc) )
    client.subscribe("homie/"+args.mqtt_client_name+"/#")
    client.subscribe("homie/shop_controller/prepare_for_next_customer")
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

    # mosquitto_pub -n -t homie/shop_controller/prepare_for_next_customer
    # message from shop_controller to all scales to become ready for next customer
    # eg reset units withdrawn
    if len(msplit) == 3 and msplit[1].lower() == "shop_controller" and msplit[2].lower() == "prepare_for_next_customer":
      msg = can.Message(arbitration_id=0x14000000, data=[], is_extended_id=True)
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

    #Set raw Zero calibration individual scale
    # cansend can0 00093320#
    if len(msplit) == 4 and msplit[3].lower() == "zero-raw-to-act-reading":
      scale_id = int(msplit[2],16)
      msg = can.Message(arbitration_id=0x90000+scale_id, data=[], is_extended_id=True)
      bus.send(msg)

    #Set slope calibration individual scale
    if len(msplit) == 4 and msplit[3].lower() == "set-slope-to-act-reading":
      scale_id = int(msplit[2],16)
      msg = can.Message(arbitration_id=0xb0000+scale_id, data=[], is_extended_id=True)
      bus.send(msg)

    #write long
    if len(msplit) == 5 and msplit[4].lower() == "set" and int(msplit[2],16) in range(0xffff+1):
      scale_id = int(msplit[2],16)
      #eg: homie/shelf01/0315/scale_calibration_zero_in_raw/set
      act_pos = 0
      can_msg_len = 4 #because long has 4 bytes
      if msplit[3].lower() in mcu_eeprom_data_dict_sgn_long:
        #send CAN bus message to 0x0006.... (....=scale id) with [length0], [length1], [bytes...]
        mem_pos_start = mcu_eeprom_data_dict_sgn_long[msplit[3].lower()]["start"]  #start memory address in MCU, eg 0x0a for scale_product_description
        hex_str=struct.pack('<l', int(m)) #parameters see: https://docs.python.org/3/library/struct.html
        data_str = [i for i in hex_str]
        data_str = [mem_pos_start&0xff, (mem_pos_start>>8)] + data_str # add first to bytes, where to store in eeprom
        #write 6 bytes to scale eeprom
        msg = can.Message(arbitration_id=0x00070000+scale_id, data=data_str, is_extended_id=True)
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
      if msplit[3].lower() in mcu_eeprom_data_dict_str:
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
  msg_handeled = False
  logger.debug("CAN received: {}".format(message))

  if debug: client.publish("homie/"+args.mqtt_client_name+"/can-messages", "{}".format(message), qos=0, retain=False)

  cmd_id = (message.arbitration_id>>16) & 0xff
  if cmd_id == 2:
    sender_id = (message.arbitration_id&0xffff)
    firmware_version = struct.unpack('<L',message.data[0:4])[0]
    hardware_version = message.data[4]
    logger.info("Firmware version: {}  Hardware version: {}".format(firmware_version, hardware_version) )
    client.publish("homie/"+args.mqtt_client_name+"/{:02x}/firmware_version".format(sender_id), "{}".format(firmware_version), qos=1, retain=True)
    client.publish("homie/"+args.mqtt_client_name+"/{:02x}/hardware_version".format(sender_id), "{}".format(hardware_version), qos=1, retain=True)
    msg_handeled = True

  if cmd_id == 3:
    sender_id = (message.arbitration_id&0xffff)
    data = struct.unpack('<l',message.data)[0]
    logger.info("Averaged Reading: {} {}".format(message.data, data ) )
    client.publish("homie/"+args.mqtt_client_name+"/{:02x}/reading_avg".format(sender_id), "{}".format( data ), qos=1, retain=False)
    msg_handeled = True

  if cmd_id == 0xa:
    sender_id = (message.arbitration_id&0xffff)
    data = struct.unpack('<f',message.data)[0]
    logger.info("Mass in kg: {} {}".format(message.data, data ) )
    client.publish("homie/"+args.mqtt_client_name+"/{:02x}/mass_kg".format(sender_id), "{}".format( data ), qos=1, retain=False)
    msg_handeled = True

  if cmd_id == 0xb:
    sender_id = (message.arbitration_id&0xffff)
    data = struct.unpack('<h',message.data)[0] #integer with 2 bytes
    logger.info("Withdrawal units: {} {}".format(message.data, data ) )
    client.publish("homie/"+args.mqtt_client_name+"/{:02x}/withdrawal_units".format(sender_id), "{}".format( data ), qos=1, retain=True)
    msg_handeled = True

  if cmd_id == 4:
    sender_id = (message.arbitration_id&0xffff)
    data = struct.unpack('<f',message.data)[0]
    logger.info("Temperature: {} {}".format(message.data, data ) )
    client.publish("homie/"+args.mqtt_client_name+"/{:02x}/temperature".format(sender_id), "{}".format( data ), qos=1, retain=False)
    msg_handeled = True

  if cmd_id == 9:
    sender_id = (message.arbitration_id&0xffff)
    eeprom_pos = (message.data[1]<<8) + message.data[0]
    for i in range(6):
      if eeprom_pos+i < 256: #currently only the lower bytes in eeprom are supported. This can later be extended
        eeprom_storage[eeprom_pos+i] = message.data[2+i]
    if eeprom_pos> 250: #when last message is send from MCU
      logger.debug("{}".format(eeprom_storage))
#      client.publish("homie/"+args.mqtt_client_name+"/{:02x}/eeprom".format(sender_id), "{}".format(eeprom_storage), qos=1, retain=False)
      for i in mcu_eeprom_data_dict_float:
        start_address = mcu_eeprom_data_dict_float[i]["start"]
        logger.info("{}: {} {} ".format(i, eeprom_storage[start_address:start_address+4], struct.unpack('<f',bytes(eeprom_storage[start_address:start_address+4] ))[0]  ))
        client.publish("homie/"+args.mqtt_client_name+"/{:02x}/{}".format(sender_id, i), "{}".format(struct.unpack('<f',bytes(eeprom_storage[start_address:start_address+4] ))[0]), qos=1, retain=True)
      for i in mcu_eeprom_data_dict_sgn_long:
        start_address = mcu_eeprom_data_dict_sgn_long[i]["start"]
        data = struct.unpack('<l',bytes(eeprom_storage[start_address:start_address+4] ))[0]
        logger.info("{}: {} {} ".format(i, eeprom_storage[start_address:start_address+4], data  ))
        client.publish("homie/"+args.mqtt_client_name+"/{:02x}/{}".format(sender_id, i), "{}".format(data), qos=1, retain=True)
      for i in mcu_eeprom_data_dict_str:
        start_address = mcu_eeprom_data_dict_str[i]["start"]
        data_length = mcu_eeprom_data_dict_str[i]["len"]
        data = eeprom_storage[start_address:start_address+data_length]
        data_concat = []
        for l in data:
          if l == 0: break #stop with 0x0 as delimiter
          data_concat.append(chr(l))
        data_concat = ''.join(data_concat)
        logger.info("{}: {}".format(i, data_concat) )
        client.publish("homie/"+args.mqtt_client_name+"/{:02x}/{}".format(sender_id, i), "{}".format(data_concat), qos=1, retain=True)
    msg_handeled = True

  if not msg_handeled:
    logger.info("Unhandeled CAN received: {}".format(message))


#  if args.verbosity>0:
  #  time.sleep(1-time.time() % 1) #every second, even if the processing before took longer
#  else:
  time.sleep(0.0001)


client.loop_stop()
client.disconnect()

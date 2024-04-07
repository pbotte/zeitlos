#!/usr/bin/env python3

# details about the sensor:
# https://www.waveshare.com/wiki/TOF_Laser_Range_Sensor

import json
import time
import serial
import paho.mqtt.client as paho
import argparse
import logging
import struct
import os, re
import socket
import collections, statistics


logging.basicConfig(
    level=logging.WARNING, format="%(asctime)-6s %(levelname)-8s  %(message)s"
)
logger = logging.getLogger("Waveshare 18301 TOF Laser Range Sensor (VL53L1) readout")

parser = argparse.ArgumentParser(description="MQTT Waveshare 18301 readout (VL53L1)")
parser.add_argument("-v", "--verbosity", help="increase output verbosity", default=0, action="count")
parser.add_argument("-r", "--send-raw-data", help="send every data packat via mqtt", default=0, action="count")
parser.add_argument("-b", "--mqtt-broker-host", help="MQTT broker hostname. default=localhost", default="localhost")
parser.add_argument("-p", "--mqtt-broker-port", default=1883, type=int)
parser.add_argument("-t", "--watchdog-timeout", help="timeout in seconds for the watchdog. default=10 sec", default=10, type=int)
parser.add_argument("serial_device_name", help="Serial port used, eg /dev/ttyUSB0", type=str)
args = parser.parse_args()
logger.setLevel(logging.WARNING - (args.verbosity * 10 if args.verbosity <= 2 else 20))

#get usb path of device
usb_path_device = "unknown"
last_dev = os.popen(f'udevadm info /{args.serial_device_name} | grep DEVLINKS').read()
regex = r"-usb-[0-9:\.]+-port0"
matches = re.finditer(regex, last_dev, re.MULTILINE)
for matchnum, match in enumerate(matches): #only one match should be found
  s=match.group()
  usb_path_device = s.replace(":","-").replace("-usb-","").replace("-port0","")
mqtt_client_name = f"tracker-{socket.gethostname()}-{usb_path_device}"



logger.info("MQTT client name: " + mqtt_client_name)
logger.info("Watchdog timeout (seconds): " + str(args.watchdog_timeout))
logger.info("Use the following Serial-Device: " + str(args.serial_device_name))


def on_connect(client, userdata, flags, rc):
    if rc == 0:
        logger.info("MQTT connected OK. Return code" + str(rc))
    else:
        logger.error("Bad connection. Return code=" + str(rc))


def on_disconnect(client, userdata, rc):
    if rc != 0:
        logger.warning("Unexpected MQTT disconnection. Will auto-reconnect")


client = paho.Client(paho.CallbackAPIVersion.VERSION1, mqtt_client_name)
client.on_connect = on_connect
client.on_disconnect = on_disconnect
client.enable_logger(logger)
logger.info("Conncting to broker " + args.mqtt_broker_host)
client.will_set(
    topic="homie/" + mqtt_client_name + "/state",
    payload="0",
    qos=1,
    retain=True,
)
client.connect(args.mqtt_broker_host, keepalive=60, port=args.mqtt_broker_port)
client.publish(
    topic="homie/" + mqtt_client_name + "/state",
    payload="1",
    qos=1,
    retain=True,
)
client.loop_start()
logger.info("MQTT loop started.")

ser = serial.Serial(args.serial_device_name, 115200, timeout=0.1)


##########

number_sensors = 8
sensor_duration_read_ms = 120 #it takes 120ms from one read to the next
sensor_time_for_request_ms = 5 #at takes roughly 0.1ms from request to answer. Add some savety on top...
time_interval_search_for_new_sensors = 5 # in seconds

sensor_act_state = [0]*number_sensors       # states: 0=init, 1=request, 2=waiting for answer, 3=problematic read out
sensor_last_read_time = [0]*number_sensors
sensor_last_data_time = [0]*number_sensors
time_last_bus_access = 0 #to ensure no overlapp of multiple writes/reads

last_sensor_data = [None]*number_sensors
last_sensor_data_averaged = [None]*number_sensors
last_sensor_data_averaged_sigma = [None]*number_sensors

readings_stack = [collections.deque(maxlen=8) for i in range(number_sensors)] #8 Hz reading rate makes depth of 1sec

next_sensor_id_to_poll_in_free_time = 0
time_start = time.time()
time_last_data_submit_raw = time_start # avoid to send data right at from the start
time_last_data_submit = time_start # avoid to send data right at from the start

###########

WatchDogCounter = args.watchdog_timeout * 1000 # to convert from sec to msec

while WatchDogCounter > 0:
  my_time = time.time()
  if (my_time - time_last_bus_access)*1000 > 5: # min distanace between read requests to avoid overlap read/write
    ActSensorID = -1
    c=0
    #schedule sensor which SHOULD have new data, because readout is some time ago (sensor_duration_read_ms)
    while ActSensorID<0 and c<number_sensors:
      if (my_time-sensor_last_read_time[c])*1000 > sensor_duration_read_ms: # wait time since last read
        ActSensorID = c
      c+=1

    #No sensor scheduled? Try some others, maybe they are back
    c=0
    while ActSensorID <0 and c<number_sensors:
      if sensor_act_state[next_sensor_id_to_poll_in_free_time] >= 2: #still waiting for data (2) or problemtic data (3)
        ActSensorID = next_sensor_id_to_poll_in_free_time
      next_sensor_id_to_poll_in_free_time += 1
      if next_sensor_id_to_poll_in_free_time >= number_sensors: next_sensor_id_to_poll_in_free_time=0
      c+=1

    if ActSensorID >= 0:
      sensor_act_state[ActSensorID] = 1
      sensor_last_read_time[ActSensorID] = my_time + time_interval_search_for_new_sensors # Relevant for check for new sensors. This get's overritten, once a reply comes

      a = b'\x57\x10\xFF\xFF'+ActSensorID.to_bytes(1, 'big')+b'\xFF\xFF'+(0x63+ActSensorID).to_bytes(1, 'big')
      ser.write(a)
      time_last_bus_access = time.time()
      logger.debug(f"Write at {(my_time-time_start)*1000:08f} {ActSensorID}")
      sensor_act_state[ActSensorID] = 2

  if ser.inWaiting() > 0:
    b = ser.read(16)
    my_time_read = time.time()

    if b[0]==0x57 and b[1]==0x0:
      id = b[3]
      system_time = struct.unpack('<l',bytes(b[4:8]))[0]
      distance = struct.unpack('<l',bytes(b[8:11]+b'\0'))[0] #uint24 to uint32 conversion first
      status = b[11] # 0=valid measurement, all others: invalid data
      signal_strength = struct.unpack('<H',bytes(b[12:14]))[0]
      checksum = b[15]

      logger.debug(f"Read at {(my_time_read-time_start)*1000:08f} after {(my_time_read-my_time)*1000:08f} {id}\t{distance}\t{status}")
      sensor_act_state[id] = 0
      sensor_last_read_time[id] = my_time_read
      if status in (0,2): #submit. 0:success or 2:low signal strength
        WatchDogCounter = args.watchdog_timeout*1000 #to convert from sec to ms
        last_sensor_data[id] = distance
        sensor_last_data_time[id] = my_time_read
        if status != 0:
          logger.info(f"Problematic read: {id} {system_time} {distance} {status} {signal_strength} {checksum}")
      else:
        #answer, but problematic
        sensor_act_state[id] = 3
        if status != 255: # status = 0xff when updating the new data to readout buffer. Normal procedure
          logger.warning(f"Problematic read: {id} {system_time} {distance} {status} {signal_strength} {checksum}")

  my_time = time.time()
  if (my_time-time_last_data_submit_raw)*1000 > 125:
    #clear data from sensors no longer connected / working
    for i in range(number_sensors):
      if last_sensor_data[i]:
        if (my_time-sensor_last_data_time[i])*1000 > 300:
          last_sensor_data[i] = None
          logger.warning(f"Sensor {i} did not deliver data in the last 300ms.")

    #do statistics for averaging
    for k,v in enumerate(last_sensor_data):
      if v:
        readings_stack[k].append(v)
      else:
        if (len(readings_stack[k])>0): #some reading has to be in the stack
          readings_stack[k].pop() #simply delete one entry

    #send raw data
    if args.send_raw_data > 0: #only
      client.publish('homie/'+mqtt_client_name+'/tof/actreading_raw', json.dumps(last_sensor_data), qos=0, retain=False)
    logger.info(f"act reading: {json.dumps(last_sensor_data)}")
    time_last_data_submit_raw = time.time()

  #send averaged data
  if (my_time-time_last_data_submit)*1000 > 950: # approx every second
    for k,v in enumerate(last_sensor_data):
      if (len(readings_stack[k])>2): #some reading has to be in the stack
        last_sensor_data_averaged[k] = round(statistics.mean(list(readings_stack[k])))
        last_sensor_data_averaged_sigma[k] = statistics.stdev(list(readings_stack[k]))
      else:
        last_sensor_data_averaged[k] = None
        last_sensor_data_averaged_sigma[k] = None
    client.publish('homie/'+mqtt_client_name+'/tof/actreading', json.dumps(last_sensor_data_averaged), qos=0, retain=False)
    client.publish('homie/'+mqtt_client_name+'/tof/actreading_sigma', json.dumps(last_sensor_data_averaged_sigma), qos=0, retain=False)
    time_last_data_submit = time.time()

  WatchDogCounter -= 1
  time.sleep(.001)



# Programm beenden
ser.close()

client.loop_stop()
client.disconnect()
logger.info("Programm stopped.")

import ubinascii
from umqtt.simple import MQTTClient
import myconfig
import machine
import json

CLIENT_UID = ubinascii.hexlify(machine.unique_id()).decode()

mqtt_connected = False
mqtt_queue = None

assigned_scaleid = None #data comming von file
assigned_product_id = None #data comming von file
assigned_product_hash = None #data comming von file

via_mqtt_received_scaleid = None
via_mqtt_received_productid = None
via_mqtt_received_hash = None

def report_status(publish_dict):
    print(f"{assigned_scaleid=} {assigned_product_id=} {assigned_product_hash=} {via_mqtt_received_productid=} {via_mqtt_received_hash=}")
    print('report_status(): '+json.dumps(publish_dict))
    if mqtt_connected:
        try:
            for k,v in publish_dict.items():
              client.publish(myconfig.mqtt_topic_pub_config+"/"+k, str(v), retain=True)
        except:
            print("Error when publishing MQTT data.")

#####################################

def reset_queue():
    global mqtt_queue
    mqtt_queue = None

def sub_cb(topic, msg):
    global servo_angle
    global mqtt_queue
    global via_mqtt_received_productid
    global via_mqtt_received_hash
    global via_mqtt_received_scaleid
    topic = topic.decode('utf-8')
    msg = msg.decode('utf-8')
    print(f"New MQTT message ({topic}): {msg}")
    if topic == myconfig.mqtt_topic_refreshall:
        mqtt_queue = 1 #process this in main loop
    if topic == myconfig.mqtt_topic_sub_scaleid+assigned_scaleid:
        print("productid via mqtt received")
        try:
          via_mqtt_received_productid = int(msg)
        except:
          via_mqtt_received_productid = None
        print(f"     --> {via_mqtt_received_productid=}")
    if topic == myconfig.mqtt_topic_sub_set_scaleid:
        print("scaleid via mqtt received")
        via_mqtt_received_scaleid = msg
        

# run this in the main loop
def mqtt_keep_checking():
    global mqtt_connected
    if not mqtt_connected:
        return
    try:
#        client.subscribe(myconfig.mqtt_topic_pub)
        client.check_msg() #important to call on a regular basis to empty incoming network buffers
                           # if not called often enough, no network communication (incl ICMP) will stop
    except OSError as e:
        mqtt_connected = False
        print("mqtt check_msg failed.")

# run this from time to time to check whether a connection really exists
def mqtt_isconnected():
    global mqtt_connected
    if not mqtt_connected:
        return
    try:
        client.ping()
    except OSError as e:
        mqtt_connected = False
        print("\nlost connection to mqtt broker...")
    #    reconnect()


def reconnect_MQTT(scaleid, productid):
    global mqtt_connected
    if not mqtt_connected:
        try:
            print("No MQTT connection. Will (re)connect...")
            client.set_last_will(myconfig.mqtt_topic_last_will, "0", retain=True)
            client.set_callback(sub_cb)
            client.connect()
            client.subscribe(myconfig.mqtt_topic_pub_config)
            client.subscribe(myconfig.mqtt_topic_refreshall)
            if scaleid:
              client.subscribe(myconfig.mqtt_topic_sub_scaleid+scaleid)
            client.subscribe(myconfig.mqtt_topic_sub_set_scaleid)
            if productid:
              client.subscribe(f"{myconfig.mqtt_topic_sub_producthash}{productid}/hash")

            mqtt_connected = True
            print('Connected to ',myconfig.mqtt_server,' MQTT Broker, as client: ', myconfig.mqtt_clientname)

            # submit two messages for the first time, after that only on signal edge or timer
            client.publish(myconfig.mqtt_topic_last_will, "1", retain=True)
        except OSError as e:
            print("Could not connect to MQTT Broker.")





client = MQTTClient(myconfig.mqtt_client_id_base_str+str(CLIENT_UID), myconfig.mqtt_server, keepalive=60, port=myconfig.mqtt_port)

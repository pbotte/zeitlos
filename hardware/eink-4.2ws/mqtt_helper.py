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

def report_status():
    publish_dict = {'scaleid': assigned_scaleid,
                    'productid': assigned_product_id,
                    'product_hash': assigned_product_hash}
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
    global mqtt_queue
    global via_mqtt_received_productid
    global via_mqtt_received_hash
    global via_mqtt_received_scaleid
    topic = topic.decode('utf-8')
    msg = msg.decode('utf-8')
    print(f"MQTT message ({topic}): {msg}")
    if topic == myconfig.mqtt_topic_refreshall:
        mqtt_queue = 1 #process this in main loop
    elif topic == myconfig.mqtt_topic_sub_scaleid+assigned_scaleid:
        print("productid via mqtt received")
        via_mqtt_received_productid = msg
        print(f"     --> {via_mqtt_received_productid=}")
    elif topic == myconfig.mqtt_topic_sub_set_scaleid:
        print("scaleid via mqtt received")
        via_mqtt_received_scaleid = msg
        mqtt_queue = 2 #process this in main loop
    elif topic == f"{myconfig.mqtt_topic_sub_producthash}{assigned_product_id}/hash":
        print("hash received")
        via_mqtt_received_hash = msg
    elif topic == f"{myconfig.mqtt_topic_sub_producthash}{via_mqtt_received_productid}/hash":
        print("hash received")
        via_mqtt_received_hash = msg
        

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


def reconnect_MQTT():
    global mqtt_connected
    if not mqtt_connected:
        try:
            print("No MQTT connection. Will (re)connect...")
            client.set_last_will(myconfig.mqtt_topic_last_will, "0", retain=True)
            client.set_callback(sub_cb)
            client.connect()
            topics = [myconfig.mqtt_topic_pub_config, myconfig.mqtt_topic_refreshall,
                      myconfig.mqtt_topic_sub_set_scaleid]
            if assigned_scaleid:
                topics.append(myconfig.mqtt_topic_sub_scaleid+assigned_scaleid)
            if via_mqtt_received_productid:
                print("Connect to MQTT broker with via_mqtt_received_productid")
                topics.append(f"{myconfig.mqtt_topic_sub_producthash}{via_mqtt_received_productid}/hash")
            elif assigned_product_id:
                print("Connect to MQTT broker with assigned_product_id")
                topics.append(f"{myconfig.mqtt_topic_sub_producthash}{assigned_product_id}/hash")
              
            print("  subscribe to these topics:")
            for v in topics:
                print(f'  - {v}')
                client.subscribe(v)

            mqtt_connected = True
            print('Connected to ',myconfig.mqtt_server,' MQTT Broker, as client: ', myconfig.mqtt_clientname)

            # submit two messages for the first time, after that only on signal edge or timer
            client.publish(myconfig.mqtt_topic_last_will, "1", retain=True)
        except OSError as e:
            print("Could not connect to MQTT Broker.")


#this is mainly needed to unsubscribe von topics
def disconnect():
    global mqtt_connected
    if mqtt_connected:
        client.disconnect()
        print("MQTT disconnected")
        mqtt_connected = False



client = MQTTClient(myconfig.mqtt_client_id_base_str+str(CLIENT_UID), myconfig.mqtt_server, keepalive=60, port=myconfig.mqtt_port)

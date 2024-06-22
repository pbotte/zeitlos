mqtt_server = '192.168.178.242'
mqtt_port = 1883
mqtt_client_id_base_str = 'eink'

wlan_SSID = "Hamilton"
wlan_password = "NeuerNachwuchs2017"



import ubinascii
import machine
CLIENT_UID = ubinascii.hexlify(machine.unique_id()).decode()

mqtt_clientname = mqtt_client_id_base_str+str(CLIENT_UID)

mqtt_topic_last_will = mqtt_clientname+'/state'
mqtt_topic_pub_config = mqtt_clientname+'/config'
mqtt_topic_sub_scaleid = 'homie/shop_controller/shop_overview/scales_products/'
#to cover: homie/shop_controller/shop_overview/products/1/hash
mqtt_topic_sub_producthash = 'homie/shop_controller/shop_overview/products/'
mqtt_topic_sub_set_scaleid = mqtt_clientname+'/config/scaleid/set'

mqtt_topic_refreshall = mqtt_clientname+'/refresh'

# MQTT Bridge

## Test mit:

Test senden mit
```bash
pi@shop-master:~ $ mosquitto_pub -h y1131616.ala.eu-central-1.emqxsl.com -u shop-controller -P ... -t 'test' -m 1 -d -p 8883
```

und empfangen mit:
```bash
pi@shop-master:~ $ mosquitto_sub -h y1131616.ala.eu-central-1.emqxsl.com -u shop-controller -P ... -t '#' -v -p 8883
```

Logs vom broker nach der Bridge überprüfen:
```bash
# die letzten Zeilen anzeigen und filtern
pi@shop-master:~/zeitlos/software/docker/mosquitto/data/log $ docker logs -f --tail 10000  mosquitto-2.18 | grep -i -C 20 emq
```

Bridge Config
```
pi@shop-master:~/zeitlos/software/docker/mosquitto/data/config/mosquitto/conf.d $ cat emqx.conf 
connection emqx1
log_type all
try_private false
address y1131616.ala.eu-central-1.emqxsl.com:8883
bridge_cafile /mosquitto/config/mosquitto/certs/emqxsl-ca.crt
#bridge_protocol_version mqttv50

remote_clientid shop-controller
remote_username shop-controller
remote_password ...
topic homie/shop_controller/# out
topic homie/public_webpage_viewer/# in
```
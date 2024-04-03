#!/usr/bin/bash

#terminate on error
set -e

echo "stopping... "
ssh shop-fsr sudo service relais-control stop && echo "shop-fsr relais-control stopped." &
ssh shop-fsr sudo service io-usb-readout stop && echo "shop-fsr io-usb-readout stopped." &
ssh shop-track sudo service tracker@dev-ttyUSB3 stop && echo "shop-track tracker USB3 stopped " &
ssh shop-track sudo service tracker@dev-ttyUSB2 stop && echo "shop-track tracker USB2 stopped " &
ssh shop-track sudo service tracker@dev-ttyUSB1 stop && echo "shop-track tracker USB1 stopped " &
ssh shop-track sudo service tracker@dev-ttyUSB0 stop && echo "shop-track tracker USB0 stopped " &
ssh shop-shelf02 sudo service scale@dev-ttyUSB2 stop && echo "shop-shelf02 scale USB2 stopped " &
ssh shop-shelf02 sudo service scale@dev-ttyUSB1 stop && echo "shop-shelf02 scale USB1 stopped " &
ssh shop-shelf02 sudo service scale@dev-ttyUSB0 stop && echo "shop-shelf02 scale USB0 stopped " &
echo "waiting... "
wait
echo "done."

echo "Next step: Restarting cardreader service. Sure to proceed? No active payments ongoing? Press Enter or CTRL+C..."
read -n 1 -s
echo -n "Restarting cardreader service... "
sudo service cardreader restart
echo "done."

echo "Setze: Kein Kund im Laden detektiert."
mosquitto_pub -t "homie/shop-track-collector/pixels-above-reference" -m 0
echo "ready for start of tests"


echo "Setzte Shop Status auf 0"
mosquitto_pub -t "homie/shop_controller/set_shop_status" -m 0

echo "Warte bis der Laden im Zustand 1 ist. Dann Enter: Simulation, dass Karte gelesen wurde"
read -n 1 -s
mosquitto_pub -t "homie/cardreader/preauth_res" -m '{"terminal-id":60903182,"amount":5000,"trace":391,"time":121151,"date":520,"exp-date":2612,"seq-no":1,"payment-type":96,"ef-id":"672590eeeeeeeee6783f","receipt-no":275,"auth-id":"3836303231320000","cc":978,"VU-number":"1882500001     ","card-name":"girocard","card-type":5,"good-groups":[0,1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20,21,22,23,24,25,26,27,28,29,30,31,32,33,34,35,36,37,38,39,40,41,42,43,44,45,46,47,48,50,51,52,53,54,55,56,57,58,59,60,61,62,63,64,65,66,67,81,82,83,84,86,87,88,89,91,92,93,94,95,110,130,131,132,133,134,135,136,180,181,184,185,186,187,190],"receipt-param":1000000,"return_code_completion":0}'
echo "MQTT Kommando für erfolgreich gelese Karte gesendet."

echo "Jetzt den Laden betreten. Tür öffnen simulieren..."
read -n 1 -s
echo "ENTER für Türe offen"
#0 == Türe offen
mosquitto_pub -t "homie/door/pin1" -m 0
echo "Türe ist nun offen."

echo "Jetzt Türe zu simulieren. ENTER"
read -n 1 -s
mosquitto_pub -t "homie/door/pin1" -m 1
echo "Türe ist nun geschlossen."

echo "Sende, dass eine Person im Laden ist. Da dies erst nach 2.5 Sekunden ausgewertet wird, mehrfach senden. ENTER"
read -n 1 -s
echo "Sende Pixel > 0, 3x..."
mosquitto_pub -t "homie/shop-track-collector/pixels-above-reference" -m 1
sleep 2
mosquitto_pub -t "homie/shop-track-collector/pixels-above-reference" -m 1
sleep 2
mosquitto_pub -t "homie/shop-track-collector/pixels-above-reference" -m 1
echo "3x Ein Pixel über Threshold gesendet."


echo "Jetzt muss eingekauft werden."

echo " "

echo "Entnahme einer Gummibärenpackung aus der Waage. ENTER"
read -n 1 -s
mosquitto_pub -t "homie/scale-shop-shelf02-0-1.2-1.0/scales/493037101F4B/mass" -m 0.9

echo " "

echo "Kunde öffnet die Türe, geht raus, kommt aber nach 2 Sekunden wieder rein."
read -n 1 -s
mosquitto_pub -t "homie/door/pin1" -m 0
echo "Türe ist nun offen."
sleep 1
mosquitto_pub -t "homie/shop-track-collector/pixels-above-reference" -m 0
echo "Kunde ausserhalb des Ladens."
sleep 1
mosquitto_pub -t "homie/shop-track-collector/pixels-above-reference" -m 1
echo "Kunde wieder im Laden."
sleep 1
mosquitto_pub -t "homie/door/pin1" -m 1
echo "Türe ist nun geschlossen."


echo " "

echo "Kunde öffnet die Türe und verlässt den Laden."
read -n 1 -s
mosquitto_pub -t "homie/door/pin1" -m 0
echo "Türe ist nun offen."
sleep 1
mosquitto_pub -t "homie/shop-track-collector/pixels-above-reference" -m 0
echo "Kunde ausserhalb des Ladens."
sleep 1
mosquitto_pub -t "homie/door/pin1" -m 1
echo "Türe ist nun geschlossen."


echo " "

echo "Ende der Simulation. Jetzt wird alles wieder eingeschaltet."
echo "press Enter to continue."
read -n 1 -s

echo "starting... "
ssh shop-shelf02 sudo service scale@dev-ttyUSB0 start && echo "shop-shelf02 scale USB0 started " &
ssh shop-shelf02 sudo service scale@dev-ttyUSB1 start && echo "shop-shelf02 scale USB1 started " &
ssh shop-shelf02 sudo service scale@dev-ttyUSB2 start && echo "shop-shelf02 scale USB2 started " &
ssh shop-track sudo service tracker@dev-ttyUSB0 start && echo "shop-track track USB0 started " &
ssh shop-track sudo service tracker@dev-ttyUSB1 start && echo "shop-track track USB1 started " &
ssh shop-track sudo service tracker@dev-ttyUSB2 start && echo "shop-track track USB2 started " &
ssh shop-track sudo service tracker@dev-ttyUSB3 start && echo "shop-track track USB3 started " &
ssh shop-fsr sudo service io-usb-readout start && echo "shop-fsr io-usb-readout started " &
ssh shop-fsr sudo service relais-control start && echo "shop-fsr relais-control started " &
echo "waiting... "
wait
echo "done"

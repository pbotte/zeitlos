# Installationshinweise

Auf dem RasPi muss vor
```bash
pip install mariadb
#ggf nicht die neueste Version installieren, damit es mit den Dingen aus apt funktioniert:
pip install -Iv mariadb==1.0.7 
```

das folgende installiert werden:
```bash
sudo apt install libmariadb3 libmariadb-dev
```


## QR-Secret-Str

in die Datei `shop-controller.service` muss noch als notwendiger Parameter der QR-Secret-Str übergeben werden. Dieser muss gleich mit den auf der Webseite und php-Seiten sein.


## crontab auf shop-master

````
2 * * * * /usr/bin/timeout -s SIGINT 3610 /home/pi/.local/bin/mqtt-recorder --host localhost --mode record --file "/mnt/usbstick/mqtt-recordings/$(/usr/bin/date +"\%Y_\%m_\%dT\%H_\%M_\%S").csv"
15 3 * * * /usr/bin/find /mnt/usbstick/mqtt-recordings -type f -mtime +180 -exec rm {} \;

#Daten zur Webseite hochladen
52 * * * * /home/pi/zeitlos/software/public-www/local/sync_to_mysql.py --reset
```
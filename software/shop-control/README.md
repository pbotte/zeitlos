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

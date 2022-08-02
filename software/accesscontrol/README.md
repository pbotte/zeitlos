# Zugangscontrolle

## System mit QR-Code

### QR-Code Scanner für Raspi

- Unbedingt 32-Bit Version von Raspi OS, da raspistill nicht von 64bit unterstützt wird
- Lite Version wurde genommen.

```bash
# mit 
sudo raspi-config
# die Kamera einschalten!

sudo apt update
sudo apt install -y python3-opencv python3-pip python3-zbar python3-picamera
pip3 install pyzbar imutils paho-mqtt
```


### Technisch für QR-Codes in PHP-Seiten

* Es wird diese PHP-Bibliothek verwendet: http://phpqrcode.sourceforge.net

Dann lässt sich wie folgt einfach ein QR-Code erzeugen, der vom Kunden zur Öffnung eingescannt wird.
```php
<?php
  // outputs image directly into browser, as PNG stream
  include('qrlib.php');
  
  $str = 'http://192.168.178.1/ui/?';
  $url_str = $str.hash('sha512', 'hallo'); //hier steht das Geheimnis
  
  //public static function png($text, $outfile = false, $level = QR_ECLEVEL_L, $size = 3, $margin = 4, $saveandprint=false)
  QRcode::png($url_str, false, QR_ECLEVEL_H, 10);
?>
```

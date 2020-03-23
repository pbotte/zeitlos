# Zugangscontrolle

## System mit QR-Code


### Technisch

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

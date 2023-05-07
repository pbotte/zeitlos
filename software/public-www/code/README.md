# Intentional use

## qr.php

Display some QR code to retrieve invoices as PDF. Call:
```
./code/qr.php?t=TEXT-IN-QR-CODE
```

## invoice.php

Erzeugt die Rechnung als PDF oder HTML output.

```
./code/invoice.php?d=lZHfTsIwFMZfpal3pFv6h8LYHQgxBkVjwBvGRYUyFkZHui4aCW_mnS_mmSAOTQRP0ib9fuec9jvd4BkON3iNw_EY39tsViwdYpgwUue-JHRCvmWOiSTS54SVaiexRhtMBOEg8WqiKFVGQZwQPMUhRhB9b-QNvK7Xg70D-w2sqxKgyKA_4x98qHPntF0lRqVnVFbK-8o6bV7VIi1MjOLEZlNlZ-ddf6tekpVKn7SzKv6SJSWUot7oITKP2s7f32JonFdyGCdC7hJOXcADn9Z9Trn4gZgIZSMyw71l77pbgQ3aooIFHHjbG1gfUUqFaAHp6FTHO4kLGZmdeQNndHEcjWYggPvzLI39gf31NmjJgGfGqaVLsxxdLpL1gd6ZNDEaBgBfX6xWel_PgoBLWpbu_bULl9kkT7QtZ2QOqXUqW6W_Y66Me86sm2Yz_fmC0_Or1RA66oHgR8CRA1qrYYIdDhFrBEI0g3qTb7cf&c=12be3d5a
```

mit dem zusätzlichen Parameter `out=pdf` (default) oder `out=html` können die beiden Formate ausgewählt werden.

Der Parameter `d=` übernimmt im JSON-format die Daten, in `c=` wird ein Check abgelegt.

Das Datenformat: 
- `p` enthält ein Array mit den Produkten. Jedes Produkt ist ein Array mit (Produktname, Anzahl, Einzelpreis, UST.-ID). Die UST.-ID kann sein 0=0%, 1=reduzierter Satz, 2= voller Satz.
- `c` der Text vom Kartenterminal
- `t` der Zeitpunkt der Rechnung als Unixtimestamp.

Beispiel-Daten (für `d`):
```
{"d":{"p":[["Produkt 1",1,42.5,0],["Produkt 2",5,5.2,1],["Birnen",3,2.2,2],["Produkt 3",3,10,2]],"c":"add card text","t": 1683378472}}
```
### Beispielberechnung

```php
<?php
$SECRETSTR= "blablablaskfjshfushdfisuh5487wzfisaubsidab";

//Load data from user via URL
$data_str = "";
if (array_key_exists("d", $_GET)) {
  $data_str = $_GET['d'];
}

//Start decoding
$data_str_encoded = rtrim(strtr(base64_encode(gzdeflate($data_str, 9)), '+/', '-_'), '=');

$str_to_check = $SECRETSTR.$data_str_encoded;
$correct_check_str = hash('crc32', $str_to_check, false);

?>
```

### Aufruf mittels:


Zur Rechnung, als HTML-Ausgabe:
```php
	<p><a href="/code/invoice.php?d=<?= $data_str_encoded?>&c=<?= $correct_check_str?>&out=html">zum PDF (index.php)</a></p>
```

Zur Rechnung, als PDF, via QR-Code:
```php
	<p><img src="/code/qr.php?t=<? echo("https://www.hemmes24.de/pdf/?d%3D".$data_str_encoded."%26c%3D".$correct_check_str)?>"></p>
```


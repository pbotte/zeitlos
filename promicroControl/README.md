# Hardware
## Pinbelegung

> Eine vollumfängliche Einführung gibt es hier: https://learn.sparkfun.com/tutorials/pro-micro--fio-v3-hookup-guide/all#hardware-overview-pro-micro

![Pinout Pro Micro](https://cdn.sparkfun.com/assets/9/c/3/c/4/523a1765757b7f5c6e8b4567.png)


| Display Pin | Pro Micro | hx711 (0) | hx711 (1) | hx711 (2) | hx711 (3) |
| ------ | ------ | - | - | - | - |
| | D0 (RX) | 
| | D1 (TX) |
|  | GND |  |  | GND | GND | 
| GND | GND |
| | D2 (SDA) |
| | D3 (SCL) (PWM) |
| | D4 (A6) |  |  | | DAT | 
| | D5 (PWM) | | | DAT
| | D6 (A7) (PWM) |
| BUSY | D7 |
| RST | D8 (A8) | 
| DC | D9 (A9) (PWM) |
| CS | D10 (A10) (PWM) |
| | D14 (MISO) |
| CLK | D15 (SPI CLK) |
| DIN | D16 (MOSI) |
| | D18 (A0) | CLK | CLK | CLK | CLK |
| | D19 (A1) | DAT | 
| | D20 (A2) | | DAT | 
| | D21 (A3) | | | | 
| VCC | VCC (3.3V) | VCC/VDD | VCC/VDD | VCC/VDD | VCC/VDD | 
|  | RST |
|  | GND | GND | GND |
|  | RAW (USB Vin) |


### Serialnumber of ATMEGA 32U4

10 bytes of serial number can be round accourding to this hint https://forum.pololu.com/t/a-star-adding-serial-numbers/7651
and it's patch https://gist.github.com/DavidEGrayson/bd12b8aed2f62ffb6989

Some sample SN:
```
0x57383735393215170b03
0x59363332393115171b11
0x59363332393115051808
0x5538333038391516070e
```

## Hinweise

### eink Display

#### Speicherbereiche und Update
Es gibt 2 Speicherbereich innerhalb des eink display. 
Sobald die Anzeige aktualisiert mit `DisplayFrame()` wird, wird der aktuelle Speicherbereich auf den anderen gewechselt.

Dies bedingt, dass man z.B. auch den Speicher zweimal löschen muss.

#### Versorgungsspannung
Sollte das Display einmalig mit einer zu großen Spannung angesprochen werden (Daten oder VCC), so ist es irreparabel defekt. Darauf achten, dass der Arduino nicht fälschlicherweise auf 5V eingestellt ist.


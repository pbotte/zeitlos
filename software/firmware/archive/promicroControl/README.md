# Hardware

## Übersicht
- Arduino Pro Micro
- eink-Display von Waveshare: [Wiki](https://www.waveshare.com/wiki/2.9inch_e-Paper_Module)
- 4x Wägezelle
- 4x HX711 ADC
- USB-Kabel: Micro-USB und A-Stecker
- Metall: Wägeschale aus VA und Teile aus Aluminium, [Spezielkleber für Edelstahl von Reinhartz](https://www.shop.kleinteileversand.de/spezialkleber-fuer-edelstahl.html)

## Pinbelegung

> Eine vollumfängliche Einführung gibt es hier: https://learn.sparkfun.com/tutorials/pro-micro--fio-v3-hookup-guide/all#hardware-overview-pro-micro

![Pinout Pro Micro](https://cdn.sparkfun.com/assets/9/c/3/c/4/523a1765757b7f5c6e8b4567.png)


| Display Pin | Pro Micro | hx711 (0) | hx711 (1) | hx711 (2) | hx711 (3) |
| ------ | ------ | - | - | - | - |
| | D0 (RX) | 
| | D1 (TX) |
|  | GND |  |  | GND | GND | 
| GND (schwarz) | GND |
| | D2 (SDA) |
| | D3 (SCL) (PWM) |
| | D4 (A6) |  |  |  | 
| | D5 (PWM) | | | | 
| | D6 (A7) (PWM) | CLK | CLK | CLK | CLK |
| BUSY (lila) | D7 |
| RST (weiß) | D8 (A8) | 
| DC (grün) | D9 (A9) (PWM) |
| CS (orange) | D10 (A10) (PWM) |
| | D14 (MISO) |
| CLK (gelb) | D15 (SPI CLK) |
| DIN (blau) | D16 (MOSI) |
| | D18 (A0) | DAT
| | D19 (A1) | | DAT | 
| | D20 (A2) | | | DAT | 
| | D21 (A3) | | | | DAT | 
| VCC (rot) | VCC (3.3V) | VCC/VDD | VCC/VDD | VCC/VDD | VCC/VDD | 
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

## Kommunikationsprotokoll

* min. length: 7 bytes 

| # |                | length (in bytes) | comments |
|---|----------------|-------------------|----------|
| 0 | start sequence | 2      | Always: 0x5a 0xa5 |
| 1 | command byte   | 2      | |
| 2 | number of data bytes    | 2  | |
| 3 | data bytes     | Number of data bytes | length = number prior advertised |
| 4 | checksum byte  | Sum of all, incl. start bytes | except checksum byte modulo 256


## Possible command bytes

| Cmd Byte | Funktion (Scale Controller an Arduino) | Funktion (Arduino an Scale Controller) |
|----------|----------------------------------------|----------------------------------------|
| 0x00 00  | Reset Arduino                          |                                        |
| 0x00 01  | Frage nach Seriennummer                | Sende Seriennummer                     |
| 0x00 02  | Frage nach Firmware Version            | Sende Firmware Version (4 bytes)       |
| 100(dec) | Update Display                         |                                        |
| 102(dec) | Transfer: ProductName                  |                                        |
| 103(dec) | Transfer:  ProductDescription.         |                                        |




## Installation 

- Installation von Platform IO

- Compilieren und hochladen mit 
  ```bash
  cd promicroControl
  pio run -t upload
  ```



## Hinweise

### eink Display

#### Speicherbereiche und Update
Es gibt 2 Speicherbereich innerhalb des eink display. 
Sobald die Anzeige aktualisiert mit `DisplayFrame()` wird, wird der aktuelle Speicherbereich auf den anderen gewechselt.

Dies bedingt, dass man z.B. auch den Speicher zweimal löschen muss.

Die Funktion `DisplayFrame()` verbraucht die Zeit von ca. 500ms für ein Update. Übergibt man `DisplayFrame(false)` so wartet die
Funktion nicht darauf, dass das Display ein busy=Low zurück gibt (Standard = true).

#### Versorgungsspannung
Sollte das Display einmalig mit einer zu großen Spannung angesprochen werden (Daten oder VCC), so ist es irreparabel defekt. Darauf achten, dass der Arduino nicht fälschlicherweise auf 5V eingestellt ist.


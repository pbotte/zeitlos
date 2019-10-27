# zeitlos
Werkzeuge für einen Bauern- oder Dorfladen

## Installation

Da Submodule in GIT enthalten sind, sollte dieses Repro mit
  ```bash
  git clone --recurse-submodules  git@github.com:pbotte/zeitlos.git
  ```
installiert werden.

Compilieren und hochladen mit 
```bash
cd promicroControl
pio run -t upload
```


## Waagen Steuerung
Für jede Waage wird auf Computerseite eine Steuerung ausgeführt.

Installation aller Python-Pakete auf Computerseite:
```bash
cd scaleController
pip3 install -r requirements.txt
````
installieren.

Starten mit
```bash
./scaleController.py -vv Controller1 /dev/ttyACM0
```

### Kommunikationsprotokoll:

```
   min. length: 7 bytes 
   [Start Sequence] [Command Byte, 2bytes] [Number of data bytes, 2bytes] [Data bytes] [Checksum byte]
   Start Sequence: 0x5a a5 = 2 bytes, fixed
   Number of data bytes: 2 bytes
   Data bytes: up to the number advertised in [Number of data bytes]
   Checksum byte: Sum of all (also start bytes) bytes except checksum byte modulo 256
```

| Cmd Byte | Funktion (Scale Controller an Arduino) | Funktion (Arduino an Scale Controller) |
|----------|----------------------------------------|----------------------------------------|
| 0x00 00  | Reset Arduino                          |                                        |
| 0x00 01  | Frage nach Seriennummer                | Sende Seriennummer                     |
| 0x00 02  | Frage nach Firmware Version            | Sende Firmware Version (4 bytes)       |
| 100(dec) | Update Display                         |                                        |
| 102(dec) | Transfer: ProductName                  |                                        |
| 103(dec) | Transfer:  ProductDescription.         |                                        |



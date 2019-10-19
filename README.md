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

````
  data transfer protocoll
   min. length: 7 bytes 
   [Start Sequence] [Command Byte, 2bytes] [Number of data bytes, 2bytes] [Data bytes] [Checksum byte]
   Start Sequence: 0x5a a5 = 2 bytes, fixed
   Command Byte: 0x00 00 = Update Display
                 0x00 01 = Update Product Info Type
   Number of data bytes: 2 bytes
   Data bytes: up to the number advertised in [Number of data bytes]
   Checksum byte: Sum of all (also start bytes) bytes except checksum byte modulo 256
```
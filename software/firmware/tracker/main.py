# wget https://raw.githubusercontent.com/CoreElectronics/CE-PiicoDev-VL53L1X-MicroPython-Module/main/PiicoDev_VL53L1X.py
# wget https://raw.githubusercontent.com/CoreElectronics/CE-PiicoDev-Unified/main/PiicoDev_Unified.py
from PiicoDev_VL53L1X import PiicoDev_VL53L1X
from time import sleep
import json

distSensor = PiicoDev_VL53L1X()

while True:
    v = {'v': distSensor.read()} # read the distance in millimetres
    print(json.dumps(v))
    sleep(0.1)


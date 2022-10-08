# How To install

wget https://raw.githubusercontent.com/CoreElectronics/CE-PiicoDev-VL53L1X-MicroPython-Module/main/PiicoDev_VL53L1X.py
wget https://raw.githubusercontent.com/CoreElectronics/CE-PiicoDev-Unified/main/PiicoDev_Unified.py

 
# All info: https://micropython.org/download/rp2-pico/
cd tracker
wget https://micropython.org/resources/firmware/rp2-pico-20220618-v1.19.1.uf2

# list all connected RP-devices
ls /dev/serial/by-id/
# or, if in bootloader mode:
lsblk

# Switch from micropython to Bootloader Modus
picocom /dev/serial/by-id/usb-MicroPython_Board_in_FS_mode_e6616408431e8b32-if00 
>>> machine.bootloader()

cd tracker
mkdir mount
sudo mount /dev/sda1 mount
sudo cp rp2-pico-20220618-v1.19.1.uf2 mount/
sudo umount mount
# Once programming of the new firmware is complete the device will automatically reset and be ready for use.


pip3 install adafruit-ampy
# possible hint: reconnect your shell to get ampy

# upload to all connected RP
for i in $(ls -1 /dev/serial/by-id/); do 
  echo $i; 
  ampy --port /dev/serial/by-id/$i put PiicoDev_Unified.py;  
  ampy --port /dev/serial/by-id/$i put PiicoDev_VL53L1X.py; 
  ampy --port /dev/serial/by-id/$i put main.py; 
  ampy --port /dev/serial/by-id/$i reset;  
done


# Regal-Computer

## Hardware
- [Raspberry Pi 3B](https://www.berrybase.de/raspberry-pi-co/raspberry-pi/boards/raspberry-pi-3-modell-b) (Leistungsfähig genug, und wird nicht so heiß, zieht nicht so viel Strom, läuft ohne Lüfter)
- micro SD-Card: [SanDisc Endurance 32GB](https://www.berrybase.de/raspberry-pi-co/raspberry-pi/speicherkarten/sandisk-high-endurance-microsdhc-uhs-i-u3-speicherkarte-43-adapter-32gb) (hält viele Schreibezyklen aus)
- Original-Gehäuse für Raspberry Pi
- [TP-Link PoE-Splitter 1GBit/s](https://www.idealo.de/preisvergleich/OffersOfProduct/2118892_-poe-splitter-tl-poe10r-tp-link.html)
- [Adapter-Kabel (Micro-B auf Hohlstecker Buchse)](https://www.berrybase.de/raspberry-pi-co/raspberry-pi/kabel-adapter/usb-kabel-adapter/adapterkabel-hohlstecker-buchse-5-5x2-1mm-micro-usb-b-stecker-schwarz-15cm) Adapterkabel Hohlstecker Buchse 5,5x2,1mm - Micro USB B Stecker schwarz 15cm
- HDMI-Kabel zum Monitor
- HDMI-Monitor mit VESA-Befestigungsmöglichkeit
- [D-Link USB-Hub, 7fach, mit PPS, mit Netzteil](https://www.idealo.de/preisvergleich/OffersOfProduct/97228.html)
- Langes Netzwerkkabel zum PoE-Switch
- 230V-Mehrfachsteckdosenleiste, genutzt für
  - Beleuchtung (Möglich sind: Zigbee-Lampen von Philips und IKEA)
  - Monitor
  - USB-HUB-Netzteil

### Alternative Konfiguration (Stand März 2024)
- Pi 4B oder 3B+
- POE+ Hat: [Spezifikation](https://datasheets.raspberrypi.com/poe/poe-plus-hat-product-brief.pdf)
  - Output power: 5 V DC/4 A
  - PoE Standard: PoE+ (IEEE 802.3at-2009 PoE)

Stand: März 2024
```bash
$ uname -a
Linux raspi-test 6.6.20+rpt-rpi-v8 #1 SMP PREEMPT Debian 1:6.6.20-1+rpt1 (2024-03-07) aarch64 GNU/Linux
```

Zügeln des Lüfters mittels:
```bash
$ dtoverlay -h rpi-poe-plus #Erläuterungen zu den Parametern
Name:   rpi-poe-plus

Info:   Raspberry Pi PoE+ HAT fan

Usage:  dtoverlay=rpi-poe-plus,<param>[=<val>]

Params: poe_fan_temp0           Temperature (in millicelcius) at which the fan
                                turns on (default 40000)
        poe_fan_temp0_hyst      Temperature delta (in millicelcius) at which
                                the fan turns off (default 2000)
...

$ sudo nano /boot/firmware/config.txt 
[all]
dtoverlay=rpi-poe-plus
dtparam=poe_fan_temp0=50000,poe_fan_temp0_hyst=5000
dtparam=poe_fan_temp1=55000,poe_fan_temp1_hyst=5000
dtparam=poe_fan_temp2=60000,poe_fan_temp2_hyst=5000
dtparam=poe_fan_temp3=65000,poe_fan_temp3_hyst=5000
```

Aktuelle Einstellung überprüfen mittels:
```bash
od -An --endian=big -td4 /proc/device-tree/thermal-zones/cpu-thermal/trips/trip?/temperature /proc/device-tree/thermal-zones/cpu-thermal/trips/trip?/hysteresis
       50000       55000       60000       65000
        5000        5000        5000        5000
```

Voll-Last-Test mit:
```bash
wget https://raw.githubusercontent.com/ssvb/cpuburn-arm/master/cpuburn-a53.S
gcc -o cpuburn-a53 cpuburn-a53.S
./cpuburn-a53 
```

CPU: Temperaturmessung in m°C
```bash
cat /sys/class/thermal/thermal_zone0/temp
```

HAT gelieferter Strom in muA
```bash
$ cat /sys/devices/platform/rpi-poe-power-supply/power_supply/rpi-poe/current_now
577000
```


## Software-Konfiguration

- Netzwerkname: `shop-shelf-01`
- Anzeige einer Webseite, Übermittlung des Hostnamens -> Weiterleitung zur angepassten Webseite
- Anzeige [im Kiosk-Modus](https://itrig.de/index.php?/archives/2309-Raspberry-Pi-3-Kiosk-Chromium-Autostart-im-Vollbildmodus-einrichten.html):
  - Maus weg
  - Vollbild
  - kein Bildschirmschoner
  ```bash
  sudo apt-get install unclutter
  sudo nano /etc/xdg/lxsession/LXDE-pi/autostart
  #Mauszeiger weg:
  @unclutter
  #Bildschirmschoner deaktivieren 
  #(die folgende Zeile also suchen und auskommentieren)
  #@xscreensaver -no-splash 

  #Bildschirm nicht ausschalten
  @xset s off
  @xset -dpms
  @xset s noblank
  #Browser starten
  @chromium-browser --kiosk http://shop-master/?hostname= 
  ```
- Abends und morgens den HDMI-Bildschirm [ein-/ausschalten](https://www.elektronik-kompendium.de/sites/raspberry-pi/2111101.htm) (nicht nicht getestet).
- Am Ende: Aktivierung des Overlay-FS



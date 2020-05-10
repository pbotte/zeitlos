# Regal-Computer

## Hardware
- [Raspberry Pi 3B](https://www.berrybase.de/raspberry-pi-co/raspberry-pi/boards/raspberry-pi-3-modell-b) (Leistungsfähig genug, und wird nicht so heiß, zieht nicht so viel Strom, läuft ohne Lüfter)
- micro SD-Card: [SanDisc Endurance 32GB](https://www.berrybase.de/raspberry-pi-co/raspberry-pi/speicherkarten/sandisk-high-endurance-microsdhc-uhs-i-u3-speicherkarte-43-adapter-32gb) (hält viele Schreibezyklen aus)
- Original-Gehäuse für Raspberry Pi
- [TP-Link PoE-Splitter 1GBit/s](https://www.idealo.de/preisvergleich/OffersOfProduct/2118892_-poe-splitter-tl-poe10r-tp-link.html)
- [Adapter-Kabel (Micro-B auf Hohlstecker Buchse)](https://www.berrybase.de/raspberry-pi-co/raspberry-pi/kabel-adapter/usb-kabel-adapter/adapterkabel-hohlstecker-buchse-5-5x2-1mm-micro-usb-b-stecker-schwarz-15cm)
- HDMI-Kabel zum Monitor
- HDMI-Monitor mit VESA-Befestigungsmöglichkeit
- [D-Link USB-Hub, 7fach, mit PPS, mit Netzteil](https://www.idealo.de/preisvergleich/OffersOfProduct/97228.html)
- Langes Netzwerkkabel zum PoE-Switch
- 230V-Mehrfachsteckdosenleiste, genutzt für
  - Beleuchtung (Zigbee-Lampen von Philips und IKEA?)
  - Monitor
  - USB-HUB-Netzteil


## Software-Konfiguration

- Netzwerkname: `shop-regal-01`
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



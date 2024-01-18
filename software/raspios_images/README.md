
Alle Opterationen in dem Verzeichnis
```bash
cd raspi_image
```

## Download des Images

Wir laden für alle Desktops to Version mit Desktop von der [offiziellen Seite](https://www.raspberrypi.com/software/operating-systems/), um später leichter einen Browser anzeigen zu können. Später wird lediglich entschieden, bis wohin gebootet werden soll (Console oder Desktop)

```bash
wget https://downloads.raspberrypi.com/raspios_armhf/images/raspios_armhf-2023-12-06/2023-12-05-raspios-bookworm-armhf.img.xz
```

## Image und Dateien kopieren

Nachschauen, wo es hingehen soll
```bash
lsblk
#macos
diskutil list
```

Dann kopieren:
```bash
xzcat 2023-12-11-raspios-bookworm-armhf-lite.img.xz | sudo dd of=/dev/sdc bs=1M status=progress conv=fsync

# unter macos 
# use devices with additional "r" eg /dev/rdisk2)
diskutil unmountDisk /dev/disk2
xzcat 2023-12-05-raspios-bookworm-armhf.img.xz | sudo dd of=/dev/rdisk2 bs=1m status=progress conv=sync
```

Alternativ mit separatem Decompress, falls es nicht funktioniert (Das Schreiben hört hie auf...)
```bash
xz -d -v 2023-12-05-raspios-bookworm-armhf.img.xz 
sudo dd if=2023-12-05-raspios-bookworm-armhf.img of=/dev/rdisk2 bs=1m status=progress conv=sync
```

Vorbereiten für das Kopieren der Konfigurationsdateien:
```bash 
mount /dev/sdc1 boot/ 
cp firstrun.sh ./boot/ # macos: Volumes/bootfs 

#entweder die komplette Datei kopieren oder die wichtigen Zeichen in cmdline.txt einfügen
cp cmdline.txt ./boot/ # macos: Volumes/bootfs 
```

Die wichtigen Zeichen in `cmdline.txt` sind:
```
systemd.run=/boot/firstrun.sh systemd.run_success_action=reboot systemd.unit=kernel-command-line.target
```
(Alles in einer Zeile!)

Für Lite-OS in Gänze:
```bash
console=serial0,115200 console=tty1 root=PARTUUID=57c84f67-02 rootfstype=ext4 fsck.repair=yes rootwait quiet init=/usr/lib/raspberrypi-sys-mods/firstboot systemd.run=/boot/firstrun.sh systemd.run_success_action=reboot systemd.unit=kernel-command-line.target ipv6.disable=1
```

Außerdem noch die beiden Dateien kopieren, für den Autostart des Browsers:
```bash
# later to /home/pi/startBrowser.sh
cp startBrowser.sh ./boot/

# later to: /etc/xdg/lxsession/LXDE-pi/autostart
cp autostart ./boot/
```
Diese beiden Dateien müssen in der Datei `firstrun.sh` noch in ihre richtigen Verzeichnisse verschoeben werden.


## Auswerfen 
```bash 
umount ./boot/
#unter mac os
sudo diskutil eject /dev/rdisk2
```



## Hinweise

Nicht alles was mit raspi-config geht ist [offiziell](https://www.raspberrypi.com/documentation/computers/configuration.html#list-of-options30) dokumentiert. Alternativ den Quellcode nach Befehlen suchen mit:
```bash
curl -sL https://github.com/RPi-Distro/raspi-config/raw/master/raspi-config | grep -E '(do|get)_[a-zA-Z0-9_ ]+\(' | sort | uniq
```
(Tipps von [hier](https://raspberrypi.stackexchange.com/questions/28907/how-could-one-automate-the-raspbian-raspi-config-setup))
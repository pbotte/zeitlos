# Installation Variante 1

Die Datei `shop-track00.service` als Vorlage nehmen und mit dem `/dev/serial/by-path/...` füllen.

```bash
sudo cp shop-track00.service /etc/systemd/system/
```


# Installation Variante 2


## Automatischer Start und Terminierung des Controllers

Dies geschieht mittels udev und systemd über die beiden Dateien `99-runTracker.rules` und `tracker@.service`. Durch die Konfiguration in der systemd-Datei ist sichergestellt, dass das Programm erst dann gestartet wird, wenn der serielle Anschluss bereit ist (After=) und beendet wird, sobald dieser verschwindet (BindTo=).

## Installationsanleitung

Nach einem git clone des Repositories müssen die beiden Dateien in die richtigen Systemverzeichnisse kopiert werden:

```bash
sudo cp zeitlos/software/waveshare-tof-readout/99-runTracker.rules /etc/udev/rules.d/
sudo cp zeitlos/software/waveshare-tof-readout/tracker@.service /etc/systemd/system/
```
Anschließend noch die Änderungen an Systemd mitteilen mittels:
```bash
sudo systemctl daemon-reload
```
Wird nun ein Serial Converter an den Computer angesteckt, so wird automatisch das Prorgamm gestartet. Wird er entfernt, so beendet sich dieses auch wieder.

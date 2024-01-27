# Automatischer Start und Terminierung des Controllers

Dies geschieht mittels udev und systemd über die beiden Dateien `99-runShopTrack.rules` und `shop-track@.service`. Durch die Konfiguration in der systemd-Datei ist sichergestellt, dass das Programm erst dann gestartet wird, wenn der serielle Anschluss bereit ist (After=) und beendet wird, sobald dieser verschwindet (BindTo=).

## Installationsanleitung

Nach einem git clone des Repositories müssen die beiden Dateien in die richtigen Systemverzeichnisse kopiert werden:

```bash
sudo cp zeitlos/scaleController/99-runShopTrack.rules /etc/udev/rules.d/
sudo cp zeitlos/scaleController/shop-track@.service /etc/systemd/system/
```
Anschließend noch die Änderungen an Systemd mitteilen mittels:
```bash
sudo systemctl daemon-reload
```
Wird nun ein Raspberry Pico an den Computer angesteckt, so wird automatisch der Shop-Track Controller gestartet. Wird er entfernt, so beendet sich auch der Scale-Track Controller.

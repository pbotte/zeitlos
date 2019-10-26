# Scaler Controller

Dieses Programm übernimmt die Steuerung des Mikrocontrollers auf Computerseite. Es wird für jede Waage einmal auf dem Computer ausgeführt und kommuniziert weiter über MQTT.

## Automatischer Start und Terminierung des Controllers

Dies geschieht mittels udev und systemd über die beiden Dateien `99-runScale.rules` und `scale-controller-@.service`.
Durch die Konfiguration in der systemd-Datei ist sichergestellt, dass das Programm erst dann gestartet wird, wenn der serielle Anschluss bereit ist (`After=`) und beendet wird, sobald dieser verschwindet (`BindTo=`). 

### Installationsanleitung
Nach einem `git clone` des Repositories müssen die beiden Dateien in die richtigen Systemverzeichnisse kopiert werden:
```bash
sudo cp zeitlos/scaleController/99-runScale.rules /etc/udev/rules.d/
sudo cp zeitlos/scaleController/scale-controller-@.service /etc/systemd/system/
```
Anschließend noch die Änderungen an Systemd mitteilen mittels: 
```bash
sudo systemctl daemon-reload
```

Wird nun ein Pro Micro Arduino an den Computer angesteckt, so wird automatisch das Scale Controller gestartet. Wird er entfernt, so beendet sich auch der Scale Controller.


## Zustände des Scale Controllers

Der Scale Controller kann folgende Zustände annehmen:
1) Nicht initialisiert.

   Dieser Zustand wird direkt nach dem Start angenommen. Die Waage muss noch mit Kalibrierungs- und Wareneigensschaften bespielt werden.
2) Initialisierung
3) Kundenmodus: Warten auf Kunden bzw. Ware entnommen.
4) Verkäufermodus: Einrichtung durch Verkäufer.

   Zuweisung der Waage mit Produkt aus Datenbank.
 
 

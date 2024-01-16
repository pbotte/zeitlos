# Übersicht über den gesamten Aufbau

Es gibt
- Einen Kontroll-Rechner, `shop-master`
- Einen Rechner für den Einlass und Werbung, `shop-doordisplay`
- Für jedes Regal einen Rechner, `shop-shelf-01`
  Die Waagen innerhalb eines Regals sind an den jeweiligen Regal-Rechner angeschlossen.
- Überwachungskameras
- Einen Router (Fritzbox, UNifi Router, etc.) für die Verbindung nach Außen.
- PoE-Switch für die Versorgung von Rechnern, Kameras, etc.

## Netzwerk

- Kontroll-Netz, 192.168.10.x/24

## Kontroll-Rechner:
- gut gesichert, nicht im Kundenbereich
- Hat eine ordentliche Festplatte oder SSD
- Bestimmt: Belegung de Ladens (Belegt/Frei)
- Berechnung des Warenkorbs

### Services:
- TimeScale-DB für 
  - Überwachungsdaten (Temperatur-Protokolle) und
  - Daten der Waagen (somit kann später eine Reklamation besser nachvollzogen werden)
- MQTT-Service
- HTTP-Server für Webseiten, die die `shop-shelf`-Computer darstellen
- Datenbank für Produkte und Einkäufe
- Am besten ein normaler Computer mit Standard-Hardware, abgesichert per USV.
- Bietet einen Wartungszugang

## Rechner mit Display am Eingang
- Netzwerkname: `shop-doordisplay`
- Zeigt den aktuellen Status an
- Immer Werbung für den Laden anzeigen.

## Pro Regal
- Zuleitung von 230V-Strom und Netzwerkkabel
- [Rechner mit USB-Hub und Waagen](setupShelfComputer.md)

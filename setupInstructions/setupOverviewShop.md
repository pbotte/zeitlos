# Übersicht über den gesamten Aufbau

Es gibt
- Einen Kontroll-Rechner, `shop-master`
- Einen Rechner für den Einlass und Werbung, `shop-doordisplay`
- Für jedes Regal einen Rechner, `shop-shelf-01`
  Die Waagen innerhalb eines Regals sind an den jeweiligen Regal-Rechner angeschlossen.
- Überwachungskameras
- Eine Fritzbox für die Verbindung nach Außen.
- PoE-Switch für die Versorgung aller Rechner.

## Netzwerk

VLANs:
- VLAN 3: Kontroll-Netz, 192.168.10.x/24
  - Fritzbox, shop-master, PoE-Switch
- VLAN 1: Kundenbereich-Netz, 192.168.20.x/24
  - shop-master, IP-Kamera, shop-shelf, shop-doordisplay, PoE-Switch

## Kontroll-Rechner:
- gut gesichert, nicht im Kundenbereich
- Hat eine ordentliche Festplatte oder SSD, damit diese nicht ständig kaputt geht und auch den Video-Daten Platz bietet.
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
- Bietet Wireguard-Zugang zur Wartung

## Rechner mit Display am Eingang
- Netzwerkname: `shop-doordisplay`
- Wenn Laden frei: Anzeige eines QR-Codes, welcher vom zentralen-PC via HTTP kommt. Andernfalls: "Bitte warten"
- Immer Werbung für den Laden anzeigen.

## Pro Regal
- Zuleitung von 230V-Strom und Netzwerkkabel
- [Rechner mit USB-Hub und Waagen](setupShelfComputer.md)

## MQTT-Namensraum

- Regal an Master:
  - Aktuelle Massen auf Waagen
  - Aktuelle Produkte auf Waagen
- Master and Regale:
  - Aktueller Einkauf auf allen Waagen
- Master an `shop-doordisplay` und Regale:
  - Belegung des Ladens

`localshop/shelf-1/scale-1/mass` (aktuell)
`localshop/shelf-1/scale-1/productNr`
`localshop/master/shopbasket` (kompletter Einkauf als JSON)
`localshop/master/shopmasket/lastchange` (letztes geändertes Produkt als JSON)
`localshop/master/shopstatus/occupancy` (Ladenbelegung)


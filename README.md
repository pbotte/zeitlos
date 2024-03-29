# Ladensystem für einen automatischen Dorfladen

Ein Paket aus Soft- und Hardware für ein automatisches Ladensystem, welches sich für kleine Läden, bis ca. 1000 Produkte, eignet. Das System basiert darauf, dass jedes Produkt durch eine eigene Waage gewogen wird, welche mit einem Computer verbunden ist.

![](https://raw.githubusercontent.com/pbotte/zeitlos/master/Projektmaterial/DorfladenTeststand2022.jpeg)

## Beschreibung eines typischen Einkaufs:
1. Einlass mit Girocard oder Kreditkarte.
2. Der Kunde betritt den Laden und entnimmt die Waren selbst aus den Regalen und Kisten. Die Anzeige der entnommen Waren und Massen erfolgt sofort und automatisch auf dem Kundendisplay.
3. Zum Abschluss des Einkaufs verlässt der Kunde den Laden. Die Abrechnung erfolgt anschließend automatisch über die Karte.

Es befindet sich immer nur max. ein Kunde im Laden. 


## Hinweise
* [Kostenübersicht](kostenuebersicht.md)

## Technische Details 
* [Zustände eines Einkaufs](ablauf.md)
* [Bestandteile des Ladens / MQTT-Übersicht](MQTT_Overview.md)
* Zum gleichzeitigen Herunterladen der Submodule: 
  ```bash
  git clone --recurse-submodules  git@github.com:pbotte/zeitlos.git
  ```

## Lizenz
Alle Soft- und Hardware stehen unter der [GPL v3](https://github.com/pbotte/zeitlos/blob/master/LICENSE) zur freien Verfügung.


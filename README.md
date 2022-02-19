# Ladensystem für einen automatischen Dorfladen

Ein Paket aus Soft- und Hardware für ein automatisches Ladensystem, welches sich für kleine Läden, bis ca. 1000 Produkte, eignet. Das System basiert darauf, dass jedes Produkt durch eine eigene Waage gewogen wird, welche mit einem Computer verbunden ist.

![](https://raw.githubusercontent.com/pbotte/zeitlos/master/Projektantraege%20und%20Vortraege/IMG_1326_klein.jpg)

### Beschreibung eines typischen Einkaufs:
1. In der einfachen Ausbaustufe befindet sich immer nur ein Kunde im Laden. Der Einlass kann durch einen Türschließer auf Kundenkarteninhaber beschränkt werden. 
2. Im weiteren Einkauf entnimmt der Kunde die Waren selbst aus den Regalen und Kisten. Die Anzeige der entnommen Waren und Massen erfolgt sofort und automatisch auf dem Kundendisplay.
3. Zum Abschluss des Einkaufs verlässt der Kunde den Laden. Gibt es eine Kundenkarte, so erfolgt die Abrechnung im Nachinein per Rechnung oder Kreditkarte. Ohne eine Kundenkarte muss noch die Bezahlung per Bargeld an einem Terminal erfolgen.

In der erweiterten Ausbaustufe hält der Kunde seine Kundenkarte vor der Entnahme von Produkten an ein Lesegerät an der Waage. 


## Übersicht:

- [Konstruktionszeichnungen Waagen](https://github.com/pbotte/zeitlos/tree/master/hardware/waagen/konstruktionszeichnungen) (aktuell vier verschiedene Modelle)
- [Firmware für Waagen](https://github.com/pbotte/zeitlos/tree/master/software/firmware/promicroControl)
- Software auf dem zentralen Computer:
  - [Auslese der Waagen](https://github.com/pbotte/zeitlos/tree/master/software/scaleController)
  - [Kundenanzeige](https://github.com/pbotte/zeitlos/tree/master/software/clientLiveDisplay)



## Lizenz
Alle Soft- und Hardware stehen unter der [GPL v3](https://github.com/pbotte/zeitlos/blob/master/LICENSE) zur freien Verfügung.


## Hinweise

### Weitere Projekte, die Verwendung finden

- [USB Power Control](https://github.com/mvp/uhubctl)

### Hinweise zum Repository

Zum gleichzeitigen Herunterladen der Submodule:
```bash
git clone --recurse-submodules  git@github.com:pbotte/zeitlos.git
```



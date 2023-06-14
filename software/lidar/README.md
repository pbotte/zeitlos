# Installationshinweise

## lidar-readout 

Service auf dem Raspi, an dem der Lidar via USB angeschlossen ist, welcher nur die Daten ausliest und 
anschließend per MQTT versendet.

Vor dem Laden Betreten soll immer eine Referenz-Messung durchgeführt werden (Temperatur unterschiede, Wackler bei Anbringung etc., Rumstehende Dinge). 

## lidar-control

Service auf dem zentralen Computer, welcher die Daten von ggf. mehreren lidar-readouts entgegenimmt und 
eine eine zentrale Aussage über die Belegung des Ladens erzeugt. Gibt auch die Befehle über an/aus an
die einzelnen Lidars weiter.
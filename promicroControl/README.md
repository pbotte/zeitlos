

### Serialnumber of ATMEGA 32U4

10 bytes of serial number can be round accourding to this hint https://forum.pololu.com/t/a-star-adding-serial-numbers/7651
and it's patch https://gist.github.com/DavidEGrayson/bd12b8aed2f62ffb6989

Some sample SN:
```
0x57383735393215170b03
0x59363332393115171b11
0x59363332393115051808
0x5538333038391516070e
```

## Hinweise

### eink Display

Es gibt 2 Speicherbereich innerhalb des eink display. 
Sobald die Anzeige aktualisiert wird, wird der aktuelle Speicherbereich auf den anderen gewechselt.
Dieser Wechsel passiert nach dem Aufruf von `SetFrameMemory`.

Dies bedingt, dass man z.B. auh den Speicher zweimal löschen muss.

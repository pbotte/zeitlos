# Waagen I2C 

- Der Master fragt regelmäßig alle Waagen ab, so schnell er kann. 
- Die LED wird bei Bedarf geändert. 
- Master kann einen Busscan durchführen um den Waagen eine neue eindeutige I2C Adresse zu geben.


## Generelle Logik

- Daten in EEPROM:
  - EEPROM, byte 0: I2C-Adresse (7bit)

- Alle Waagen haben eine 6x 8bit MAC-Adresse. Sie wird aus der Chip Seriennummer abgeleitet.

- I2C Bus-Geschwindigkeit: sollte so niedrig sein, dass er auch als "Feldbus" über die langen Distanzen funktionieren kann. 
  - Evtl. die Widerstände niedriger wählen, siehe auch https://www.nxp.com/docs/en/application-note/AN10216.pdf Slide 41 auf Seite 17. 
  - 1,3kOhm ist die statische untere Grenze, daneben gibt es noch eine dynamisch (rise time).


Alle Waagen hören lesend auf:
- Adresse `0x00` (Broadcast/"General Call", https://www.i2c-bus.org/addressing/general-call-address/, nur schreibend möglich, kein Lesen von target)
- schreibend auf `0x08` (erste freie Adresse nach den reservierten Bereich `0..7`) und 
- r/w auf ihrer individuellen Adressen `9..119`:

| I2C Adr. | Richtung | Byte 0 = cmd | Anz. Bytes <br>(excl. cmd byte) | Erläuterung |
| ------ | -- | -- | -- | -- |
| `0x00` | w | `0x00` | 0 | Alle Waagen: Neustart  |
| `0x00` | w | `0x01` | 0 | Alle Waagen: Antwort-Bit zurücksetzen |
| `0x00` | w | `0x02` | 7 | I2C-Adresse setzen, MAC(Bytes 1..6), I2C-Adresse(Byte 7)  |
| `0x00` | w | `0x03` | 6 | Setzen der Referenz-MAC-Adresse, vgl. auch Read von Adresse `0x8` |
| `0x00` | w | `0x04` | 0 | LEDs aller Waagen: aus |
| `0x00` | w | `0x05` | 0 | LEDs aller Waagen: ein |
| `0x08` | r | - | 1 | Rückmeldung ob MAC-Adresse kleiner gleich der gesuchten. |
| `9..119` | r | - | <br>4 ODER<br>7 | Abhängig von Register: vgl. write `0x00`/`0x01` an `9..119`<br>Waagenwert (Byte 0..3) ODER<br>MAC-Adresse (Byte 0..5) und LED-Status (Byte 6) |
| `9..119` | w | `0x00` | 0 | nächtes Lesen enthält Waagen-Wert |
| `9..119` | w | `0x01` | 0 | nächtes Lesen enthält MAC-Adresse und LED-Status |
| `9..119` | w | `0x02` | 0 | LED aus |
| `9..119` | w | `0x03` | 0 | LED an |


## Einschalten der Waagen

- Beim Einsetzen der Stromversorgung nimmt die Waage die I2C-Adresse, welche sie bereits zuvor hatte, aus dem EEPROM. 
- Dies dient der Vermeidung von fehlenden Adressen bei  einer wackeligen Stromverbindung oder Stcker-Wackelkontakt.

- Stromversorgung des I2C-Bus sollte via MOSFET durch I2C Master steuerbar sein. Alternativ: USB-Hub mit Power Switch functionality.

## Setzen der I2C-Adressen / Suchen von Waagen

1. Master sendet auf Adresse `0x0` und Daten `0x1`: Alle Waagen setzen ihr Antwort-Bit zurück.
2. Master sendet auf Adresse `0x0` und Daten `0x03`+`0xxx xx xx xx xx xx` (7 bytes): MAC-Adresse, welche bei der nächsten Abfrage als Referenz gilt.
3. Master fragt ab, ob es ein Waage mit MAC-Adresse kleiner der Referenz gibt, die noch das Antwort-Bit gesetzt hat: Lesen eines Bytes von Adresse `0x8`.
4. Client antwortet mit 
   - `0xFF`, falls Antwort-Bit nicht mehr gesetzt ODER Adresse ist größer als Referenz
   - `0x00` (dominant bei Übertragung auf I2C-Bus), falls Adresse kleiner gleich Referenz

5. Der Master fährt so lang mit der Suche fort, bis er die MAC-Adresse einer einzelnen Waage herausgefunden hat. (Binäre Suche, suchen nach MAC-Adresse-1)
6. Der Master sendet nun an Adresse `0x0` ein "I2C Adresse setzen"-Kommando (`0x02`) mit der MAC-Adresse und der I2C-Adresse (8 Bytes).
  - Die Waage speichert sie ins EEPROM. 
  - Die Waage setzt bei sich das Antwort-Bit und antwortet damit bei zukündigen Broadcasts nur noch mit `0xFF`
  - Anschließend (`Wire.begin`) oder neustart via `resetViaSWR()`
7. Die Suche geht so lang weiter (zurück zu Punkt 2) wie bei einem Broadcast mit der Adresse 0xFFFFFFFFFFFF noch mind. eine Waage antwortet.

ToDO: Falls die Mehrheit der Waagen mit 0xFF die eine antwortende Waage mit 0x0 elektrisch überstimmen sollte, dann muss der I2C-Bus kurzzeitig bei manchen Waagen deaktiviert und auf "z" gesetzt werden. 


## Weitere Funktionen

- Master sendet auf Adresse `0x0` und Daten `0x0`: Waagen Restart


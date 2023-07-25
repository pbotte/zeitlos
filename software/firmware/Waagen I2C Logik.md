# Waagen I2C Logik

Beim Einsetzen der Stromversorgung nimmt die Waage die I2C-Adresse, welche sie bereits zuvor hatte. Dies dient der Vermeidung von fehlenden Adressen bei  einer wackeligen Stromverbindung oder Stcker-Wackelkontakt.
- EEPROM, byte 0-5: MAC-Adresse
- EEPROM, byte 6: I2C-Adresse

Der Master fragt regelmäßig alle Waagen ab, so schnell er kann. Die LED wird bei Bedarf geändert.

Die Geschwindigkeit des Busses sollte so niedrig sein, dass er auch als "Feldbus" über die langen Distanzen funktionieren kann. Evtl. die Widerstände niedriger wählen.

## Setzen der I2C-Adressen

- Alle Waagen hören auf Adresse `0x0`, als Broadcast/"General Call". 
- Alle Waagen haben eine 6x 8bit MAC-Adresse. Die ersten 3 Bytes sind Hersteller spezifisch, die hinteren 3 Bytes sind fortlaufend für jede produzierte Waage.
- Master sendet auf Adresse `0x0` und Daten `0x0 0x0 0x0 0x0 0x0 0x0`: Alle Waagen setzen ihr Antwort-Bit zurück.
- Wenn auf `0x0` ein Read-Request mit einer MAC-Adresse (6 Bytes) kommt, wird wie folgt geantwortet (GEHT NICHT, DA bei 0x0 kein Read möglich!):
  - Falls Antwort-Bit bereits gesetzt: `0xFF`
  - Falls Antwort-Bit noch nicht gesetzt: 
    -  mit `0xFF` geantwortet, falls die MAC-Adresse der Waage größer ist und 
    -  mit `0x00`, falls sie kleiner ist.
- Der Master fährt so lang mit der Sucher fort, bis er die MAC-Adresse einer einzelnen Waage herausgefunden hat. (Binäre Suche, suchen nach MAC-Adresse-1)
- Der Master sendet nun an Broadcast-Adresse `0x0` ein "I2C Adresse setzen"-Kommando mit der MAC-Adresse und der I2C-Adresse.
  - Die Waage setzt sich die I2C-Adresse und speichert sie ins EEPROM.
  - Die Waage setzt bei sich das Antwort-Bit und antwortet damit bei zukündigen Broadcasts nur noch mit `0xFF`

Die Suche geht so lang wie bei einem Broadcast mit der Adresse 0xFFFFFFFFFFFF noch eine Waage antwortet.

Falls die Mehrheit der Waagen mit 0xFF die eine antwortende Waage mit 0x0 elektrisch überstimmen sollte, dann muss der I2C-Bus kurzzeitig bei manchen Waagen deaktiviert und auf "z" gesetzt werden. 


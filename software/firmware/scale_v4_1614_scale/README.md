# Programiergerät

## Hardware:
- Raspberry Pi
- Arduino Nano as Programmer, Aufbau: https://github.com/SpenceKonde/AVR-Guidance/blob/master/UPDI/NanoUPDI_Recommended.png
  - Alternativen: https://github.com/wagiminator/AVR-Programmer
- Einen Widerstand, 480 Ohm
- 3x Pogo Pins für den Kontakt 


## Aufbau Anleitung
1. Raspi mit Raspbian installieren, Am Ende Readonly mounten
2. jtag2updi (alt!) oder SerialUPDI als Software nutzen: 
   - https://github.com/SpenceKonde/AVR-Guidance/blob/master/UPDI/jtag2updi.md
   - https://github.com/SpenceKonde/megaTinyCore/blob/master/megaavr/tools/ManualPython.md
3. Beim Einschalten: Raspi holt neueste Version von github.com für den Waagen Controller
4. Auf Knopfdruck: Upload startet, Ausnutzen der LED auf Arduino Nano
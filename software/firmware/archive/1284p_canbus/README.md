# Firmware erstmalig auf Waagencontroller aufspielen
Den Raspi auf die korrekte Geschwindigkeit einstellen:
```bash
sudo ip link set can0 up type can bitrate 125000
```

## Bootloader installieren
1. ISP-Kabel (alle 6 Pins von Sparkfun Pocket Programmer an ISP Header) aufstecken.
2. Fuse-Bits setzen
   ```bash
   avrdude -p atmega1284p -c usbtiny -B 10 -U lfuse:w:0xFF:m  -U hfuse:w:0xDA:m  -U efuse:w:0xFE:m
   ```
3. Bootloader schreiben
   ```bash
   cd ~/mcp-can-boot/
   avrdude -p atmega1284p -c usbtiny -U flash:w:.pio/build/ATmega1284P/firmware.hex:i
   ```
   Hinweis: Falls eine Meldung kommt, dass nicht alle Bytes korrekt verifiziert werden konnten, so kann doch alles geklappt haben.
4. ISP-Kabel ab

## Firmware compilieren
1. ```bash
   cd ~/zeitlos/software/firmware/1284p_canbus
   pio run
   ```

## Firmware erstmalig aufspielen
1. CAN-Bus 10-Pol dran.
2. ```bash
   cd ~/zeitlos/software/firmware/1284p_canbus
   # frische Chips haben noch 0xffff im Speicher, sonst die ID der Waage wie z.B. 0x1503
   npx mcp-can-boot-flash-app -p m1284p -m 0xffff -f .pio/build/atmega1284p/firmware.hex
   ```
3. Power-cycle das Board, dann wird geflashed. 

## Firmware das zweite mal aufspielen
1. CAN-Bus 10-Pol dran.
2. ```bash
   cd ~/zeitlos/software/firmware/1284p_canbus
   # Anstatt von 1503 die eigentlich ID des Chips einsetzen
   npx mcp-can-boot-flash-app -p m1284p -m 0x1503 -f .pio/build/atmega1284p/firmware.hex -R 80001503#42fabeef
   ```
3. Warten, fertig.

Fertig.

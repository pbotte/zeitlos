# Ausführung

```bash
pip install --break-system-packages -r requirements.txt

python3 ./software/roy-tof-camera/libroyale-5.10.0.2751-LINUX-arm-64Bit/python/tof_camera_readout.py -v -b 192.168.10.10
```

# Vobereitung

### Hardware:
- Raspi 4B, 1GB
- Raspbian, 64bit, Desktop

### Erster Test, ob Kamera korrekt angeschlossen:

```bash
cd Desktop/libroyale-5.10.0.2751-LINUX-arm-64Bit/bin/
sudo ./royaleviewer 
```

### udev-rules installieren, damit ohne sudo ausführbar
```bash
cd Desktop/libroyale-5.10.0.2751-LINUX-arm-64Bit/driver/udev/
sudo cp 10-royale-ubuntu.rules /etc/udev/rules.d/
```

### System vorbereiten
Anleitung: https://www.youtube.com/watch?v=8IJLDIYbaCg&t=156s
```bash
cd Desktop/libroyale-5.10.0.2751-LINUX-arm-64Bit/python/
sudo apt update
sudo apt upgrade
sudo apt install libusb-1.0-0 qtbase5-dev libopengl0 python3 python3-tk python3-matplotlib python3-numpy cmake cmake-gui swig
sudo reboot
````

Warpper für aktuelles python installieren
```bash
cd Desktop/libroyale-5.10.0.2751-LINUX-arm-64Bit/python/
cat README.md 

#noch eine Datei reinkopieren:
# von hier: https://github.com/numpy/numpy/tree/master/tools/swig
cd swig
wget https://raw.githubusercontent.com/numpy/numpy/main/tools/swig/numpy.i

#cmake-gui braucht das aktuelle Verzeichnis der libpython, dies ggf. mit find zuvor suchen
PYTHON_LIBRARY=/usr/lib/aarch64-linux-gnu/libpython3.11.so cmake-gui 

#Vorgehen / dort auswählen:
# - Eingabe-Pfad: python/swig Verzeichnis
# - Ausgabe neuen Ordner: python/build
# Configure, dort 2. Eintrag in Dropdown auswählen: "UNIX..."
# Haken bei cmake option für numpy.i anwählen
# Generate klicken
# cmake-gui verlassen

#build script ausführen
cd python/build/
make

#erzeugte Datei nach python kopieren
cd python/
mv _roypy.so _roypy.so-3.8
cp build/_roypy.so .
```
### Beispiel ausprobieren
```bash
python3 ./sample_retrieve_data.py 
````


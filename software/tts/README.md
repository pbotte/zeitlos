sudo apt install mpg321 

#Falls Raspbian lite installiert wurde, dann muss noch folgendes installiert werden
#sudo apt install pipewire puleaudio
#(Falls das nicht hilft, dann noch:
#sudo apt install alsa-oss libasound2-plugins libavresample4 pulseaudio pulseaudio-utils
#)

pip install -r requirements.txt

Die Datei asound.conf muss nach /etc kopiert werden, da sonst mpg321 (oder auch andere Komponenten wie pygame) das Sound-Gerät nicht finden.


## Installationshinweise

Bei 
```bash
aplay -l
**** Liste der Hardware-Geräte (PLAYBACK) ****
Karte 0: Headphones [bcm2835 Headphones], Gerät 0: bcm2835 Headphones [bcm2835 Headphones]
  Sub-Geräte: 8/8
  Sub-Gerät #0: subdevice #0
  Sub-Gerät #1: subdevice #1
  Sub-Gerät #2: subdevice #2
  Sub-Gerät #3: subdevice #3
  Sub-Gerät #4: subdevice #4
  Sub-Gerät #5: subdevice #5
  Sub-Gerät #6: subdevice #6
  Sub-Gerät #7: subdevice #7
Karte 1: vc4hdmi0 [vc4-hdmi-0], Gerät 0: MAI PCM i2s-hifi-0 [MAI PCM i2s-hifi-0]
  Sub-Geräte: 1/1
  Sub-Gerät #0: subdevice #0
Karte 2: vc4hdmi1 [vc4-hdmi-1], Gerät 0: MAI PCM i2s-hifi-0 [MAI PCM i2s-hifi-0]
  Sub-Geräte: 1/1
  Sub-Gerät #0: subdevice #0
```

```bash
cat /etc/asound.conf 
pcm.!default {
type asym
playback.pcm {
type plug
slave.pcm "hw:0,0"
}
}
````

Sonst:

bei 
```bash
aplay -l
**** Liste der Hardware-Geräte (PLAYBACK) ****
Karte 0: vc4hdmi0 [vc4-hdmi-0], Gerät 0: MAI PCM i2s-hifi-0 [MAI PCM i2s-hifi-0]
  Sub-Geräte: 1/1
  Sub-Gerät #0: subdevice #0
Karte 1: vc4hdmi1 [vc4-hdmi-1], Gerät 0: MAI PCM i2s-hifi-0 [MAI PCM i2s-hifi-0]
  Sub-Geräte: 1/1
  Sub-Gerät #0: subdevice #0
Karte 2: Headphones [bcm2835 Headphones], Gerät 0: bcm2835 Headphones [bcm2835 Headphones]
  Sub-Geräte: 8/8
  Sub-Gerät #0: subdevice #0
  Sub-Gerät #1: subdevice #1
  Sub-Gerät #2: subdevice #2
  Sub-Gerät #3: subdevice #3
  Sub-Gerät #4: subdevice #4
  Sub-Gerät #5: subdevice #5
  Sub-Gerät #6: subdevice #6
  Sub-Gerät #7: subdevice #7
```
Muss die Datei aussehen:
```bash
cat /etc/asound.conf 
pcm.!default {
type asym
playback.pcm {
type plug
slave.pcm "hw:2,0"
}
}
```


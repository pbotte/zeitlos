
sudo apt install mpg321 

#Falls Raspbian lite installiert wurde, dann muss noch folgendes installiert werden
# sudo apt install puleaudio

pip install -r requirements.txt

Die Datei asound.conf muss nach /etc kopiert werden, da sonst mpg321 (oder auch andere Komponenten wie pygame) das Sound-Gerät nicht finden.

# Installation

## Alle Software-Komponenten

Einfach mit dem Install-Skript. 
1. Download via
```bash
curl -fsSL https://raw.githubusercontent.com/pbotte/zeitlos/master/software/get.sh -o get.sh
```
2. run the script either as root, or using sudo to perform the installation.
```bash
sudo bash get.sh
```



## www

```bash
cd /home/pi/zeitlos/software/www/
git clone https://git.code.sf.net/p/phpqrcode/git qr
git clone https://github.com/nodeca/pako.git
git clone https://github.com/tecnickcom/TCPDF.git tcpdf
```

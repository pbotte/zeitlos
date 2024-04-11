# Install Docker

```bash
curl -fsSL https://get.docker.com -o get-docker.sh
sh get-docker.sh
sudo usermod -aG docker pi
```

# Start containers with

## PHP with Apache
```bash
docker run -dit --restart unless-stopped -p 80:80 --name apache-php -v /home/pi/zeitlos/software/www/:/var/www/html php:7.2-apache
```
and modifiy it in a second step to enable GD and SQL support:
```bash
docker exec -it apache-php /bin/bash
$ apt-get update && apt-get -y install libjpeg-dev libpng-dev zlib1g-dev git zip
$ docker-php-ext-configure gd \
        --with-png-dir=/usr/include \
        --with-jpeg-dir=/usr/include \
    && docker-php-ext-install gd \
    && docker-php-ext-enable gd
$ docker-php-ext-install pdo pdo_mysql
$ logout
docker stop apache-php
docker start apache-php
```
As a third step, one needs to clone /qr from:
```bash
cd ~/zeitlos/software/www/
git clone https://git.code.sf.net/p/phpqrcode/git qr
```


## Mosquitto
Verison 2.0.18 ist mit emqx.com kompatibel, vorherige Versionen evtl. nicht. 
```bash
# https://hub.docker.com/_/eclipse-mosquitto
docker run -dit --restart unless-stopped --name mosquitto -p 1883:1883/tcp -p 9001:9001  -v /home/pi/zeitlos/software/docker/mosquitto/data:/mosquitto/ eclipse-mosquitto:2.0.18
# wichtig: Das Verzeichnis /home/pi/docker/mosquitto/data und allen Unterordnern muss 1883:1883 gehören:
#          sudo chown -R 1883:1883 /home/pi/docker/mosquitto/data
```

## Maria DB
```bash
# https://hub.docker.com/r/jsurf/rpi-mariadb/
# für normale x86 (und nicht auf RasPi): https://hub.docker.com/_/mariadb, dann aber auch -e MARIASQL_ROOT... verwenden
sudo docker run --name mariadb  -v /home/pi/zeitlos/software/docker/mariadb/data/:/var/lib/mysql -p 3306:3306 -e MYSQL_ROOT_PASSWORD=mysupersecretpw --restart unless-stopped -dit jsurf/rpi-mariadb
# das Passwort wird beim ANLEGEN der Datenbank gesetzt. Anschließend kann die Umgebungsvariable weggelassen werden, es wird NICHT neu gesetzt!
```

## PHPMyAdmin
```bash
# https://hub.docker.com/_/phpmyadmin
docker run --name phpmyadmin --restart unless-stopped -dit -e PMA_ARBITRARY=1 -p 8080:80 phpmyadmin
# Zugriff mit: http://192.168.179.150:8080/index.php?route=/
# Benutzername root und Passwort siehe "-e MYSQL_ROOT_PASSWORD=mysupersecretpw"
```


## Node Red
```bash
docker run -dit --restart unless-stopped -p 1880:1880 -v /home/pi/zeitlos/software/docker/nodered/data:/data  -e TZ=Europe/Berlin  --name nodered nodered/node-red
``

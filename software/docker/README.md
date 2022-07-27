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

## Mosquitto
```bash
# https://hub.docker.com/_/eclipse-mosquitto
docker run -dit --restart unless-stopped --name mosquitto -p 1883:1883/tcp -p 9001:9001  -v /home/pi/zeitlos/software/docker/mosquitto/data:/mosquitto/ eclipse-mosquitto 
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


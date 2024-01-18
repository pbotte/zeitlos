#!/bin/bash

# problematic: No network avaiable during first run!
# script needs to get split

set +e

#set hostname
raspi-config nonint do_hostname shelf01 >> /firstrun.log

#boot to (B1=console, requiring login)
#        (B4 - Boot to desktop, logging in automatically)
raspi-config nonint do_boot_behaviour B4 >> /firstrun.log

#set user and password to pi/pi
FIRSTUSER=`getent passwd 1000 | cut -d: -f1`
FIRSTUSERHOME=`getent passwd 1000 | cut -d: -f6`
if [ -f /usr/lib/userconf-pi/userconf ]; then
   /usr/lib/userconf-pi/userconf 'pi' '$5$d1r4xXRNWw$zvwAMq6RcdkzfgTrDaqrNwgBRUD68pc4JmhT6Y87Bn4'
else
   echo "$FIRSTUSER:"'$5$d1r4xXRNWw$zvwAMq6RcdkzfgTrDaqrNwgBRUD68pc4JmhT6Y87Bn4' | chpasswd -e
   if [ "$FIRSTUSER" != "pi" ]; then
      usermod -l "pi" "$FIRSTUSER"
      usermod -m -d "/home/pi" "pi"
      groupmod -n "pi" "$FIRSTUSER"
      if grep -q "^autologin-user=" /etc/lightdm/lightdm.conf ; then
         sed /etc/lightdm/lightdm.conf -i -e "s/^autologin-user=.*/autologin-user=pi/"
      fi
      if [ -f /etc/systemd/system/getty@tty1.service.d/autologin.conf ]; then
         sed /etc/systemd/system/getty@tty1.service.d/autologin.conf -i -e "s/$FIRSTUSER/pi/"
      fi
      if [ -f /etc/sudoers.d/010_pi-nopasswd ]; then
         sed -i "s/^$FIRSTUSER /pi /" /etc/sudoers.d/010_pi-nopasswd
      fi
   fi
fi

#enable ssh
systemctl enable ssh  >> /firstrun.log

#set timezone
rm -f /etc/localtime
echo "Europe/Berlin" >/etc/timezone
dpkg-reconfigure -f noninteractive tzdata  >> /firstrun.log

#set keyboard layout
cat >/etc/default/keyboard <<'KBEOF'
XKBMODEL="pc105"
XKBLAYOUT="de"
XKBVARIANT=""
XKBOPTIONS=""

KBEOF
dpkg-reconfigure -f noninteractive keyboard-configuration


apt-get update  >> /firstrun.log
apt-get upgrade -y  >> /firstrun.log
# install packages, if Raspi OS lite version is choosen:
# python3 python3-pip nano git
apt-get install -y  unclutter   >> /firstrun.log
# unclutter to get the mouse pointer away

cd /home/pi
sudo -u pi git clone --recurse-submodules  https://github.com/pbotte/zeitlos.git  >> /firstrun.log

#deactivate swap file
dphys-swapfile swapoff  >> /firstrun.log
dphys-swapfile uninstall  >> /firstrun.log
apt-get purge -y dphys-swapfile  >> /firstrun.log

###################################
# get rid of the welcome wizard
# see: https://forums.raspberrypi.com/viewtopic.php?t=231557
###################################
rm /etc/xdg/autostart/piwiz.desktop
###################################

###################################
# for shelf displays
###################################

#Set to X11 mode, since Wayland and chormium in kiosk mode are not (yet) compatible
sudo raspi-config nonint do_wayland W1  >> /firstrun.log

##screen blanking, default=1 (=Yes)
# details here: https://www.raspberrypi.com/documentation/computers/configuration.html#desktop
raspi-config nonint do_blanking 0  >> /firstrun.log

##activate VNC, default=1 (0=enabled, 1=No)
raspi-config nonint do_vnc 0  >> /firstrun.log

mv /boot/startBrowser.sh /home/pi/startBrowser.sh
chmod a+x /home/pi/startBrowser.sh
chwon pi:pi /home/pi/startBrowser.sh

mv /boot/autostart /etc/xdg/lxsession/LXDE-pi/autostart
chown pi:pi /boot/autostart /etc/xdg/lxsession/LXDE-pi/autostart

#########################################


#Overlay file system, 0=enabled, 1 =disable
#sudo raspi-config nonint do_overlayfs 0

echo "Reached end of firstrun.sh" >> /firstrun.log

#make sure, firstrun.sh will not be executed again
rm -f /boot/firstrun.sh
sed -i 's| systemd.run.*||g' /boot/cmdline.txt

exit 0
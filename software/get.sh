#!/bin/bash

# Set the shell to exit immediately if any command or pipeline returns a non-zero exit status
set -e

# Usage
# ==============================================================================
#
# To install all software and their dependencies:
#
# 1. download the script
#
#   $ curl -fsSL https://raw.githubusercontent.com/pbotte/zeitlos/master/software/get.sh -o get.sh
#
# 2. run the script either as root, or using sudo to perform the installation.
#
#   $ sudo bash get.sh
#

apt-get update
apt-get upgrade -y 

# install packages: 
# python3 python3-pip git  are not included in lite version of raspi os
# unclutter hides the mouse pointer on request
apt-get install -y python3 python3-pip nano git unclutter  

#boot to (B1=console, requiring login)
#        (B4 - Boot to desktop, logging in automatically)
raspi-config nonint do_boot_behaviour B4

# set hostname and activate ssh service via raspi imager
#set hostname
#raspi-config nonint do_hostname shelf01
#
#enable ssh
# 0 - Enable SSH
# 1 - Disable SSH
#raspi-config nonint do_ssh 0
#
#Select a locale, for example en_GB.UTF-8 UTF-8.
#correct setting will display currency and time correctly
#raspi-config nonint do_change_locale de_DE.UTF-8
#
#timezone
#raspi-config nonint do_change_timezone Europe/Berlin

cd /home/pi
sudo -u pi git clone --recurse-submodules  https://github.com/pbotte/zeitlos.git 

#deactivate swap file
dphys-swapfile swapoff 
dphys-swapfile uninstall 
apt-get purge -y dphys-swapfile 

###################################
# get rid of the welcome wizard
# see: https://forums.raspberrypi.com/viewtopic.php?t=231557
###################################
rm /etc/xdg/autostart/piwiz.desktop
###################################

###################################
# for shelf displays
###################################

# 0 - Enable splash screen
# 1 - Disable splash screen
raspi-config nonint do_boot_splash 1

#Set to X11 mode, since Wayland and chormium in kiosk mode are not (yet) compatible
raspi-config nonint do_wayland W1 

##screen blanking, default=1 (=Yes)
# details here: https://www.raspberrypi.com/documentation/computers/configuration.html#desktop
raspi-config nonint do_blanking 0 

##activate VNC, default=1 (0=enabled, 1=No)
raspi-config nonint do_vnc 0 

mv /boot/startBrowser.sh /home/pi/startBrowser.sh
chmod a+x /home/pi/startBrowser.sh
chwon pi:pi /home/pi/startBrowser.sh

mv /boot/autostart /etc/xdg/lxsession/LXDE-pi/autostart
chown pi:pi /boot/autostart /etc/xdg/lxsession/LXDE-pi/autostart

#########################################


#Overlay file system, 0=enabled, 1 =disable
#raspi-config nonint do_overlayfs 0

echo "Reached end of installation procedure"

exit 0
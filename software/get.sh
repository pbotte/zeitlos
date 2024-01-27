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


sstr="**********************************************************************\n"

echo "$sstr   apt update && apt upgrade \n$sstr"
apt-get update
apt-get upgrade -y 

echo "$sstr   install packages via apt \n$sstr"
# install packages: 
# python3 python3-pip git  are not included in lite version of raspi os
# unclutter hides the mouse pointer on request
apt-get install -y python3 python3-pip nano git unclutter  

cd /home/pi
echo "$sstr   git clone zeitlos \n$sstr"
sudo -u pi git clone --recurse-submodules  https://github.com/pbotte/zeitlos.git 

echo "$sstr   Install all Python depencies \n$sstr"
cd zeitlos/software/
find . -type f -name requirements.txt -exec cat '{}' ';' | sort -u > requirements.txt
pip3 install -r requirements.txt
cd

#deactivate swap file
echo "$sstr   deactivate swap file \n$sstr"
dphys-swapfile swapoff 
dphys-swapfile uninstall 
apt-get purge -y dphys-swapfile 


echo "$sstr   set boot target do_boot_behaviour \n$sstr"
#boot to (B1=console, requiring login)
#        (B4 - Boot to desktop, logging in automatically)
raspi-config nonint do_boot_behaviour B4

#echo "$sstr   set hostname \n$sstr"
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


###################################
# get rid of the welcome wizard
# see: https://forums.raspberrypi.com/viewtopic.php?t=231557
###################################
echo "$sstr   Delete file piwiz.desktop \n$sstr"
myfile="/etc/xdg/autostart/piwiz.desktop"
[ -e $myfile ] && rm $myfile && echo "File piwiz.desktop deleted."
###################################

###################################
# for shelf displays
###################################

# 0 - Enable splash screen
# 1 - Disable splash screen
echo "$sstr   raspi-config nonint do_boot_splash 1 \n$sstr"
raspi-config nonint do_boot_splash 1

#Set to X11 mode, since Wayland and chormium in kiosk mode are not (yet) compatible
echo "$sstr   raspi-config nonint do_wayland W1  \n$sstr"
raspi-config nonint do_wayland W1 

##screen blanking, default=1 (=Yes)
# details here: https://www.raspberrypi.com/documentation/computers/configuration.html#desktop
echo "$sstr   raspi-config nonint do_blanking 0 \n$sstr"
raspi-config nonint do_blanking 0 

##activate VNC, default=1 (0=enabled, 1=No)
echo "$sstr   raspi-config nonint do_vnc 0  \n$sstr"
raspi-config nonint do_vnc 0 

echo "$sstr   cp startBrowser.sh \n$sstr"
cp ./zeitlos/software/raspios_images/startBrowser.sh /home/pi/startBrowser.sh
chmod a+x /home/pi/startBrowser.sh
chown pi:pi /home/pi/startBrowser.sh

cp ./zeitlos/software/raspios_images/autostart /etc/xdg/lxsession/LXDE-pi/autostart
chown pi:pi /etc/xdg/lxsession/LXDE-pi/autostart

#########################################


#Overlay file system, 0=enabled, 1 =disable
#raspi-config nonint do_overlayfs 0

echo "Reached end of installation procedure"

reboot

exit 0
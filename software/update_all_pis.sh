#!/bin/bash

# Set the shell to exit immediately if any command or pipeline returns a non-zero exit status
set -e

ssh shop-shelf01 "cd /home/pi/zeitlos/ && git pull && sudo reboot"
ssh shop-shelf02 "cd /home/pi/zeitlos/ && git pull && sudo reboot"
ssh shop-shelf04 "cd /home/pi/zeitlos/ && git pull && sudo reboot"
ssh shop-shelf06 "cd /home/pi/zeitlos/ && git pull && sudo reboot"
ssh shop-shelf07 "cd /home/pi/zeitlos/ && git pull && sudo reboot"
ssh shop-shelf08 "cd /home/pi/zeitlos/ && git pull && sudo reboot"

ssh shop-track "cd /home/pi/zeitlos/ && git pull && sudo reboot"
ssh shop-tof "cd /home/pi/zeitlos/ && git pull && sudo reboot"

ssh shop-display01 "cd /home/pi/zeitlos/ && git pull && sudo reboot"
ssh shop-display02 "cd /home/pi/zeitlos/ && git pull && sudo reboot"
ssh shop-door "cd /home/pi/zeitlos/ && git pull && sudo reboot"

#!/bin/bash
#
#run: sudo bash ./install.sh

# Set the shell to exit immediately if any command or pipeline returns a non-zero exit status
set -e

SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )

echo "Copy files"
cp "$SCRIPT_DIR/io-usb-readout.service" /etc/systemd/system/

echo "Update systemctl"
systemctl daemon-reload

echo "Enable and start deamon"
systemctl enable io-usb-readout.service
systemctl start io-usb-readout.service

echo "Done."
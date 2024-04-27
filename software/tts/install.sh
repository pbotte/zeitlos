#!/bin/bash
#
#run: sudo bash ./install.sh

# Set the shell to exit immediately if any command or pipeline returns a non-zero exit status
set -e

SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )

echo "Copy files"
cp "$SCRIPT_DIR/shop-tts.service" /etc/systemd/system/
cp "$SCRIPT_DIR/asound.conf" /etc/

echo "Update systemctl"
systemctl daemon-reload

echo "Enable and start daemon"
systemctl enable shop-tts.service
systemctl start shop-tts.service

echo "Done."

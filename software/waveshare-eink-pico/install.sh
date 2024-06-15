#!/bin/bash
#
#run: sudo bash ./install.sh

# Set the shell to exit immediately if any command or pipeline returns a non-zero exit status
set -e

SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )

#for numpy install:
echo "Install dependencies"
sudo apt-get update
sudo apt-get install libopenblas-dev


echo "Copy files"
cp "$SCRIPT_DIR/shop-waveshare-eink-server.service" /etc/systemd/system/

echo "Update systemctl"
systemctl daemon-reload

echo "Enable and start daemon"
systemctl enable shop-waveshare-eink-server.service
systemctl start shop-waveshare-eink-server.service

echo "Done."

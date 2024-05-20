#!/bin/bash
#
#run: sudo bash ./install.sh

# Set the shell to exit immediately if any command or pipeline returns a non-zero exit status
set -e

SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )

echo "HINT: Install packages via pip and check whether the python TOF-Python-packages matches the python version. If not, see Readme.md"

echo "Copy files"
cp "$SCRIPT_DIR/tof-camera.service" /etc/systemd/system/

echo "Update systemctl"
systemctl daemon-reload

echo "Enable and start daemon"
systemctl enable tof-camera.service
systemctl start tof-camera.service

echo "Done."

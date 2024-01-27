#!/bin/bash
#
#run: sudo bash ./install.sh

# Set the shell to exit immediately if any command or pipeline returns a non-zero exit status
set -e

SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )

echo "Copy files"

cp "$SCRIPT_DIR/zeitlos/software/waveshare-tof-readout/99-runTracker.rules" /etc/udev/rules.d/
cp "$SCRIPT_DIR/zeitlos/software/waveshare-tof-readout/tracker@.service" /etc/systemd/system/

echo "Update systemctl"
systemctl daemon-reload

echo "Done."
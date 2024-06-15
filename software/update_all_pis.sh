#!/bin/bash

# Set the shell to exit immediately if any command or pipeline returns a non-zero exit status
set -e

for shelf in shop-shelf01 shop-shelf02 shop-shelf04 shop-shelf06 shop-shelf07 shop-shelf08 shop-fsr shop-track shop-tof shop-display01 shop-display02 shop-door; do
    echo "Checking $shelf..."
    
    # Test if the computer is reachable
    if ping -c 1 "$shelf" &> /dev/null; then
        echo "$shelf is reachable, proceeding with SSH command."
        ssh "$shelf" "cd /home/pi/zeitlos/ && git pull && ( sleep 5 ; sudo reboot ) & "
    else
        echo "$shelf is not reachable, skipping."
    fi
done

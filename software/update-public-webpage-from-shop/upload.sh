#!/usr/bin/bash


filename="password"
if [[ -f $filename ]]; then
   line=$(head -n 1 $filename)
   export SSHPASS=$line
else
   echo "File $filename not found. Create it and put only the SSH password as the first line."
   exit 1
fi

echo -n "Switching lights on... "
mosquitto_pub -h 192.168.10.10 -t homie/update_public_webpage/generic_pir/innen_licht -m "{\"v\":1,\"type\":\"Generic_PIR\"}"
echo "done."

echo -n "wait 10 Seconds to allow camera to adapt... "
sleep 10
echo "done."

echo -n "Getting image from top camera... "
wget -q -O /dev/shm/actualpic.jpg "http://peter:peter@192.168.10.25/image/jpeg.cgi?nowprofile=1"
echo "done."

echo -n "Getting image from side camera... "
wget -q -O /dev/shm/actualpic2.jpg "http://peter:peter@192.168.10.34/image/jpeg.cgi?nowprofile=1"
echo "done"

# sudo apt-get install imagemagick sshpass

cd /dev/shm/
#rotate in degree clockwise
echo -n "rotate image... "
convert actualpic.jpg -rotate 210 actualpic_r.jpg
echo "done."

#crop
# good hints to determine the numbers:
# https://askubuntu.com/questions/631689/cropping-images-using-command-line-tools-only
echo -n "crop image... "
convert actualpic_r.jpg -crop 780x650+1390+640 actualpic_rc.jpg
echo "done."

#export SSHPASS=SetPasswordHereForDebugPurposes
echo -n "upload to webpage... "
sshpass -e sftp -oBatchMode=no -b - sftp_uploader-act-pic\@hemmes24.de@ssh.strato.de << !
   put actualpic_rc.jpg
   put actualpic2.jpg
   bye
!
echo "done."

echo -n "Remove lights lock, will switch off in some time... "
mosquitto_pub -h 192.168.10.10 -t homie/update_public_webpage/generic_pir/innen_licht -m "{\"v\":0,\"type\":\"Generic_PIR\"}"
echo "done."


echo "script finished."

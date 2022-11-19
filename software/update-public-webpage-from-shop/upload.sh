#!/usr/bin/bash

echo -n "Getting image from camera... "
wget -q -O /dev/shm/actualpic.jpg "http://peter:peter@192.168.10.25/image/jpeg.cgi?nowprofile=1"
echo "done."

# sudo apt-get install imagemagick sshpass

cd /dev/shm/
#rotate in degree clockwise
echo -n "rotate iamge... "
convert actualpic.jpg -rotate 210 actualpic_r.jpg
echo "done."

#crop
# good hints to determine the numbers:
# https://askubuntu.com/questions/631689/cropping-images-using-command-line-tools-only
echo -n "crop image... "
convert actualpic_r.jpg -crop 780x650+1390+640 actualpic_rc.jpg
echo "done."

export SSHPASS=NeueBilderHeute463
echo -n "upload to webpage... "
sshpass -e sftp -oBatchMode=no -b - sftp_uploader-act-pic\@hemmes24.de@ssh.strato.de << !
   put actualpic_rc.jpg
   bye
!
#sftp_uploader-act-pic@hemmes24.de
#NeueBilderkommen2345
echo "done."

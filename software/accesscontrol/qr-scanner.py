#!/usr/bin/python3

# reinstall
# sudo apt install python3-opencv
# pip3 install pyzbar
# sudo apt install python-zbar
# pip3 install imutils
# pip3 install paho-mqtt
# sudo apt install python3-picamera

import time

time_last_debug_picture_saved = 0
time_script_started = time.time() #to terminate script after some time to prevent possible hang up of hard or software


import cv2
from pyzbar import pyzbar
import imutils
from imutils.video import VideoStream
import paho.mqtt.publish as publish
import hashlib
import json
import argparse
import requests #pip3 install requests
import logging
from pathlib import Path
import numpy as np


logging.basicConfig(format="%(asctime)-15s %(levelname)-8s  %(message)s")
logger = logging.getLogger("QR-Code Scanner")

parser = argparse.ArgumentParser()
parser.add_argument("-v", "--verbosity", help="increase output verbosity", default=0, action="count")
args = parser.parse_args()
logger.setLevel(logging.WARNING-(args.verbosity*10 if args.verbosity <=2 else 20) )

logger.info("Verbosity min. at info level.")


# floodfill like function
def find_components(arr):
  res = []
  dx,dy = [1,0,-1,0],[0,-1,0,1]
  N,M = arr.shape
  seen = np.zeros((N,M))
  for i in range(N):
    for j in range(M):
      if not seen[i][j] and arr[i][j]:
        todo=[(i,j)]
        seen[i][j] = 1
        cnt=0
        extreme_position = {'x':[i,i], 'y':[j,j]} #'x':min..max, 'y':min..max
        while todo:
          x,y = todo.pop()
          cnt = cnt+1
          for dX, dY in zip(dx,dy):
            X=x+dX
            Y=y+dY
            if X>=0 and X<N and  Y>=0 and Y<M and not seen[X][Y] and arr[X][Y]:
                todo.append((X,Y))
                seen[X][Y] = 1
                if X>extreme_position['x'][1]: extreme_position['x'][1]=X
                if X<extreme_position['x'][0]: extreme_position['x'][0]=X
                if Y>extreme_position['y'][1]: extreme_position['y'][1]=Y
                if Y<extreme_position['y'][0]: extreme_position['y'][0]=Y
        res.append({'pos':(i,j),'N_pixels':cnt,'extreme_position':extreme_position,
          'width':extreme_position['x'][1]-extreme_position['x'][0],
          'height':extreme_position['y'][1]-extreme_position['y'][0]})
  return res


# initialize video stream
video_width = 1920
video_height = 1440
page_width=148 #*mm #final page after cut
page_height=148 #*mm #final page after cut
qr_code_size = 60 #*mm

vs = VideoStream(usePiCamera = True, resolution=(video_width, video_height)  ).start()
logger.debug("wait for camera to adapt")
time.sleep(5)
last_frame = vs.read()

logger.info("Script completed initialisation.")
#while (time.time() - time_script_started < 60*60*24): #terminate after 24 hours of runtime
continue_loop = True
while continue_loop:
  #oben weiß
  #publish.single("homie/qrscanner/message", "Lege die Laufkarte ein.", hostname="localhost")
  time.sleep(0.5) #spend soem time to make the CPU not heating up too much

  # read from camera
  frame = vs.read()
  logger.debug("picture taken")
  loop_diff_test = cv2.subtract(frame, last_frame)
  result = not np.any(loop_diff_test)
  if result is True:
    logger.error("picture comparision shows: picture is NOT different comparend to last loop. This means, our camera connection is broken. Terminating.")
    continue_loop = False
  else:
    logger.debug("picture comparision shows: picture is different comparend to last loop. Good, our camera is still alive.")
    last_frame = frame.copy()

  frame_small = imutils.resize(frame, width=540)
  frame_gray = cv2.cvtColor(frame_small, cv2.COLOR_BGR2GRAY)
  if (time.time() - time_last_debug_picture_saved >= 10):
    cv2.imwrite("/dev/shm/time_{}.png".format(round(time.time())), frame_small) #for debug reasons
    time_last_debug_picture_saved = time.time()
    logger.info("debug picture saved")

  logger.debug("start searching for qr-codes")
  barcodes = pyzbar.decode(frame_gray)

  for barcode in barcodes: #for each barcode found
 #   cv2.imwrite("/home/pi/Pictures/time_{}.png".format(round(time.time())), frame) #for debugging
#    publish.single("homie/qrscanner/message", "QR-Code gefunden.", hostname="localhost")

    logger.debug("{}".format(barcode.data.decode("utf-8")) )



cv2.destroyAllWindows()
vs.stop()

logger.info("Script terminated. Total runtime: {:.2f} min".format( (time.time()-time_script_started)/60 ) )

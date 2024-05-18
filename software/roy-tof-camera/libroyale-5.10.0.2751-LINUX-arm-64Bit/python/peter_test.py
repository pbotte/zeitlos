#!/usr/bin/python3

# Copyright (C) 2017 Infineon Technologies & pmdtechnologies ag
#
# THIS CODE AND INFORMATION ARE PROVIDED "AS IS" WITHOUT WARRANTY OF ANY
# KIND, EITHER EXPRESSED OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND/OR FITNESS FOR A
# PARTICULAR PURPOSE.

"""This sample shows how to shows how to capture image data.

It uses Python's numpy and matplotlib to process and display the data.
"""

import argparse
try:
    from roypypack import roypy  # package installation
except ImportError:
    import roypy  # local installation
import time
import queue
from sample_camera_info import print_camera_info
from roypy_sample_utils import CameraOpener, add_camera_opener_options, select_use_case
from roypy_platform_utils import PlatformHelper

import sys
import collections

import numpy as np
import matplotlib.pyplot as plt

tof_data_queue = collections.deque(maxlen=20)
tof_data_base = None
v_std = None

class MyEventListener(roypy.PythonEventListener):
    def __init__(self):
        super(MyEventListener, self).__init__()

    def onEventPython(self, severity, description, type):
        print("Event : Severity : ", severity, " Description : ", description, " Type : ", type)

class MyListener(roypy.IDepthDataListener):
    def __init__(self, q):
        super(MyListener, self).__init__()
        self.queue = q
        self.figSetup = False

    def onNewData(self, data):
        #this is slower
        #zvalues = []
        #for i in range(data.getNumPoints()):
        #    zvalues.append(data.getZ(i))
        #zarray = np.asarray(zvalues)
        #p = zarray.reshape (-1, data.width)

        #faster retrieval of points by using numpy.i
        pc = data.npoints ()
        p = pc[:,:,2]
        self.queue.put(p)

    def paint (self, data):
        """Called in the main thread, with data containing one of the items that was added to the
        queue in onNewData.
        """
        # create a figure and show the raw data
        if not self.figSetup:
            self.fig = plt.figure(1)
            self.im = plt.imshow(data)

            plt.show(block = False)
            plt.draw()
            self.figSetup = True
        else:
            self.im.set_data(data)
            self.fig.canvas.draw()
        # this pause is needed to ensure the drawing for
        # some backends
        plt.pause(0.001)


np.set_printoptions(threshold=sys.maxsize)

if True:
    platformhelper = PlatformHelper()
    parser = argparse.ArgumentParser (usage = __doc__)
    add_camera_opener_options (parser)
    parser.add_argument ("--seconds", type=int, default=15, help="duration to capture data")
    options = parser.parse_args()
    opener = CameraOpener (options)
    cam = opener.open_camera ()

    print_camera_info (cam)
    print("isConnected", cam.isConnected())
    print("getFrameRate", cam.getFrameRate())

#    curUseCase = select_use_case(cam) #select dialog
    curUseCase = "Long_Range_5FPS"

    print ("Using a live camera")
    
    # we will use this queue to synchronize the callback with the main
    # thread, as drawing should happen in the main thread
    q = queue.Queue()
    l = MyListener(q)
    cam.registerDataListener(l)

    print ("Setting use case : " + curUseCase)
    cam.setUseCase(curUseCase)

    # uncomment to enable the event listening
    #el = MyEventListener()
    #cam.registerEventListener(el)

    cam.startCapture()
    # create a loop that will run for a time (default 15 seconds)
#    process_event_queue (q, l, options.seconds)

    # create a loop that will run for the given amount of time
    t_end = time.time() + options.seconds
    while True: #time.time() < t_end:
        try:
            # try to retrieve an item from the queue.
            # this will block until an item can be retrieved
            # or the timeout of 1 second is hit
            if len(q.queue) == 0:
                print("Aus 0")
                item = q.get(True, 1)
            else:
                print("Aus m")
                for i in range (0, len (q.queue)):
                    item = q.get(True, 1)
        except queue.Empty:
            # this will be thrown when the timeout is hit
            break
        else:
            tof_data_queue.append(item)

#        print(len(tof_data_queue))
        if len(tof_data_queue) > 8:

            if time.time() < t_end:
                #average over all arrays:, see https://stackoverflow.com/questions/18461623/average-values-in-two-numpy-arrays
                avg = np.array([ i for i in list(tof_data_queue)])
                v = np.mean( avg, axis=0 ) # if you want to ignore nan, use: np.nanmean
                v_std = np.std( avg, axis=0 ) # if you want to ignore nan, use: np.nanmean
#                print(v_std)

#                print (v)
#                print(v_std)
                #print(np.argwhere(v_std > 0.01))
                v_std[v_std > 0.01] = 0
                v_std[v_std != 0] = 1
#                print(v_std)
#                l.paint(v_std)
                print()

                #print(v)
                tof_data_base = np.copy(v)
            else:
#                l.paint(item)
                nv = (tof_data_base - item)
                print(f"{time.time() - t_end}: {np.sum(nv)}")
                nv = (tof_data_base - item) * v_std
                nv[nv < 0.1] = 0
                print(f"{time.time() - t_end}: {np.sum(nv)}")
                print()
#                l.paint(v_std)
                #l.paint(nv)

    cam.stopCapture()




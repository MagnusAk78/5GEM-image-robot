import numpy as np
from picamera.array import PiRGBArray
from picamera import PiCamera
import cv2
import socket
import math
import struct
import time
import helpers.logger
import datagram.data_transfer

LOG_INTERVAL = 10

X_RES = 640
Y_RES = 480
FPS = 10
JPEG_QUALITY = 75
PICAMERA = True

HOST = "127.0.0.1"
PORT = 5000
ADDRESS = (HOST, PORT)

TIME_BETWEEN_FRAMES = float(1.0 / FPS)

if PICAMERA:
    camera = PiCamera()
    camera.resolution = (X_RES, Y_RES)
    camera.framerate = FPS
    rawCapture = PiRGBArray(camera, size=(X_RES, Y_RES))
    print("x res: " + str(X_RES))
    print("y res: " + str(Y_RES))    
else:
    cap = cv2.VideoCapture(0)
    ret = cap.set(3, X_RES)
    ret = cap.set(4, Y_RES)
    print("x res: " + str(cap.get(3)))
    print("y res: " + str(cap.get(4)))

# allow the camera to warmup
time.sleep(0.1)

print("FPS: " + str(FPS))
print("JPEG_QUALITY: " + str(JPEG_QUALITY))

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

datagramNumber = 0

lastLogTime = time.time()

if PICAMERA:
    for frame in camera.capture_continuous(rawCapture, format="rgb", use_video_port=True):
        image = frame.array
        
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    
        ret, buf = cv2.imencode('.jpeg', gray, [cv2.IMWRITE_JPEG_QUALITY, JPEG_QUALITY])
        #ret, buf = cv2.imencode('.png', gray)
    
        if ret == True:
            npString = buf.tostring()
            datagramNumber = datagram.data_transfer.send_dataset(sock, ADDRESS, npString, datagramNumber)
        else:
            print('ret == False')
 
        # clear the stream in preparation for the next frame
        rawCapture.truncate(0)
        
        after = time.time()
        
        logDiffTime = after - lastLogTime
        if logDiffTime > LOG_INTERVAL:
            lastLogTime = after
            print('logging')
            after = time.time()
        
else:        
    while(True):
        before = time.time()
        # Capture frame-by-frame
        
        ret, frame = cap.read()
    
        if ret:
            # Our operations on the frame come here
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    
            ret, buf = cv2.imencode('.jpeg', gray, [cv2.IMWRITE_JPEG_QUALITY, JPEG_QUALITY])
            #ret, buf = cv2.imencode('.png', gray)
    
            if ret == True:
                npString = buf.tostring()
                datagramNumber = datagram.data_transfer.send_dataset(sock, ADDRESS, npString, datagramNumber)
            else:
                print('ret == False')
        
            after = time.time()
        
            logDiffTime = after - lastLogTime
            if logDiffTime > LOG_INTERVAL:
                lastLogTime = after
                print('logging')
                after = time.time()
        
            diffTime = after - before
            sleepTime = TIME_BETWEEN_FRAMES - diffTime
            if sleepTime > 0:
                time.sleep(sleepTime)

    # When everything done, release the capture
    sock.close()
    cap.release()

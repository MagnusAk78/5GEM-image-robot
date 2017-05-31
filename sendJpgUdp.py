import numpy as np
import cv2
import socket
import jpgUdpCommon
import math
import struct
import time
import logging
import custom_logger

LOG_INTERVAL = 10

TIME_BETWEEN_FRAMES = float(1.0 / jpgUdpCommon.FPS)

cap = cv2.VideoCapture(0)
ret = cap.set(3, jpgUdpCommon.X_RES)
ret = cap.set(4, jpgUdpCommon.Y_RES)

def sendImage(socket, imgData, datagramNumber):
    dataToSend = jpgUdpCommon.START_MESSAGE
    dataToSend += struct.pack('I', len(imgData))
    dataToSend += imgData
    datagramNumber = jpgUdpCommon.sendData(socket, dataToSend, datagramNumber)
    return datagramNumber

print("x res: " + str(cap.get(3)))
print("y res: " + str(cap.get(4)))
print("FPS: " + str(jpgUdpCommon.FPS))
print("JPEG_QUALITY: " + str(jpgUdpCommon.JPEG_QUALITY))

statsLogger = custom_logger.setup('sendJpgUdpStats')

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

datagramNumber = 0

lastLogTime = time.time()

while(True):
    before = time.time()
    # Capture frame-by-frame
    ret, frame = cap.read()
    
    if ret:
        # Our operations on the frame come here
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    
        ret, buf = cv2.imencode('.jpeg', gray, [cv2.IMWRITE_JPEG_QUALITY, jpgUdpCommon.JPEG_QUALITY])
        #ret, buf = cv2.imencode('.png', gray)
    
        if ret == True:
            npString = buf.tostring()
            datagramNumber = sendImage(sock, npString, datagramNumber)
        else:
            print('ret == False')
        
        after = time.time()
        
        logDiffTime = after - lastLogTime
        if logDiffTime > LOG_INTERVAL:
            statsLogger.info('datagramNumber: ' + str(datagramNumber))
            print('logging')
        
        diffTime = after - before
        sleepTime = TIME_BETWEEN_FRAMES - diffTime
        if sleepTime > 0:
            time.sleep(sleepTime)

# When everything done, release the capture
sock.close()
cap.release()

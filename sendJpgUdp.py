import numpy as np
import cv2
from socket import *

X_RES = 1280
Y_RES = 720
FPS = 10
JPEG_QUALITY = 75

cap = cv2.VideoCapture(0)
ret = cap.set(3, X_RES)
ret = cap.set(4, Y_RES)
ret = cap.set(5, FPS)

HOST = "127.0.0.1"
PORT = 4096
ADDRESS = (HOST, PORT)

MAX_MESSAGE_SIZE = 1500


def sendData(sock, data):
    sock.sendto(str(len(data)), ADDRESS)
    while len(data) > 0:
        if len(data) > MAX_MESSAGE_SIZE:
            dataToSend = MAX_MESSAGE_SIZE
        else:
            dataToSend = len(data)
        if(s.sendto(data[:dataToSend], ADDRESS)):
            data = data[dataToSend:]

print("x res: " + str(cap.get(3)))
print("y res: " + str(cap.get(4)))
print("FPS: " + str(cap.get(5)))
print("JPEG_QUALITY: " + str(JPEG_QUALITY))

s = socket(AF_INET, SOCK_DGRAM)

while(True):
    # Capture frame-by-frame
    ret, frame = cap.read()

    # Our operations on the frame come here
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    
    ret, buf = cv2.imencode('.jpeg', gray, [cv2.IMWRITE_JPEG_QUALITY, JPEG_QUALITY])
    
    if ret == True:
        npString = buf.tostring()
        sendData(s, npString)
    else:
        print('ret == False')
    
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

# When everything done, release the capture
s.close()
cap.release()
cv2.destroyAllWindows()
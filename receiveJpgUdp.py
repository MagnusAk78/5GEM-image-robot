import numpy as np
import cv2
from socket import *

HOST = "127.0.0.1"
PORT = 4096
ADDRESS = (HOST, PORT)

MAX_MESSAGE_SIZE = 1500

TIMEOUT = 1.0

def receiveData(sock):
    recData, address = sock.recvfrom(MAX_MESSAGE_SIZE)
    
    lenOfData = int(recData)
    print('image size: ' + str(lenOfData))
    data = ''
    while len(data) < lenOfData:
        recData, address = sock.recvfrom(MAX_MESSAGE_SIZE)
        data += recData
    return data

s = socket(AF_INET, SOCK_DGRAM)
s.bind(ADDRESS)

s.settimeout(TIMEOUT)

print("Receiving frames")

while(True):

    try:
        data = receiveData(s)
    except timeout:
        s.close()
        break
    
    npString = data
        
    #Unpack
    nparr = np.fromstring(npString, np.uint8)
    #img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    img = cv2.imdecode(nparr, cv2.IMREAD_GRAYSCALE)

    # Display the resulting frame
    cv2.imshow('img', img)
    
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

# When everything done, release the capture
cv2.destroyAllWindows()
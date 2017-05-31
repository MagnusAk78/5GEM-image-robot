import numpy as np
import cv2
import socket
import jpgUdpCommon
import struct

TIMEOUT = 1.0

def receiveImage(socket):
    while True:
        datagramNumber, data = jpgUdpCommon.receiveDatagram(socket)
        supposedStartMessage = data[:len(jpgUdpCommon.START_MESSAGE)]
        if supposedStartMessage == jpgUdpCommon.START_MESSAGE:
            break
        
    lenOfData = struct.unpack('I', data[len(jpgUdpCommon.START_MESSAGE):len(jpgUdpCommon.START_MESSAGE)+4])[0]
    data = data[len(jpgUdpCommon.START_MESSAGE)+4:]
    datagrams = 1
    while len(data) < lenOfData:
        expectedDatagramNumber = jpgUdpCommon.nextDatagramNumber(datagramNumber)
        datagramNumber, recData = jpgUdpCommon.receiveDatagram(socket)
        if datagramNumber != expectedDatagramNumber:
            print('Missing datagram, skipping image')
            return '', False
        data += recData
        datagrams += 1
    print('image size: ' + str(lenOfData) + ', datagrams: ' + str(datagrams))
    return data, True

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.bind(jpgUdpCommon.ADDRESS)

sock.settimeout(TIMEOUT)

print("Receiving frames")

while(True):
    data, ret = receiveImage(sock)

    if ret:
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
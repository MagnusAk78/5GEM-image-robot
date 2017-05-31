import socket
import struct

X_RES = 640
Y_RES = 480
FPS = 10
JPEG_QUALITY = 75

HOST = "172.16.0.25"
PORT = 4096
ADDRESS = (HOST, PORT)

DATAGRAM_SIZE = 1500
HEADER_SIZE = 4
PAYLOAD_SIZE = DATAGRAM_SIZE - HEADER_SIZE

START_MESSAGE = 'START'

MAX_DATAGRAM_NR = 0xFFFFFFFF

def nextDatagramNumber(datagramNumber):
    datagramNumber += 1
    if datagramNumber > MAX_DATAGRAM_NR:
        datagramNumber = 0
    return datagramNumber

def sendDatagram(sock, data, datagramNumber):
    datagram = struct.pack('I', datagramNumber)
    datagram += data
    sock.sendto(datagram, ADDRESS)
    return nextDatagramNumber(datagramNumber)
    
# return remaining data    
def sendData(sock, data, datagramNumber):
    while len(data) > 0:
        if len(data) > PAYLOAD_SIZE:
            dataToSend = PAYLOAD_SIZE
        else:
            dataToSend = len(data)
        datagramNumber = sendDatagram(sock, data[:dataToSend], datagramNumber)
        data = data[dataToSend:]
    return datagramNumber

def receiveDatagram(sock):
    try:
        recData, address = sock.recvfrom(DATAGRAM_SIZE)
    except socket.timeout:
        print('timeout')
        return -1, ''
    datagramNumber = struct.unpack('I', recData[:4])[0]
    return datagramNumber, recData[4:]
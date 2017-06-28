import socket
import struct

START_MESSAGE = 'START'

DATAGRAM_SIZE = 1384
HEADER_SIZE = 8
PAYLOAD_SIZE = DATAGRAM_SIZE - 4 - len(START_MESSAGE)

MAX_DATAGRAM_NR = 0xFFFFFFFF

def send_dataset(socket, address, dataset, datagramNumber):
    dataToSend = START_MESSAGE
    dataToSend += struct.pack('I', len(dataset))
    dataToSend += dataset
    datagramNumber = __send_data(socket, address, dataToSend, datagramNumber)
    return datagramNumber
    
def receive_dataset(socket):
    while True:
        (datagramNumber, data) = __receive_datagram(socket)
        supposedStartMessage = data[:len(START_MESSAGE)]
        if supposedStartMessage == START_MESSAGE:
            break
        
    lenOfData = struct.unpack('I', data[len(START_MESSAGE):len(START_MESSAGE)+4])[0]
    data = data[len(START_MESSAGE)+4:]
    datagrams = 1
    while len(data) < lenOfData:
        expectedDatagramNumber = __next_datagram_number(datagramNumber)
        datagramNumber, recData = __receive_datagram(socket)
        if datagramNumber != expectedDatagramNumber:
            return False, datagramNumber, ''
        data += recData
        datagrams += 1
    return (True, datagramNumber, data)

def __next_datagram_number(datagramNumber):
    datagramNumber += 1
    if datagramNumber > MAX_DATAGRAM_NR:
        datagramNumber = 0
    return datagramNumber

def __send_datagram(sock, address, data, datagramNumber):
    datagram = struct.pack('I', datagramNumber)
    datagram += data
    sock.sendto(datagram, address)
    return __next_datagram_number(datagramNumber)
    
# return remaining data    
def __send_data(sock, address, data, datagramNumber):
    while len(data) > 0:
        if len(data) > PAYLOAD_SIZE:
            dataToSend = PAYLOAD_SIZE
        else:
            dataToSend = len(data)
        datagramNumber = __send_datagram(sock, address, data[:dataToSend], datagramNumber)
        data = data[dataToSend:]
    return datagramNumber

def __receive_datagram(sock):
    try:
        recData, address = sock.recvfrom(DATAGRAM_SIZE)
    except socket.timeout:
        print('socket.timeout')
        return -1, ''
    datagramNumber = struct.unpack('I', recData[:4])[0]
    return (datagramNumber, recData[4:])
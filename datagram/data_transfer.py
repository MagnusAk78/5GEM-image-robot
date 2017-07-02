import socket
import struct
import math
import threading
import Queue

START_MESSAGE = 'START'

DATAGRAM_SIZE = 1384
HEADER_SIZE = 4
PAYLOAD_SIZE = DATAGRAM_SIZE - HEADER_SIZE

MAX_DATAGRAM_NR = 0xFFFFFFFF
SMALL_NUMBER = 0x400
LARGE_NUMBER = 0xFFFFFFFF - SMALL_NUMBER

MAX_BUFFER = 10
ERROR_DATA = -1

def next_datagram_number(datagram_number):
    datagram_number += 1
    if datagram_number > MAX_DATAGRAM_NR:
        datagram_number = 0
    return datagram_number
    
def send_dataset(socket, address, dataset, datagram_number):
    dataToSend = START_MESSAGE
    dataToSend += struct.pack('I', len(dataset))
    dataToSend += dataset
    datagram_number = __send_data(socket, address, dataToSend, datagram_number)
    return datagram_number
    
def __send_data(sock, address, data, datagram_number):
    while len(data) > 0:
        if len(data) > PAYLOAD_SIZE:
            dataToSend = PAYLOAD_SIZE
        else:
            dataToSend = len(data)
        datagram_number = __send_datagram(sock, address, data[:dataToSend], datagram_number)
        data = data[dataToSend:]
    return datagram_number

def __send_datagram(sock, address, data, datagram_number):
    datagram = struct.pack('I', datagram_number)
    datagram += data
    sock.sendto(datagram, address)
    return next_datagram_number(datagram_number)    
    
class DatasetReceiver(threading.Thread): 
    def __init__(self, sock, dataset_queue): 
        threading.Thread.__init__(self)
        self.threadRun = True
        self.dataset_queue = dataset_queue
        self.datagram_queue = Queue.Queue()
        self.datagram_receiver = DatagramReceiver(sock, self.datagram_queue)
        
    def stop_thread(self):
        self.datagram_receiver.stop_thread()
        self.threadRun = False
        
    def run(self):
        print 'DatasetReceiver run'
        
        self.datagram_receiver.start()
        start_found = False
        
        datagram = self.__get_next_start_datagram()
        
        while self.threadRun:
            size_of_dataset = struct.unpack('I', datagram[len(START_MESSAGE):len(START_MESSAGE) + 4])[0]
            dataset = datagram[len(START_MESSAGE) + 4:]
            datagrams = 1
            
            while len(dataset) < size_of_dataset:
                datagram = self.datagram_queue.get()
                if datagram != ERROR_DATA:
                    # All is good
                    dataset += datagram
                    datagrams += 1
                else:
                    # We have lost a datagram
                    break
            
            if len(dataset) == size_of_dataset:
                # All is good
                self.dataset_queue.put(dataset)
            else:
                # Datagram lost
                print 'Datagram lost, aborting'
            
            # Find next start
            datagram = self.__get_next_start_datagram()
                
    def __get_next_start_datagram(self):
        while True:
            datagram = self.datagram_queue.get()
            if datagram != ERROR_DATA:
                supposed_start_message = datagram[:len(START_MESSAGE)]
                if supposed_start_message == START_MESSAGE:
                    return datagram
        
class DatagramReceiver(threading.Thread): 

    def __init__(self, sock, datagram_queue): 
        threading.Thread.__init__(self)
        self.sock = sock
        self.threadRun = True
        self.datagram_queue = datagram_queue
        self.buffer_datagram_dict = {}
        
    def __receive_datagram(self):
        try:
            received_data, address = self.sock.recvfrom(DATAGRAM_SIZE)
        except socket.timeout:
            print('socket.timeout')
            return -1, ''
        received_datagram_number = struct.unpack('I', received_data[:4])[0]
        return (received_datagram_number, received_data[4:])
        
    def stop_thread(self):
        self.threadRun = False
        
    def run(self):
        print 'DatagramReceiver run'
        
        (received_datagram_number, received_data) = self.__receive_datagram()
        self.datagram_queue.put(received_data)
        next_expected_datagram_number = next_datagram_number(received_datagram_number)
        
        while self.threadRun:
            while self.buffer_datagram_dict.has_key(next_expected_datagram_number):
                self.datagram_queue.put(buffer_datagram_dict.pop(next_expected_datagram_number))
                next_expected_datagram_number = next_datagram_number(next_expected_datagram_number)
            (received_datagram_number, received_data) = self.__receive_datagram()
            if received_datagram_number != next_expected_datagram_number:
                self.buffer_datagram_dict[received_datagram_number] = received_data
                if len(self.buffer_datagram_dict) > MAX_BUFFER:
                    self.datagram_queue.put(ERROR_DATA)
                    next_expected_datagram_number = next_datagram_number(next_expected_datagram_number)
            else:
                self.datagram_queue.put(received_data)
                next_expected_datagram_number = next_datagram_number(received_datagram_number)

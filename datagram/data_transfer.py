import socket
import struct
import math
import threading
import Queue
import time

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
    def __init__(self, sock, dataset_queue, info_logger, statistics_logger, log_interval): 
        threading.Thread.__init__(self)
        self.threadRun = True
        self.dataset_queue = dataset_queue
        self.datagram_queue = Queue.Queue()
        self.datagram_receiver = DatagramReceiver(sock, self.datagram_queue)
        self.statistics_logger = statistics_logger
        self.info_logger = info_logger
        self.log_interval = log_interval
        
    def stop_thread(self):
        self.threadRun = False
        
    def run(self):
        print 'DatasetReceiver run'
        
        self.datagram_receiver.start()
        start_found = False
        
        start_time = time.time()
        self.info_logger.info('DatasetReceiver, start_time: ' + str(start_time))
        print('DatasetReceiver, start_time: ' + str(start_time))
        self.statistics_logger.info('Datagrams_received Datagrams_lost Frames_read Frames_lost')
        time_last_log = start_time        
        
        total_datagrams_received = 0
        total_datagrams_lost = 0
        total_frames_read = 0
        total_frames_lost = 0
        datagrams_received_since_last_log = 0
        datagrams_lost_since_last_log = 0
        frames_read_since_last_log = 0
        frames_lost_since_last_log = 0
        
        (received_datagrams, lost_datagrams, datagram) = self.__get_next_start_datagram()
        total_datagrams_received += received_datagrams
        datagrams_received_since_last_log += received_datagrams
        total_datagrams_lost += lost_datagrams
        datagrams_lost_since_last_log += lost_datagrams
        
        while self.threadRun:
            size_of_dataset = struct.unpack('I', datagram[len(START_MESSAGE):len(START_MESSAGE) + 4])[0]
            dataset = datagram[len(START_MESSAGE) + 4:]
            
            while len(dataset) < size_of_dataset:
                datagram = self.datagram_queue.get()
                if datagram != ERROR_DATA:
                    # All is good
                    dataset += datagram
                    total_datagrams_received += 1
                    datagrams_received_since_last_log += 1
                else:
                    # We have lost a datagram
                    total_datagrams_lost += 1
                    datagrams_lost_since_last_log += 1
                    break
            
            if len(dataset) == size_of_dataset:
                # All is good
                self.dataset_queue.put(dataset)
                total_frames_read += 1
                frames_read_since_last_log += 1
            else:
                # Datagram lost
                print 'Datagram lost, aborting'
                total_frames_lost += 1
                frames_lost_since_last_log += 1
                
            now = time.time()
            diff_time = now - time_last_log    
            if(diff_time > self.log_interval):
                time_last_log = now
                self.info_logger.info('DatasetReceiver, received ' + str(datagrams_received_since_last_log) + ' datagrams at ' + \
                    str(float(datagrams_received_since_last_log) / diff_time) + ' datagrams/second' + '. And ' + \
                    str(datagrams_lost_since_last_log) + ' were lost.')
                print('DatasetReceiver, received ' + str(datagrams_received_since_last_log) + ' datagrams at ' + \
                    str(float(datagrams_received_since_last_log) / diff_time) + ' datagrams/second' + '. And ' + \
                    str(datagrams_lost_since_last_log) + ' were lost.')
                self.info_logger.info('DatasetReceiver, received ' + str(frames_read_since_last_log) + ' frames at ' + \
                    str(float(frames_read_since_last_log) / diff_time) + ' frames/second' + '. And ' + \
                    str(frames_lost_since_last_log) + ' were lost.')
                print('DatasetReceiver, received ' + str(frames_read_since_last_log) + ' frames at ' + \
                    str(float(frames_read_since_last_log) / diff_time) + ' frames/second' + '. And ' + \
                    str(frames_lost_since_last_log) + ' were lost.')
                self.statistics_logger.info(str(datagrams_received_since_last_log) + ' ' + str(datagrams_lost_since_last_log) + ' ' + \
                    str(frames_read_since_last_log) + ' ' + str(frames_lost_since_last_log))
                time_last_log = now
                frames_read_since_last_log = 0
                frames_lost_since_last_log = 0
                datagrams_received_since_last_log = 0
                datagrams_lost_since_last_log = 0
            
            # Find next start
            (received_datagrams, lost_datagrams, datagram) = self.__get_next_start_datagram()
            total_datagrams_received += received_datagrams
            datagrams_received_since_last_log += received_datagrams
            total_datagrams_lost += lost_datagrams
            datagrams_lost_since_last_log += lost_datagrams
            
            
        end_time = time.time()
        total_time = end_time - start_time
        self.info_logger.info('DatasetReceiver done, received ' + str(total_datagrams_received) + \
            ' datagrams at ' + str(float(total_datagrams_received) / total_time) + ' datagrams/second' + '. And ' + \
                    str(total_datagrams_lost) + ' were lost.')
        print('DatasetReceiver done, received ' + str(total_datagrams_received) + \
            ' datagrams at ' + str(float(total_datagrams_received) / total_time) + ' datagrams/second' + '. And ' + \
                    str(total_datagrams_lost) + ' were lost.')        
        self.info_logger.info('DatasetReceiver done, received ' + str(total_frames_read) + \
            ' frames at ' + str(float(total_frames_read) / total_time) + ' frames/second' + '. And ' + \
                    str(total_frames_lost) + ' were lost.')
        print('DatasetReceiver done, received ' + str(total_frames_read) + \
            ' frames at ' + str(float(total_frames_read) / total_time) + ' frames/second' + '. And ' + \
                    str(total_frames_lost) + ' were lost.')
                    
        self.info_logger.info('DatasetReceiver, end_time: ' + str(end_time))
        print('DatasetReceiver, end_time: ' + str(end_time))
        self.datagram_receiver.stop_thread()
        self.datagram_receiver.join()
                
    def __get_next_start_datagram(self):
        found_start_message = False
        received_datagrams = 0
        lost_datagrams = 0
        
        while found_start_message == False:
            datagram = self.datagram_queue.get()
            if datagram != ERROR_DATA:
                received_datagrams += 1
                supposed_start_message = datagram[:len(START_MESSAGE)]
                if supposed_start_message == START_MESSAGE:
                    found_start_message = True
            else:
                lost_datagrams += 1
        
        return (received_datagrams, lost_datagrams, datagram)
        
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
                self.datagram_queue.put(self.buffer_datagram_dict.pop(next_expected_datagram_number))
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

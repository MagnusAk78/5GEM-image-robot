import socket
import struct
import math
import threading
import Queue
import time

START_MESSAGE = 'START'
END_MESSAGE = 'END'

def send_dataset(socket, dataset):
    dataToSend = START_MESSAGE
    dataToSend += dataset
    dataToSend += END_MESSAGE
    socket.sendall(dataToSend)
    
class DatasetReceiver(threading.Thread): 
    def __init__(self, connection, read_buffer_size, dataset_queue, info_logger, statistics_logger, log_interval): 
        threading.Thread.__init__(self)
        self.connection = connection
        self.read_buffer_size = read_buffer_size
        self.threadRun = True
        self.dataset_queue = dataset_queue
        self.statistics_logger = statistics_logger
        self.info_logger = info_logger
        self.log_interval = log_interval
        
    def stop_thread(self):
        self.threadRun = False
        
    def run(self):
        print 'DatasetReceiver run'
        
        start_found = False
        
        start_time = time.time()
        self.info_logger.info('DatasetReceiver, start_time: ' + str(start_time))
        print('DatasetReceiver, start_time: ' + str(start_time))
        self.statistics_logger.info('Frames_read')
        time_last_log = start_time
        
        total_frames_read = 0
        frames_read_since_last_log = 0
        
        bytes = ''
        while self.threadRun:
            a = bytes.find(START_MESSAGE)
            b = bytes.find(END_MESSAGE)
            if(a!=-1 and b!=-1):
                dataset = bytes[a + len(START_MESSAGE):b + len(END_MESSAGE)]
                bytes = bytes[b+len(END_MESSAGE):]
                self.dataset_queue.put(dataset)
                total_frames_read += 1
                frames_read_since_last_log += 1
            else:
                bytes += self.connection.recv(self.read_buffer_size)
            
            now = time.time()
            diff_time = now - time_last_log
            if(diff_time > self.log_interval):
                print('logging')
                time_last_log = now
                self.info_logger.info('DatasetReceiver received ' + str(frames_read_since_last_log) + ' frames at ' + \
                    str(float(frames_read_since_last_log) / diff_time) + ' frames/second')
                print('DatasetReceiver received ' + str(frames_read_since_last_log) + ' frames at ' + \
                    str(float(frames_read_since_last_log) / diff_time) + ' frames/second')
                    
                self.statistics_logger.info(str(frames_read_since_last_log))
                    
                time_last_log = now
                frames_read_since_last_log = 0
        
        end_time = time.time()
        total_time = end_time - start_time
        self.info_logger.info('DatasetReceiver done, received ' + str(total_frames_read) + \
            ' frames at ' + str(float(total_frames_read) / total_time) + ' frames/second' + '. And ' + \
                    str(total_frames_lost) + ' were lost.')
        print('DatasetReceiver done, received ' + str(total_frames_read) + \
            ' frames at ' + str(float(total_frames_read) / total_time) + ' frames/second' + '. And ' + \
                    str(total_frames_lost) + ' were lost.')
                    
        self.info_logger.info('DatasetReceiver, end_time: ' + str(end_time))
        print('DatasetReceiver, end_time: ' + str(end_time))

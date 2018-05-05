import socket
import struct
import math
import threading
import Queue
import timeit

START_MESSAGE = 'START'
END_MESSAGE = 'END'

def send_dataset(socket, dataset):
    dataToSend = START_MESSAGE
    dataToSend += dataset
    dataToSend += END_MESSAGE
    socket.sendall(dataToSend)
    
class DatasetReceiver(threading.Thread): 
    def __init__(self, socket, read_buffer_size, dataset_queue, info_logger, statistics_logger, log_interval): 
        threading.Thread.__init__(self)
        self.setDaemon(True)
        self.sock = socket
        self.client_connected = False
        self.connection = None
        self.read_buffer_size = read_buffer_size
        self.threadRun = True
        self.dataset_queue = dataset_queue
        self.statistics_logger = statistics_logger
        self.info_logger = info_logger
        self.log_interval = log_interval
        
    def wait_for_image_sending_client(self):
        print 'DatasetReceiver wait_for_image_sending_client'
        self.sock.listen(1)
        self.connection, client_address = self.sock.accept()
        print('DatasetReceiver, client connected: ' + client_address[0] + ':' + str(client_address[1]))        
        self.client_connected = True
        
    def stop_thread(self):
        self.threadRun = False
        
    def reveive_data(self):
        print 'DatasetReceiver reveive_data'
        start_time = timeit.default_timer()
        self.info_logger.info('DatasetReceiver, start_time: ' + str(start_time))
        print('DatasetReceiver, start_time: ' + str(start_time))
        self.statistics_logger.info('Frames_read')
        time_last_log = start_time
        
        total_frames_read = 0
        frames_read_since_last_log = 0    
    
        bytes = ''
        while self.threadRun and self.client_connected:
            a = bytes.find(START_MESSAGE)
            b = bytes.find(END_MESSAGE)
            if(a!=-1 and b!=-1):
                dataset = bytes[a + len(START_MESSAGE):b + len(END_MESSAGE)]
                bytes = bytes[b+len(END_MESSAGE):]
                self.dataset_queue.put(dataset)
                total_frames_read += 1
                frames_read_since_last_log += 1
            else:
                new_bytes = self.connection.recv(self.read_buffer_size)
                if new_bytes == '':
                    print('DatasetReceiver, empty bytestring received, connection is dead')
                    self.client_connected = False
                    break
                bytes += new_bytes
            
            now = timeit.default_timer()
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
                
        end_time = timeit.default_timer()
        total_time = end_time - start_time
        self.info_logger.info('DatasetReceiver done, received ' + str(total_frames_read) + \
            ' frames at ' + str(float(total_frames_read) / total_time) + ' frames/second')
        print('DatasetReceiver done, received ' + str(total_frames_read) + \
            ' frames at ' + str(float(total_frames_read) / total_time) + ' frames/second')
                    
        self.info_logger.info('DatasetReceiver, end_time: ' + str(end_time))
        print('DatasetReceiver, end_time: ' + str(end_time))                
        
    def run(self):
        print 'DatasetReceiver run'

        while self.threadRun:
            if not self.client_connected:
                self.wait_for_image_sending_client()
            try:
                if self.client_connected:
                    self.reveive_data()
            except socket.error, exc:
                print('socket.error: %s' % exc)
                self.connection.close()
                self.client_connected = False
                pass
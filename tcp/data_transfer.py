import socket
import struct
import math
import threading
import Queue
import timeit

CLIENT_ACK = 'ACK'
MAX_IMAGE_NUMBER = 2147483647

def send_image_data(socket, previous_round_trip_time, image_number, image_data):
    dataToSend = struct.pack('f', previous_round_trip_time) + struct.pack('i', image_number) + struct.pack('i', len(image_data)) + image_data
    socket.sendall(dataToSend)
    if image_number < MAX_IMAGE_NUMBER:
        return image_number + 1
    else:
        return 0
        
class DatasetReceiver(threading.Thread): 
    def __init__(self, socket, read_buffer_size, dataset_queue, info_logger, statistics_logger, latency_logger, log_interval): 
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
        self.latency_logger = latency_logger
        
    def wait_for_image_sending_client(self):
        print 'DatasetReceiver, waiting for image sending client'
        self.sock.listen(1)
        self.connection, client_address = self.sock.accept()
        print('DatasetReceiver, image sending client connected: ' + client_address[0] + ':' + str(client_address[1]))        
        self.client_connected = True
        
    def stop_thread(self):
        self.threadRun = False
        
    def get_data(self):
        new_bytes = self.connection.recv(self.read_buffer_size)
        if new_bytes == '':
            print('DatasetReceiver, empty bytestring received, connection is dead')
            self.client_connected = False
        return new_bytes
        
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
            while len(bytes) < struct.calcsize('fii') and self.client_connected:
                bytes += self.get_data()
            if self.client_connected == False:
                break
            rtt = struct.unpack('f', bytes[0:4])[0]
            image_number = struct.unpack('i', bytes[4:8])[0]
            self.latency_logger.image_received(rtt, image_number)
            length_of_next_image = struct.unpack('i', bytes[8:12])[0]
            bytes = bytes[12:]
            while(len(bytes) < length_of_next_image) and self.client_connected:
                bytes += self.get_data()
            if self.client_connected == False:
                break
            image_data = bytes[:length_of_next_image]
            bytes = bytes[length_of_next_image:]
            self.dataset_queue.put((image_data, image_number))
            total_frames_read += 1
            frames_read_since_last_log += 1
            
            # Send acknowledgement
            self.connection.sendall(CLIENT_ACK)
            
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
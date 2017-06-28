import cv2
import numpy as np
import Queue
import time
import threading
import socket
import datagram.data_transfer

# queue             Thread safe fifo queue where the frames are stored
# logger            Logger
# log_interval      How long between every statistic log in seconds

class ImageReader(threading.Thread): 
    def __init__(self, address, queue, info_logger, statistics_logger, log_interval): 
        threading.Thread.__init__(self)
        self.frame_queue = queue
        self.info_logger = info_logger
        self.statistics_logger = statistics_logger
        self.log_interval = log_interval
        self.thread_run = True
        self.datagram_address = address
        
    def stop_thread(self):
        self.thread_run = False

    def run(self):
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.bind(self.datagram_address)

        sock.settimeout(1.0)

        total_frames_read = 0
        total_frames_lost = 0
        frames_read_since_last_log = 0
        frames_lost_since_last_log = 0
    
        start_time = time.time()
        print('start_time: ' + str(start_time))
        time_last_log = start_time
        
        while self.thread_run:
            ret, datagram_number, np_string = datagram.data_transfer.receive_dataset(sock)
            if ret:
                #Unpack
                nparr = np.fromstring(np_string, np.uint8)
                #img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
                img = cv2.imdecode(nparr, cv2.IMREAD_GRAYSCALE)
                self.frame_queue.put(img)
                total_frames_read += 1
                frames_read_since_last_log += 1
            else:
                total_frames_lost += 1
                frames_lost_since_last_log += 1
    
            now = time.time()
            diff_time = now - time_last_log
                
            if(diff_time > self.log_interval):
                time_last_log = now
                self.statistics_logger.info('JpegUdpReader, received ' + str(frames_read_since_last_log) + ' frames at ' + \
                    str(float(frames_read_since_last_log) / diff_time) + ' frames/second' + '. And ' + \
                    str(frames_lost_since_last_log) + ' were lost.')
                print('JpegUdpReader, received ' + str(frames_read_since_last_log) + ' frames at ' + \
                    str(float(frames_read_since_last_log) / diff_time) + ' frames/second' + '. And ' + \
                    str(frames_lost_since_last_log) + ' were lost.')
                time_last_log = now
                frames_read_since_last_log = 0
                frames_lost_since_last_log = 0
    
        end_time = time.time()
        total_time = end_time - start_time
        self.statistics_logger.info('JpegUdpReader done, received ' + str(total_frames_read) + \
            ' frames at ' + str(float(total_frames_read) / total_time) + ' frames/second' + '. And ' + \
                    str(total_frames_lost) + ' were lost.')
        print('JpegUdpReader done, received ' + str(total_frames_read) + \
            ' frames at ' + str(float(total_frames_read) / total_time) + ' frames/second' + '. And ' + \
                    str(total_frames_lost) + ' were lost.')



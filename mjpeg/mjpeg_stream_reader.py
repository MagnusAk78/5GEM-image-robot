import logging
import cv2
import numpy as np
import urllib
import requests
import Queue
import time
import threading

# stream_url        Url where the strem is
# read_chunk_size   How many bytes to read every time
# queue             Thread safe fifo queue where the frames are stored
# info_logger       Info logger
# statistics_logger Statistics logger
# log_interval      How long between every statistic log in seconds

class MjpegStreamReader(threading.Thread): 
    def __init__(self, stream_url, read_chunk_size, queue, info_logger, statistics_logger, log_interval): 
        threading.Thread.__init__(self)
        self.stream_url = stream_url
        self.read_chunk_size = read_chunk_size
        self.frame_queue = queue
        self.info_logger = info_logger
        self.statistics_logger = statistics_logger
        self.log_interval = log_interval
        self.threadRun = True
        
    def stop_thread(self):
        self.threadRun = False

    def run(self):
        stream = requests.get(self.stream_url, stream = True)
        total_frames_read = 0
        frames_read_since_last_log = 0
        bytes = ''
    
        print('Connected to ' + self.stream_url +  ', Headers:')
        print(stream.request.headers)
    
        start_time = time.time()
        print('start_time: ' + str(start_time))
        time_last_log = start_time
    
        while self.threadRun:
            a = bytes.find('\xff\xd8')
            b = bytes.find('\xff\xd9')
            if(a!=-1 and b!=-1):
                jpg = bytes[a:b+2]
                bytes = bytes[b+2:]
                img = cv2.imdecode(np.fromstring(jpg, dtype=np.uint8),cv2.IMREAD_COLOR)
                self.frame_queue.put(img)
                total_frames_read += 1
                frames_read_since_last_log += 1
            else:
                #We only read more data if there are no images in the buffer
                bytes += stream.raw.read(self.read_chunk_size)
            now = time.time()
            diff_time = now - time_last_log
            if(diff_time > self.log_interval):
                print('logging')
                time_last_log = now
                self.info_logger.info('MjpegStreamReader, received ' + str(frames_read_since_last_log) + ' frames at ' + \
                    str(float(frames_read_since_last_log) / diff_time) + ' frames/second')
                time_last_log = now
                frames_read_since_last_log = 0
    
        end_time = time.time()
        total_time = end_time - start_time
        self.info_logger.info('MjpegStreamReader done, received ' + str(total_frames_read) + \
            ' frames at ' + str(float(total_frames_read) / total_time) + ' frames/second')
        print('MjpegStreamReader done, received ' + str(total_frames_read) + \
            ' frames at ' + str(float(total_frames_read) / total_time) + ' frames/second')



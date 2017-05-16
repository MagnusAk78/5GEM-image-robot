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
# total_frames      Total number of frames to read, 0 => no limit
# logger            Logger
# log_interval      How long between every statistic log in seconds

class MjpegStreamReader(threading.Thread): 
    def __init__(self, stream_url, read_chunk_size, queue, total_frames, logger, log_interval): 
        threading.Thread.__init__(self)
        self.stream_url = stream_url
        self.read_chunk_size = read_chunk_size
        self.frameQueue = queue
        self.total_frames = total_frames
        self.logger = logger
        self.log_interval = log_interval

    def run(self):
        stream = requests.get(self.stream_url, stream=True)
        total_frames_read = 0
        frames_read_since_last_log = 0
        bytes = ''
    
        print(stream.request.headers)
    
        start_time = time.time()
        print('start_time: ' + str(start_time))
        time_last_log = start_time
    
        while True:
            a = bytes.find('\xff\xd8')
            b = bytes.find('\xff\xd9')
            if(a!=-1 and b!=-1):
                jpg = bytes[a:b+2]
                bytes = bytes[b+2:]
                img = cv2.imdecode(np.fromstring(jpg, dtype=np.uint8),cv2.IMREAD_COLOR)
                self.frameQueue.put(img)
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
                self.logger.info('mjpeg_stream_reader done, received ' + \
                    str(frames_read_since_last_log) + ' frames at ' + \
                    str(float(frames_read_since_last_log) / diff_time) + ' frames/second')
                time_last_log = now
                frames_read_since_last_log = 0
            if(total_frames_read >= self.total_frames and self.total_frames > 0):
                break
    
        end_time = time.time()
        total_time = end_time - start_time
        print('end_time: ' + str(now))
        print('total_time: ' + str(total_time))
        self.logger.info('mjpeg_stream_reader done, received ' + str(total_frames_read) + \
            ' frames at ' + str(float(total_frames_read) / total_time) + ' frames/second')



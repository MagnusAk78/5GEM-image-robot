import logging
import cv2
import numpy as np
import Queue
import time
import threading
import socket
import jpgUdpCommon
import struct

# queue             Thread safe fifo queue where the frames are stored
# logger            Logger
# log_interval      How long between every statistic log in seconds

class JpegUdpReader(threading.Thread): 
    def __init__(self, queue, infoLogger, statisticsLogger, log_interval): 
        threading.Thread.__init__(self)
        self.frameQueue = queue
        self.infoLogger = infoLogger
        self.statisticsLogger = statisticsLogger
        self.log_interval = log_interval
        self.threadRun = True
        
    def stopThread(self):
        self.threadRun = False
        
    def receiveImage(self, socket):
        while True:
            datagramNumber, data = jpgUdpCommon.receiveDatagram(socket)
            supposedStartMessage = data[:len(jpgUdpCommon.START_MESSAGE)]
            if supposedStartMessage == jpgUdpCommon.START_MESSAGE:
                break
        
        lenOfData = struct.unpack('I', data[len(jpgUdpCommon.START_MESSAGE):len(jpgUdpCommon.START_MESSAGE)+4])[0]
        data = data[len(jpgUdpCommon.START_MESSAGE)+4:]
        datagrams = 1
        while len(data) < lenOfData:
            expectedDatagramNumber = jpgUdpCommon.nextDatagramNumber(datagramNumber)
            datagramNumber, recData = jpgUdpCommon.receiveDatagram(socket)
            if datagramNumber != expectedDatagramNumber:
                return '', False
            data += recData
            datagrams += 1
        self.infoLogger.info('image size: ' + str(lenOfData) + ', datagrams: ' + str(datagrams))
        return data, True        

    def run(self):
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.bind(jpgUdpCommon.ADDRESS)

        sock.settimeout(1.0)

        total_frames_read = 0
        total_frames_lost = 0
        frames_read_since_last_log = 0
        frames_lost_since_last_log = 0
    
        start_time = time.time()
        print('start_time: ' + str(start_time))
        time_last_log = start_time
        
        while self.threadRun:
            npString, ret = self.receiveImage(sock)
            if ret:
                #Unpack
                nparr = np.fromstring(npString, np.uint8)
                #img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
                img = cv2.imdecode(nparr, cv2.IMREAD_GRAYSCALE)
                self.frameQueue.put(img)
                total_frames_read += 1
                frames_read_since_last_log += 1
            else:
                total_frames_lost += 1
                frames_lost_since_last_log += 1
    
            now = time.time()
            diff_time = now - time_last_log
            if(diff_time > self.log_interval):
                time_last_log = now
                self.statisticsLogger.info('JpegUdpReader, received ' + str(frames_read_since_last_log) + ' frames at ' + \
                    str(float(frames_read_since_last_log) / diff_time) + ' frames/second' + '. And ' + \
                    str(frames_lost_since_last_log) + ' were lost.')
                print('JpegUdpReader, received ' + str(frames_read_since_last_log) + ' frames at ' + \
                    str(float(frames_read_since_last_log) / diff_time) + ' frames/second' + '. And ' + \
                    str(frames_lost_since_last_log) + ' were lost.')
                time_last_log = now
                frames_read_since_last_log = 0
    
        end_time = time.time()
        total_time = end_time - start_time
        self.statisticsLogger.info('JpegUdpReader done, received ' + str(total_frames_read) + \
            ' frames at ' + str(float(total_frames_read) / total_time) + ' frames/second' + '. And ' + \
                    str(total_frames_lost) + ' were lost.')
        print('JpegUdpReader done, received ' + str(total_frames_read) + \
            ' frames at ' + str(float(total_frames_read) / total_time) + ' frames/second' + '. And ' + \
                    str(total_frames_lost) + ' were lost.')



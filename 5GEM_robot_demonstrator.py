import logging
import threading
import re
import cv2
import urllib
import requests
import numpy as np 
import Queue
import time
import socket
import os, sys
import math
import custom_logger
import mjpeg_stream_reader
import face_detection

#Constants
STREAM_URL = 'http://129.16.214.222:9090/stream/video.mjpeg'
LOG_INTERVAL = 10
READ_CHUNK_SIZE = 32768
TOTAL_NR_OF_FRAMES = 500
WRITE_IMAGE_INTERVAL = 20

PI = math.pi
MINIMUM_ANGLE_MOVEMENT = PI / 20
IMAGE_WIDTH = 640
IMAGE_TOTAL_ANGLE = PI / 2

ANGLE_MIN = PI / 2
ANGLE_MAX = 5 * PI / 4

IMAGE_COOLDOWN_SECONDS = 10.0
COORDINATE_COOLDOWN_SECONDS = 3.0

PORT = 3000

ROBOT_COOLDOWN_SECONDS = 2

FACE_COOLDOWN_SECONDS = 2

logger = custom_logger.setup('5GEM_robot_demonstrator')

# square                Tuple of square (x, y, width, height)
# screen_width          Screen width in pixels
# angle_screen          Total angle in radians over the screen width (float)
def convert_square_on_screen_to_angle_in_x(square, screen_width, angle_screen):
    center_x = square[0] + (square[2] / 2)
    xDiff = float(float(screen_width / 2) - float(center_x))
    return float(xDiff * angle_screen) / float(screen_width)

class RobotCommunicator(threading.Thread): 
    def __init__(self, queue): 
        threading.Thread.__init__(self)
        self.s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.newFaceQueue = queue
        self.currentRadianValue = float(PI)
        self.lastSentValue = self.currentRadianValue
        self.faces = 0
        self.facesSkipped = 0
        
    def run(self):
        print("Setup socket")
        try:
            self.s.bind(('', PORT))
        except socket.error as msg:
            print 'Bind failed. Error Code : ' + str(msg[0]) + ' Message: ' + msg[1]
            sys.exit()
            
        self.s.listen(10)
        print 'Socket now listening'

        #wait to accept a connection - blocking call
        conn, addr = self.s.accept()
        print 'Connected with ' + addr[0] + ':' + str(addr[1])
            
        print("Socket bind ready!")
        dataSent = True
                
        while(True):
            if dataSent:
                data = conn.recv(1024)
            
            if(data == "OK" or dataSent == False):
                dataSent = False
                if(self.newFaceQueue.empty() == False):
                    while(self.newFaceQueue.empty() == False):
                        self.facesSkipped += 1
                        face = self.newFaceQueue.get()
                    
                    # Checks if the current message is the "Poison Pill"
                    if isinstance(face, str) and face == 'quit':
                        # if so, exit the loop
                        break
                    
                    self.currentRadianValue = self.currentRadianValue + \
                        convert_square_on_screen_to_angle_in_x(face, IMAGE_WIDTH, \
                        IMAGE_TOTAL_ANGLE)
                        
                    #Make sure the angle is within min/max
                    if(self.currentRadianValue < ANGLE_MIN):
                        self.currentRadianValue = ANGLE_MIN
                    if(self.currentRadianValue > ANGLE_MAX):
                        self.currentRadianValue = ANGLE_MAX
                        
                    if(abs(self.currentRadianValue - self.lastSentValue) > MINIMUM_ANGLE_MOVEMENT):
                        print 'Sending value = ' + str(self.currentRadianValue)
                        logger.info('Sending value = ' + str(self.currentRadianValue))
                        conn.send("(" + str(self.currentRadianValue) + ",0.300,-0.100,0.300,0,0,0)" + '\n')
                        dataSent = True
                        self.lastSentValue = self.currentRadianValue
            #End of while loop

        #Now we die!
        if dataSent:
            data = conn.recv(1024)
        conn.send("(3,0.300,-0.100,0.300,0,0,0)" + '\n')
        conn.close()
        print 'RobotCommunicator dies'
        print 'faces skipped: ' + str(self.facesSkipped)        

if __name__ == '__main__':
    imageQueue = Queue.Queue()
        
    reader = mjpeg_stream_reader.MjpegStreamReader(STREAM_URL, READ_CHUNK_SIZE, imageQueue, TOTAL_NR_OF_FRAMES, logger, LOG_INTERVAL)

    facePosQueue = Queue.Queue()
    robotCommunicatior = RobotCommunicator(facePosQueue)
    
    robotCommunicatior.start()
    reader.start()
    
    face_detection.detect(imageQueue, facePosQueue, logger, LOG_INTERVAL, WRITE_IMAGE_INTERVAL)
        
    facePosQueue.put('quit')
    robotCommunicatior.join()
    reader.join()
    
    print('Done')
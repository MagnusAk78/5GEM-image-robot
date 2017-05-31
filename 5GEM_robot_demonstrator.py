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
import jpeg_udp_reader
import face_detection
import SocketServer

#Constants
HOST, PORT = "", 3000
STREAM_URL = 'http://129.16.214.222:9090/stream/video.mjpeg'
#STREAM_URL = 'http://82.89.169.171:80/axis-cgi/mjpg/video.cgi?camera=&resolution=320x240'
LOG_INTERVAL = 10
READ_CHUNK_SIZE = 32768
WRITE_IMAGE_INTERVAL = 10
KEEP_ALIVE_INTERVAL = 1.0

RAD_TO_DEG_CONV = 57.2958
PI = math.pi
MINIMUM_ANGLE_MOVEMENT = PI / 30
IMAGE_WIDTH = 640
CENTER_X = IMAGE_WIDTH / 2
IMAGE_TOTAL_ANGLE = PI / 3

ANGLE_MIN = PI / 2
ANGLE_MAX = 5 * PI / 4

infoLogger = custom_logger.setup('5GEM_robot_demonstrator_info')
statisticsLogger = custom_logger.setup('5GEM_robot_demonstrator_stats')

# square                Tuple of square (x, y, width, height)
# screen_width          Screen width in pixels
# angle_screen          Total angle in radians over the screen width (float)
def convert_face_on_screen_to_angle_in_x(face, screen_width, angle_screen, logger):
    xDiff = float(CENTER_X - face.centerX())
    diffAngle = xDiff * PI / (IMAGE_WIDTH * 8)
    logger.info('xDiff: ' + str(xDiff) + ', diffAngle (deg): ' + str(diffAngle * RAD_TO_DEG_CONV))
    return diffAngle
    
class MyTCPHandler(SocketServer.BaseRequestHandler):
    """
    The request handler class for our server.

    It is instantiated once per connection to the server, and must
    override the handle() method to implement communication to the
    client.
    """

    def handle(self):
        print('Client connected')
        imageQueue = Queue.Queue()
        faceQueue = Queue.Queue()
        faceDetector = face_detection.FaceDetector(imageQueue, faceQueue, infoLogger, statisticsLogger, LOG_INTERVAL, WRITE_IMAGE_INTERVAL)
        faceDetector.start()
        jpegUdpReader = jpeg_udp_reader.JpegUdpReader(imageQueue, infoLogger, statisticsLogger, LOG_INTERVAL)
        jpegUdpReader.start()
        currentRadianValue = float(PI)
        lastSentValue = currentRadianValue
        lastSentTime = time.time()
        faces = 0
        facesSkipped = 0
        dataSent = True
        connectionOpen = True
        while connectionOpen:
            now = time.time()
            if dataSent:
                self.data = self.request.recv(1024).strip()
            if self.data == '':
                connectionOpen = False
            elif(self.data == "OK" or dataSent == False):
                dataSent = False
                if(faceQueue.empty() == False):
                    while(faceQueue.empty() == False):
                        facesSkipped += 1
                        face = faceQueue.get()
                    
                    # Checks if the current message is the "Poison Pill"
                    if isinstance(face, str) and face == 'quit':
                        # if so, exit the loop
                        break
                    elif isinstance(face, face_detection.Face):
                        currentRadianValue = currentRadianValue + convert_face_on_screen_to_angle_in_x(face, IMAGE_WIDTH, IMAGE_TOTAL_ANGLE, infoLogger)
                    else:
                        print("Something is very wrong")
                        break
                        
                    #Make sure the angle is within min/max
                    if(currentRadianValue < ANGLE_MIN):
                        currentRadianValue = ANGLE_MIN
                    if(currentRadianValue > ANGLE_MAX):
                        currentRadianValue = ANGLE_MAX
                        
                    if(abs(currentRadianValue - lastSentValue) > MINIMUM_ANGLE_MOVEMENT):
                        infoLogger.info('Sending value = ' + str(currentRadianValue))
                        self.request.sendall("(" + str(currentRadianValue) + ",0.300,-0.100,0.300,0,0,0)" + '\n')
                        dataSent = True
                        lastSentTime = now
                        lastSentValue = currentRadianValue
                
                #If nothing happens we need to send something to keep the connection alive
                if((now - lastSentTime) > KEEP_ALIVE_INTERVAL):
                        infoLogger.info('Sending value = ' + str(currentRadianValue) + ', *** keep alive ***')
                        self.request.sendall("(" + str(currentRadianValue) + ",0.300,-0.100,0.300,0,0,0)" + '\n')
                        dataSent = True
                        lastSentTime = now
                        lastSentValue = currentRadianValue
                        
            #End of while loop

        #Now we die!
        if dataSent:
            self.data = self.request.recv(1024).strip()
        self.request.sendall("(3,0.300,-0.100,0.300,0,0,0)" + '\n')
        
        print('Client disconnected')
        print 'faces skipped: ' + str(facesSkipped)
        
        faceDetector.stopThread()
        faceDetector.join()
        print('faceDetector stopped')
        jpegUdpReader.stopThread()
        jpegUdpReader.join()
        print('jpegUdpReader stopped')

if __name__ == "__main__":
    # Create the server, binding to localhost
    server = SocketServer.TCPServer((HOST, PORT), MyTCPHandler)

    # Activate the server; this will keep running until you
    # interrupt the program with Ctrl-C
    server.serve_forever()
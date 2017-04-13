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

#Constants
READ_CHUNK_SIZE = 16384 # 1024 => 4,78 fps, 4096 => 10,63 fps, 16384 => 15.69 fps, 32768 => 17.16 fps
NR_OF_FRAMES = 300
IMAGE_COOLDOWN_SECONDS = 10.0
COORDINATE_COOLDOWN_SECONDS = 3.0

#ROBOT_IP = "172.16.1.10"
#ROBOT_PORT = 30002

HOST = ""
PORT = 3000

ROBOT_COOLDOWN_SECONDS = 2

IMAGE_WIDTH = 640

PI = math.pi

logging.basicConfig(filename='image_robot.log',level=logging.DEBUG)

class RobotCommunicator(threading.Thread): 
    def __init__(self): 
        threading.Thread.__init__(self)
        self.s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.last_robot_send = 0
        self.stopped = False
        self.counter = 0
        self.currentFaceXPosition = -1
        
    def my_stop(self):
        self.stopped = True
        
    def setCurrentXPos(self, xPos):
        self.currentFaceXPosition = xPos
    
    def run(self):
        print("Setup socket to robot")
        try:
            self.s.bind((HOST, PORT))
        except socket.error as msg:
            print 'Bind failed. Error Code : ' + str(msg[0]) + ' Message: ' + msg[1]
            sys.exit()
            
        self.s.listen(10)
        print 'Socket now listening'

        #wait to accept a connection - blocking call
        conn, addr = self.s.accept()
        print 'Connected with ' + addr[0] + ':' + str(addr[1])
            
        print("Socket bind ready!")
        
        while(self.stopped == False):
            data = conn.recv(1024)
            if data == "OK":
                if(self.counter % 100 == 0):
                    print "OK received, currentFaceXPosition: " + str(self.currentFaceXPosition)
                value = 0
                if(self.currentFaceXPosition != -1):
                    value = (5*PI/4) - (self.currentFaceXPosition * (PI/(2*IMAGE_WIDTH)))
                else:
                    value = PI
                if(value > (PI/2) and value < (5*PI/4)):
                    conn.send("(" + str(value) + ",0.300,-0.100,0.300,0,0,0)" + '\n')
                else:
                    conn.send("(3,0.300,-0.100,0.300,0,0,0)" + '\n')
                self.counter = self.counter + 1

        #Now we die!
        data = conn.recv(1024)
        if data == "OK":
            conn.send("(3,0.300,-0.100,0.300,0,0,99)" + '\n')
        conn.close()
        print 'RobotCommunicator dies'


class ImageProcessor(threading.Thread): 
    def __init__(self, queue): 
        threading.Thread.__init__(self)
        self.imageQueue = queue
    	self.robotCommunicatior = RobotCommunicator()
        
    def run(self):
    	self.robotCommunicatior.start()
    	
        last_image_write = 0.0
        skipped = 0
        frames_read = 0
        face_cascade = cv2.CascadeClassifier('../opencv-3.1.0/data/haarcascades/haarcascade_frontalface_default.xml')
        eye_cascade = cv2.CascadeClassifier('../opencv-3.1.0/data/haarcascades/haarcascade_eye.xml')
        start_time = time.time()
        while True: 
            face = False
            # queue.get() blocks the current thread until 
            # an item is retrieved. 
            img = self.imageQueue.get() 
            # Checks if the current message is 
            # the "Poison Pill"
            if isinstance(img, str) and img == 'quit':
                # if so, exit the loop
                break
               
            #Only process images if the queue is empty
            if(self.imageQueue.empty()):
                # "Processes" the image
                
                now = time.time()
                if face and ((now - last_image_write) > IMAGE_COOLDOWN_SECONDS):
                    writeImg = True                
                
                #Convert to grayscale
                gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
                faces = face_cascade.detectMultiScale(gray, 1.3, 5)
                writeImg=False
                
                for(x,y,w,h) in faces:
                    middleX = x+w/2
                    middleY = x+w/2
                    
                    print "Face detected, middleX: " + str(middleX)
                    
                    #TODO: Handle multiple faces
                    self.robotCommunicatior.setCurrentXPos(middleX)
                    
                    logging.info('Face detected: ' + str(middleX) + ', ' + str(middleY))
                    face = True
                    
                    if writeImg:
                        print "Wrinting img"
                        cv2.rectangle(img, (x, y), (x+w, y+h), (255,0,0), 2)
                
                if writeImg:
                    cv2.imwrite('face' + str(frames_read) + '.jpg', img)
                    last_image_write = now

                frames_read += 1
            else:
                #We have skipped an image
                skipped+=1;
        
        self.robotCommunicatior.my_stop()
        diff_time = time.time() - start_time
        print 'ImageProcessor dies, read: ' + str(frames_read) + ', skipped: ' + str(skipped)
        print 'ImageProcessor handled ' + str(frames_read / diff_time) + ' frames/second'


def StreamReader(stream_url):
    frames_read = 0
    bytes = ''
    
    # Queue is used to share items between the threads.
    queue = Queue.Queue()
    
    # Create an instance of the imageProcessor
    imageProcessor = ImageProcessor(queue)
    # start calls the internal run() method to 
    # kick off the thread
    imageProcessor.start()
    
    stream = requests.get(stream_url, stream=True)

    print(stream.request.headers)
    
    start_time = time.time()
    
    while True:
        a = bytes.find('\xff\xd8')
        b = bytes.find('\xff\xd9')
    
        if a!=-1 and b!=-1:
            jpg = bytes[a:b+2]
            bytes = bytes[b+2:]
            #print("")
            #print("Frame found, jpg size: " + str(len(jpg)))
            #print("bytes: " + str(len(bytes)))
            img = cv2.imdecode(np.fromstring(jpg, dtype=np.uint8),cv2.IMREAD_COLOR)
            queue.put(img)
            frames_read += 1
        else:
            #We only read more data if there are no images in the buffer
            bytes += stream.raw.read(READ_CHUNK_SIZE)
    
        if(frames_read >= NR_OF_FRAMES):
            break
    
    # This the "poison pill" method of killing a thread.
    queue.put('quit')
    # wait for the thread to close down
    imageProcessor.join()
    
    diff_time = time.time() - start_time
    print 'StreamReader dies. Received: ' + str(frames_read) + ' frames.'
    print 'StreamReader received ' + str(frames_read / diff_time) + ' frames/second'

if __name__ == '__main__':
    stream_url = 'http://127.0.0.1:9090/stream/video.mjpeg'
    StreamReader(stream_url)

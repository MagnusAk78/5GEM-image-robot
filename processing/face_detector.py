import cv2
import numpy as np
import time
import sys
import math
import threading
import Queue
from processing import face

SHOW_IMAGE_ON_SCREEN = True
ADD_FAKED_DELAY = False
FAKED_DELAY = 0.3

FACE_CASCADE_PATH = './processing/haarcascades/haarcascade_frontalface_default.xml'
#   EYE_CASCADE_PATH = '../opencv-3.1.0/data/haarcascades/haarcascade_eye.xml'

# FACE_DETECTION_COOLDOWN determines how many seconds a face is 'remembered' after lost
FACE_DETECTION_COOLDOWN = 0.5

MAX_DISTANCE = 3.0        # % of size of face box
MAX_SIZE_DIFF = 1.2       # % of size of face box

def transfer_queue(source_queue, target_queue):
    target_queue.put(source_queue.get())
    
# frame_queue            Thread safe fifo queue where the frames are stored
# face_queue             Thread safe fifo queue where the located faces are stored
# logger                Logger
# log_interval           How long between every statistic log in seconds
# write_image_interval    Minimum time between image written to disk, 0 = no image write
class FaceDetector(threading.Thread): 
    def __init__(self, frame_queue, face_queue, info_logger, statistics_logger, log_interval, write_image_interval): 
        threading.Thread.__init__(self)
        self.threadRun = True
        if ADD_FAKED_DELAY:
            self.faked_delay_queue = frame_queue
            self.buffer_queue = Queue.Queue()
            self.read_queue = Queue.Queue()
        else:
            self.read_queue = frame_queue
        self.writeQueue = face_queue
        self.info_logger = info_logger
        self.statistics_logger = statistics_logger
        self.log_interval = log_interval
        self.write_image_interval = write_image_interval
        
    def stop_thread(self):
        self.threadRun = False
    
    def run(self):
        last_image_write = 0.0
        total_frames_processed = 0
        total_faces_detected = 0
        total_frames_skipped = 0
        frames_processed_since_last_log = 0
        faces_detected_since_last_log = 0
        frames_skipped_since_last_log = 0
        face_cascade = cv2.CascadeClassifier(FACE_CASCADE_PATH)
        #eye_cascade = cv2.CascadeClassifier(EYE_CASCADE_PATH)
        start_time = time.time()
        time_last_log = start_time
        currentFace = face.NO_FACE
        last_face_found_time = start_time
        
        while self.threadRun: 
            face_found = False
            
            if ADD_FAKED_DELAY:
                while self.read_queue.empty():
                    if self.faked_delay_queue.empty() == False:
                        img_now = self.faked_delay_queue.get()
                        self.buffer_queue.put(img_now)
                        threading.Timer(FAKED_DELAY, transfer_queue, (self.buffer_queue, self.read_queue)).start()
                    else:
                        time.sleep(0.005)
            
            img = self.read_queue.get()
            now = time.time()
                   
            #Only process images if the queue is empty
            if(self.read_queue.empty()):
                # "Processes" the image
                    
                #Convert to grayscale
                #gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
                faces = face_cascade.detectMultiScale(img, 1.3, 5)
                    
                nrOfFaces = 0
                
                write_image = False
                if((now - last_image_write) > self.write_image_interval):
                    write_image = True
                    
                currentDistance = float(sys.maxint)
                
                if(len(faces) == 1):
                    self.info_logger.info('Looping over 1 face')
                if(len(faces) > 1):    
                    self.info_logger.info('Looping over ' + str(len(faces)) + ' faces')
                    
                faces_detected_since_last_log += len(faces)
                total_faces_detected += len(faces)
                    
                for(x,y,w,h) in faces:
                    face_found = True
                    thisFace = face.Face(x,y,w,h)                
                    if currentFace != face.NO_FACE:
                        thisDistance = currentFace.distanceTo(thisFace)
                        thisSizeDiff = currentFace.sizeDiff(thisFace)
                        thisSize = thisFace.size()
                        if (thisDistance < (MAX_DISTANCE * thisSize)) and (thisSizeDiff < (MAX_SIZE_DIFF * thisSize)) and (thisDistance < currentDistance):
                            currentDistance = thisDistance
                            currentFace = thisFace
                            self.info_logger.info('Setting current face, dist: ' + str(currentDistance) + ', size diff: ' + str(thisSizeDiff))
                        else:
                            self.info_logger.info('Ignoring this face, dist: ' + str(currentDistance) + ', size diff: ' + str(thisSizeDiff))
                    else:
                        currentFace = thisFace
                        currentDistance = 0.0
                        self.info_logger.info('New current face, x: ' + str(x) + ', y: ' + str(y) + ', w: ' + str(w) + ', h: ' + str(h))
                        continue
                        
                if face_found:

                    if SHOW_IMAGE_ON_SCREEN:
                        cv2.rectangle(img, (currentFace.x, currentFace.y), \
                            (currentFace.x + currentFace.w, \
                            currentFace.y + currentFace.h), (255,0,0), 2)
                
                    self.writeQueue.put(currentFace)
                    last_face_found_time = now
                    if write_image:
                        #Write image
                        cv2.rectangle(img, (currentFace.x, currentFace.y), \
                            (currentFace.x + currentFace.w, \
                            currentFace.y + currentFace.h), (255,0,0), 2)
                        cv2.imwrite('face_' + str(total_frames_processed) + '.png', img)
                        last_image_write = now
                elif (currentFace != face.NO_FACE) and ((now - last_face_found_time) > FACE_DETECTION_COOLDOWN):
                        self.info_logger.info('Forgetting face')
                        currentFace = face.NO_FACE
                        
                if SHOW_IMAGE_ON_SCREEN:
                    cv2.imshow('Image', img)
                    cv2.waitKey(1)
                    
                total_frames_processed += 1
                frames_processed_since_last_log += 1
            else: #if(!self.read_queue.empty()):
                #We have skipped an image
                total_frames_skipped += 1
                frames_skipped_since_last_log += 1
                
            diff_time = now - time_last_log
            if(diff_time > self.log_interval):
                time_last_log = now
                self.statistics_logger.info('FaceDetector, processed ' + str(frames_processed_since_last_log) + \
                    ' frames at ' + str(float(frames_processed_since_last_log) / diff_time) + \
                    ' frames/second. ' + str(frames_skipped_since_last_log) + ' frames were skipped.' \
                    ' faces detected: ' + str(faces_detected_since_last_log))
                print('FaceDetector, processed ' + str(frames_processed_since_last_log) + \
                    ' frames at ' + str(float(frames_processed_since_last_log) / diff_time) + \
                    ' frames/second. ' + str(frames_skipped_since_last_log) + ' frames were skipped.' \
                    ' faces detected: ' + str(faces_detected_since_last_log))                    
                frames_skipped_since_last_log = 0
                frames_processed_since_last_log = 0
                faces_detected_since_last_log = 0
                faces_skipped_since_last_log = 0
        
        if SHOW_IMAGE_ON_SCREEN:
            cv2.destroyAllWindows()
        
        total_time = time.time() - start_time
        self.statistics_logger.info('FaceDetector done, processed ' + str(total_frames_processed) + \
            ' frames at ' + str(float(total_frames_processed) / total_time) + \
            ' frames/second. ' + str(total_frames_skipped) + ' frames were skipped. ' \
            ' Total faces detected: ' + str(total_faces_detected))
        print('FaceDetector done, processed ' + str(total_frames_processed) + \
            ' frames at ' + str(float(total_frames_processed) / total_time) + \
            ' frames/second. ' + str(total_frames_skipped) + ' frames were skipped. ' \
            ' Total faces detected: ' + str(total_faces_detected))

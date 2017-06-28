import cv2
import numpy as np
import time
import sys
import math
import threading
from processing import face

FACE_CASCADE_PATH = './processing/haarcascades/haarcascade_frontalface_default.xml'
#   EYE_CASCADE_PATH = '../opencv-3.1.0/data/haarcascades/haarcascade_eye.xml'

# FACE_DETECTION_COOLDOWN determines how many seconds a face is 'remembered' after lost
FACE_DETECTION_COOLDOWN = 0.5

MAX_DISTANCE = 3.0        # % of size of face box
MAX_SIZE_DIFF = 1.2       # % of size of face box
    
# frameQueue            Thread safe fifo queue where the frames are stored
# faceQueue             Thread safe fifo queue where the located faces are stored
# logger                Logger
# logInterval           How long between every statistic log in seconds
# writeImageInterval    Minimum time between image written to disk, 0 = no image write
class FaceDetector(threading.Thread): 
    def __init__(self, frameQueue, faceQueue, infoLogger, statisticsLogger, logInterval, writeImageInterval): 
        threading.Thread.__init__(self)
        self.threadRun = True
        self.readQueue = frameQueue
        self.writeQueue = faceQueue
        self.infoLogger = infoLogger
        self.statisticsLogger = statisticsLogger
        self.logInterval = logInterval
        self.writeImageInterval = writeImageInterval
        
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
            img = self.readQueue.get()
            now = time.time()
                   
            #Only process images if the queue is empty
            if(self.readQueue.empty()):
                # "Processes" the image
                    
                #Convert to grayscale
                #gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
                faces = face_cascade.detectMultiScale(img, 1.3, 5)
                    
                nrOfFaces = 0
                
                write_image = False
                if((now - last_image_write) > self.writeImageInterval):
                    write_image = True
                    
                currentDistance = float(sys.maxint)
                
                if(len(faces) == 1):
                    self.infoLogger.info('Looping over 1 face')
                if(len(faces) > 1):    
                    self.infoLogger.info('Looping over ' + str(len(faces)) + ' faces')
                    
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
                            self.infoLogger.info('Setting current face, dist: ' + str(currentDistance) + ', size diff: ' + str(thisSizeDiff))
                        else:
                            self.infoLogger.info('Ignoring this face, dist: ' + str(currentDistance) + ', size diff: ' + str(thisSizeDiff))
                    else:
                        currentFace = thisFace
                        currentDistance = 0.0
                        self.infoLogger.info('New current face, x: ' + str(x) + ', y: ' + str(y) + ', w: ' + str(w) + ', h: ' + str(h))
                        continue
                        
                if face_found:
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
                        self.infoLogger.info('Forgetting face')
                        currentFace = face.NO_FACE
                    
                total_frames_processed += 1
                frames_processed_since_last_log += 1
            else: #if(!self.readQueue.empty()):
                #We have skipped an image
                total_frames_skipped += 1
                frames_skipped_since_last_log += 1
                
            diff_time = now - time_last_log
            if(diff_time > self.logInterval):
                time_last_log = now
                self.statisticsLogger.info('FaceDetector, processed ' + str(frames_processed_since_last_log) + \
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
            
        total_time = time.time() - start_time
        self.statisticsLogger.info('FaceDetector done, processed ' + str(total_frames_processed) + \
            ' frames at ' + str(float(total_frames_processed) / total_time) + \
            ' frames/second. ' + str(total_frames_skipped) + ' frames were skipped. ' \
            ' Total faces detected: ' + str(total_faces_detected))
        print('FaceDetector done, processed ' + str(total_frames_processed) + \
            ' frames at ' + str(float(total_frames_processed) / total_time) + \
            ' frames/second. ' + str(total_frames_skipped) + ' frames were skipped. ' \
            ' Total faces detected: ' + str(total_faces_detected))

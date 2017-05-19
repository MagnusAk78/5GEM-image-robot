import cv2
import numpy as np
import time
import sys
import math

FACE_CASCADE_PATH = './haarcascades/haarcascade_frontalface_default.xml'
#   EYE_CASCADE_PATH = '../opencv-3.1.0/data/haarcascades/haarcascade_eye.xml'

# FACE_DETECTION_COOLDOWN determines how many seconds a face is 'remembered' after lost
FACE_DETECTION_COOLDOWN = 0.3

MIN_DISTANCE = 0.2      # % of diagonal of face box
MIN_SIZE_DIFF = 1.0     # % of diagonal of face box

NO_FACE_TUPLE = (-1,-1,-1,-1)

def __distance(tuple1, tuple2):
    center1 = (tuple1[0] + (tuple1[2] / 2), tuple1[1] + (tuple1[3] / 2))
    center2 = (tuple2[0] + (tuple2[2] / 2), tuple2[1] + (tuple2[3] / 2))
    distx = abs(center1[0] - center2[0])
    disty = abs(center1[1] - center2[1])
    return math.sqrt(distx * distx + disty * disty)
    
def __diagonal(tuple):
    return math.sqrt(tuple[2] * tuple[2] + tuple[3] * tuple[3])

def __sizeDiff(tuple1, tuple2):
    return abs(__diagonal(tuple1) - __diagonal(tuple2))
    
# read_queue            Thread safe fifo queue where the frames are stored, (Poison Pill: 'quit')
# write_queue           Thread safe fifo queue where the located faces are stored
# logger                Logger
# log_interval          How long between every statistic log in seconds
# write_image_interval  Minimum time between image written to disk, 0 = no image write
def detect(read_queue, write_queue, logger, log_interval, write_image_interval):
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
    current_face = NO_FACE_TUPLE
    last_face_found_time = start_time
    
    while True: 
        face_found = False
        img = read_queue.get()
        # Checks if the current message is the "Poison Pill"
        if isinstance(img, str) and img == 'quit':
            # if so, exit the loop
            break
               
        #Only process images if the queue is empty
        if(read_queue.empty()):
            # "Processes" the image
                
            #Convert to grayscale
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            faces = face_cascade.detectMultiScale(gray, 1.3, 5)
                
            nrOfFaces = 0
            
            write_image = False
            now = time.time()
            if((now - last_image_write) > write_image_interval):
                write_image = True
                
            distance_to_current_face = float(sys.maxint)
            
            logger.info('Looping over ' + str(len(faces)) + ' faces')
            for(x,y,w,h) in faces:
                face_found = True       
                faces_detected_since_last_log += 1
                total_faces_detected += 1                
                if current_face != NO_FACE_TUPLE:
                    tmp_distance = __distance(current_face, (x,y,w,h))
                    tmp_size_diff = __sizeDiff(current_face, (x,y,w,h))
                    diagonal = __diagonal(current_face)
                    if (tmp_distance < (MIN_DISTANCE * diagonal)) and (tmp_size_diff < (MIN_SIZE_DIFF * diagonal)) and (tmp_distance < distance_to_current_face):
                        distance_to_current_face = tmp_distance
                        current_face = (x,y,w,h)
                        logger.info('Setting current face, dist: ' + str(distance_to_current_face) + ', size diff: ' + str(tmp_size_diff))
                    else:
                        logger.info('Ignoring this face, dist: ' + str(distance_to_current_face) + ', size diff: ' + str(tmp_size_diff))
                else:
                    distance_to_current_face = 0.0
                    logger.info('New current face, x: ' + str(x) + ', y: ' + str(y) + ', w: ' + str(w) + ', h: ' + str(h))
                    current_face = (x,y,w,h)
                    
            if face_found:
                write_queue.put(current_face)
                last_face_found_time = now
                if write_image:
                    #Write image
                    cv2.rectangle(img, (current_face[0], current_face[1]), \
                        (current_face[0] + current_face[2], \
                        current_face[1] + current_face[3]), (255,0,0), 2)
                    cv2.imwrite('face_' + str(total_frames_processed) + '.png', img)
                    last_image_write = now
            elif (current_face != NO_FACE_TUPLE) and ((now - last_face_found_time) > FACE_DETECTION_COOLDOWN):
                    logger.info('Forgetting face')
                    current_face = NO_FACE_TUPLE
                
            total_frames_processed += 1
            frames_processed_since_last_log += 1
        else:
            #We have skipped an image
            total_frames_skipped += 1
            frames_skipped_since_last_log += 1
            
        now = time.time()
        diff_time = now - time_last_log
        if(diff_time > log_interval):
            time_last_log = now
            logger.info('face_detection, processed ' + str(frames_processed_since_last_log) + \
                ' frames at ' + str(float(frames_processed_since_last_log) / diff_time) + \
                ' frames/second. ' + str(frames_skipped_since_last_log) + ' frames were skipped.' \
                ' faces detected: ' + str(faces_detected_since_last_log))
            time_last_log = now
            frames_skipped_since_last_log = 0
            frames_processed_since_last_log = 0
            faces_detected_since_last_log = 0
            faces_skipped_since_last_log = 0
        
    total_time = time.time() - start_time
    logger.info('face_detection done, processed ' + str(total_frames_processed) + \
        ' frames at ' + str(float(total_frames_processed) / total_time) + \
        ' frames/second. ' + str(total_frames_skipped) + ' frames were skipped. ' \
        ' Total faces detected: ' + str(total_faces_detected))

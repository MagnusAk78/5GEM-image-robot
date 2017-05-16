import cv2
import numpy as np
import time
import sys

FACE_CASCADE_PATH = './haarcascades/haarcascade_frontalface_default.xml'
#   EYE_CASCADE_PATH = '../opencv-3.1.0/data/haarcascades/haarcascade_eye.xml'

FACE_DETECTION_COOLDOWN = 2.5

NO_FACE_TUPLE = (-1,-1,-1,-1)

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
                
            distance_to_current_face = sys.maxint
            
            for(x,y,w,h) in faces:                
                if current_face != NO_FACE_TUPLE:
                    tmp_distance = abs(x - current_face[0]) + abs(y - current_face[1]) + abs(w - current_face[2]) + abs(h - current_face[3])
                    if distance_to_current_face > tmp_distance:
                        distance_to_current_face = tmp_distance
                        current_face = (x,y,w,h)
                else:
                    current_face = (x,y,w,h)
                    
                face_found = True    
                faces_detected_since_last_log += 1
                total_faces_detected += 1
                    
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
            else:
                if (now - last_face_found_time) > FACE_DETECTION_COOLDOWN:
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

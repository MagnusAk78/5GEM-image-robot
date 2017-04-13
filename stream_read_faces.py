import logging
import threading
import re
import cv2
import urllib
import requests
import numpy as np 
import Queue
import time

#Constants
READ_CHUNK_SIZE = 16384 # 1024 => 4,78 fps, 4096 => 10,63 fps, 16384 => 15.69 fps, 32768 => 17.16 fps
NR_OF_FRAMES = 1000
IMAGE_COOLDOWN_SECONDS = 10.0

logging.basicConfig(filename='faces.log',level=logging.DEBUG)


class Consumer(threading.Thread): 
    def __init__(self, queue): 
        threading.Thread.__init__(self)
        self._queue = queue

    def run(self):
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
            img = self._queue.get() 
            # Checks if the current message is 
            # the "Poison Pill"
            if isinstance(img, str) and img == 'quit':
                # if so, exit the loop
                break
               
            #Only process images if the queue is empty
            if(self._queue.empty()):
                # "Processes" the image
                
                #Convert to grayscale
                gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
                faces = face_cascade.detectMultiScale(gray, 1.3, 5)
                for(x,y,w,h) in faces:
                    logging.info('Face detected: ' + str(x+w/2) + ', ' + str(y+h/2))
                    face = True
                    cv2.rectangle(img, (x, y), (x+w, y+h), (255,0,0), 2)
                    roi_gray = gray[y:y+h, x:x+w]
                    roi_color = img[y:y+h, x:x+w]
                    
                    eyes = eye_cascade.detectMultiScale(roi_gray, 1.3, 5)
                    for(ex,ey,ew,eh) in eyes:
                        cv2.rectangle(roi_color, (ex, ey), (ex+ew, ey+eh), (0,255,0), 2)
                
                now = time.time()
                if face and ((now - last_image_write) > IMAGE_COOLDOWN_SECONDS):
                        cv2.imwrite('face' + str(frames_read) + '.jpg', img)
                        last_image_write = now

                frames_read += 1
            else:
                #We have skipped an image
                skipped+=1;
                
        #Now we die!
        diff_time = time.time() - start_time
        print 'Consumer dies, read: ' + str(frames_read) + ', skipped: ' + str(skipped)
        print 'Consumer handled ' + str(frames_read / diff_time) + ' frames/second'


def Producer(stream_url):
    frames_read = 0
    bytes = ''
    
    # Queue is used to share items between the threads.
    queue = Queue.Queue()
    
    # Create an instance of the worker
    worker = Consumer(queue)
    # start calls the internal run() method to 
    # kick off the thread
    worker.start()    
    
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
    worker.join()
    
    diff_time = time.time() - start_time
    print 'Producer dies. Received: ' + str(frames_read) + ' frames.'
    print 'Producer received ' + str(frames_read / diff_time) + ' frames/second'

if __name__ == '__main__':
    stream_url = 'http://192.168.1.99:8080/stream/video.mjpeg'
    Producer(stream_url)

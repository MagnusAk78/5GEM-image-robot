import face_detection
import Queue
import custom_logger
import threading
import cv2
import time

TOTAL_TEST_TIME = 10

logger = custom_logger.setup('face_detection_test')

camera = cv2.VideoCapture(0)

class ImageProcessor(threading.Thread): 
    def __init__(self, queue):
        threading.Thread.__init__(self)
        self.imageQueue = queue
        self.facePosQueue = Queue.Queue()
        
    def run(self):
    	face_detection.detect(self.imageQueue, self.facePosQueue, logger, 3, 3)
        print 'ImageProcessor dies'


time.sleep(0.3)
stream_reader_queue = Queue.Queue()
imageProcessor = ImageProcessor(stream_reader_queue)
imageProcessor.start()
start_time = time.time()
while True:
    retval, image = camera.read()
    stream_reader_queue.put(image)
    cv2.imwrite("test.png", image)
    #time.sleep(0.02)
    if((time.time() - start_time) > TOTAL_TEST_TIME):
        break
camera.release()
stream_reader_queue.put('quit')
imageProcessor.join()
print 'Done'
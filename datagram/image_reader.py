import cv2
import numpy as np
import Queue
import threading
import socket
import datagram.data_transfer

# queue             Thread safe fifo queue where the frames are stored
# logger            Logger
# log_interval      How long between every statistic log in seconds

class ImageReader(threading.Thread): 
    def __init__(self, address, queue, info_logger, statistics_logger, log_interval): 
        threading.Thread.__init__(self)
        self.frame_queue = queue
        self.thread_run = True
        self.datagram_address = address
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.dataset_queue = Queue.Queue()
        self.dataset_receiver = datagram.data_transfer.DatasetReceiver(self.sock, self.dataset_queue, info_logger, statistics_logger, log_interval)
        
    def stop_thread(self):
        self.thread_run = False

    def run(self):
        self.sock.bind(self.datagram_address)

        self.sock.settimeout(1.0)
        
        self.dataset_receiver.start()
        
        while self.thread_run:
            np_string = self.dataset_queue.get()
            #Unpack
            nparr = np.fromstring(np_string, np.uint8)
            img = cv2.imdecode(nparr, cv2.IMREAD_GRAYSCALE)
            self.frame_queue.put(img)
            
        # Thread stopped
        self.dataset_receiver.stop_thread()
        self.dataset_receiver.join()
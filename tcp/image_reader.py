import cv2
import numpy as np
import Queue
import threading
import socket
import tcp.data_transfer

# queue             Thread safe fifo queue where the frames are stored
# logger            Logger
# log_interval      How long between every statistic log in seconds

class ImageReader(threading.Thread): 
    def __init__(self, address, read_buffer_size, queue, info_logger, statistics_logger, log_interval): 
        threading.Thread.__init__(self)
        self.frame_queue = queue
        self.thread_run = True
        self.socket_address = address
        self.read_buffer_size = read_buffer_size
        self.info_logger = info_logger
        self.statistics_logger = statistics_logger
        self.log_interval = log_interval
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        # Disable Nagle's algorithm
        self.sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        self.dataset_queue = Queue.Queue()
        
    def stop_thread(self):
        self.thread_run = False

    def run(self):
        self.sock.bind(self.socket_address)
        self.sock.listen(1)

        #self.sock.settimeout(1.0)
        connection, client_address = self.sock.accept()
        
        dataset_receiver = tcp.data_transfer.DatasetReceiver(connection, self.read_buffer_size, self.dataset_queue, self.info_logger, self.statistics_logger, self.log_interval)
        dataset_receiver.start()
        
        while self.thread_run:
            np_string = self.dataset_queue.get()
            #Unpack
            nparr = np.fromstring(np_string, np.uint8)
            img = cv2.imdecode(nparr, cv2.IMREAD_GRAYSCALE)
            self.frame_queue.put(img)
            
        # Thread stopped
        dataset_receiver.stop_thread()
        dataset_receiver.join()
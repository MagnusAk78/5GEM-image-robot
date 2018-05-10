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
    def __init__(self, address, read_buffer_size, queue, info_logger, statistics_logger, latency_logger, log_interval): 
        threading.Thread.__init__(self)
        self.setDaemon(True)
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
        self.latency_logger = latency_logger
        
    def stop_thread(self):
        self.thread_run = False

    def run(self):
        self.sock.bind(self.socket_address)
        
        dataset_receiver = tcp.data_transfer.DatasetReceiver(self.sock, self.read_buffer_size, self.dataset_queue, self.info_logger, self.statistics_logger, self.latency_logger, self.log_interval)
        dataset_receiver.start()
        
        while self.thread_run:
            np_string = self.dataset_queue.get()
            #Unpack
            nparr = np.fromstring(np_string, np.uint8)
            img = cv2.imdecode(nparr, cv2.IMREAD_GRAYSCALE)
            try:
                height, width = img.shape[:2]
            except AttributeError:
                self.info_logger.info('Image corrupt, AttributeError')
            except:
                self.info_logger.info('Image corrupt, some other error')
            else:
                self.frame_queue.put(img)
            
        # Thread stopped
        dataset_receiver.stop_thread()
        dataset_receiver.join(3.0)
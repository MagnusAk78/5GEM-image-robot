import logging
import timeit
import time
import csv
import threading
import Queue

LOG_TIME = 10.0

def setup_normal_logger(name):
    formatter = logging.Formatter(fmt='%(asctime)s.%(msecs)03d %(levelname)-8s %(message)s', \
        datefmt='%Y-%m-%d %H:%M:%S')
    handler = logging.FileHandler(name + '.log', mode='w')
    handler.setFormatter(formatter)
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)
    logger.addHandler(handler)
    return logger
    
class LatencyLogging(threading.Thread):
    def __init__(self, file_name):
        threading.Thread.__init__(self)
        self.setDaemon(True)
        self.threadRun = True
        if file_name.endswith(".csv") == False:
            file_name = file_name + ".csv"
        self.csv_writer = csv.writer(open(file_name, 'w'), delimiter=';', lineterminator='\n')
        self.image_send_latency_queue = Queue.Queue()
        self.image_received_queue = Queue.Queue()
        self.image_wait_processing_queue = Queue.Queue()
        self.image_process_start_queue = Queue.Queue()
        self.image_process_time_queue = Queue.Queue()
        
    def image_received(self, previous_round_trip_time, image_number):
        if previous_round_trip_time > 0.0:
            latency = previous_round_trip_time / 2
            self.image_send_latency_queue.put(latency)
        self.image_received_queue.put((image_number, timeit.default_timer()))
            
    def image_process_start(self, image_number):
        self.image_process_start_queue.put((image_number, timeit.default_timer()))
        while True or self.image_received_queue.empty():
            received_number, received_time = self.image_received_queue.get()
            if received_number == image_number:
                self.image_wait_processing_queue.put(timeit.default_timer() - received_time)
                break
                
    def image_process_end(self, image_number):
        while True or self.image_process_start_queue.empty():
            start_number, start_time = self.image_process_start_queue.get()
            if start_number == image_number:
                self.image_process_time_queue.put(timeit.default_timer() - start_time)
                break                
        
    def stop_thread(self):
        self.threadRun = False
    
    def run(self):
        self.csv_writer.writerow(("Timestamp", "Delta time", "Send image time (min)", "Send image time (max)", "Wait processing time (min)", "Wait processing time (max)", "Processing time (min)", "Processing time (max)"))
        start_time = timeit.default_timer()
        previous_log_time = start_time
        time.sleep(LOG_TIME)
        
        while self.threadRun: 
            now = timeit.default_timer()
            image_send_latency_list = []

            while(not self.image_send_latency_queue.empty()):
                image_send_latency_list.append(self.image_send_latency_queue.get())
            image_send_latency_min = -1
            image_send_latency_max = -1
            for image_send_latency in image_send_latency_list:
                if(image_send_latency_min == -1 or image_send_latency_min > image_send_latency):
                    image_send_latency_min = image_send_latency
                if(image_send_latency_max == -1 or image_send_latency_max < image_send_latency):
                    image_send_latency_max = image_send_latency
                    
            wait_processing_time_list = []            
            while(not self.image_wait_processing_queue.empty()):
                wait_processing_time_list.append(self.image_wait_processing_queue.get())
            image_wait_processing_time_min = -1
            image_wait_processing_time_max = -1
            for wait_processing_time in wait_processing_time_list:
                if(image_wait_processing_time_min == -1 or image_wait_processing_time_min > wait_processing_time):
                    image_wait_processing_time_min = wait_processing_time
                if(image_wait_processing_time_max == -1 or image_wait_processing_time_max < wait_processing_time):
                    image_wait_processing_time_max = wait_processing_time
                    
            processing_time_list = []            
            while(not self.image_process_time_queue.empty()):
                processing_time_list.append(self.image_process_time_queue.get())
            processing_time_min = -1
            processing_time_max = -1
            for processing_time in processing_time_list:
                if(processing_time_min == -1 or processing_time_min > processing_time):
                    processing_time_min = processing_time
                if(processing_time_max == -1 or processing_time_max < processing_time):
                    processing_time_max = processing_time                    
            
            self.csv_writer.writerow((str(now - start_time), str(now - previous_log_time), str(image_send_latency_min), str(image_send_latency_max), str(image_wait_processing_time_min), str(image_wait_processing_time_max), str(processing_time_min), str(processing_time_max)))
            previous_log_time = now
            time.sleep(LOG_TIME)

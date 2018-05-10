import logging
import timeit
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
        self.client_latency_queue = Queue.Queue()
        
    def add_client_latency(self, round_trip_time):
        latency = round_trip_time / 2
        self.client_latency_queue.add(latency)
        
    def stop_thread(self):
        self.threadRun = False
    
    def run(self):
        latest_log_time = timeit.default_timer()
        
        self.csv_writer.writerow([["Timestamp", "Delta time", "Client min latency", "Client max latency"]])
        
        while self.threadRun: 
            now = timeit.default_timer()
            diff_time = now - latest_log_time
            if(diff_time >= LOG_TIME):
                client_latency_list = []
                while(not self.client_latency_queue.empty()):
                    client_latency_list.append(self.client_latency_queue.get())
                client_latency_min = -1
                client_latency_max = -1
                for current_client_latency in client_latency_list:
                    if(client_latency_min == -1 or client_latency_min > current_client_latency):
                        client_latency_min = current_client_latency
                    if(client_latency_max == -1 or client_latency_max < current_client_latency):
                        client_latency_max = current_client_latency
                self.csv_writer.writerow([[str(now), str(diff_time), str(client_latency_min), str(client_latency_max)]])

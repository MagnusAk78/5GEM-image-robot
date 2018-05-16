import threading

class BaseRunnableClass():
    
    def __init__(self, info_logger):
        self.running = True
        self.info_logger = info_logger
        
    def stop_running(self):
        self.running = False
        
    def is_running(self):
        return self.running
        
    def log_info(self, log_string):
        self.info_logger.info(log_string)

class BaseThreadedClass(BaseRunnableClass, threading.Thread):
    
    def __init__(self, info_logger):
        threading.Thread.__init__(self)
        BaseRunnableClass.__init__(self, info_logger)
        self.setDaemon(True)
import logging

def setup(name):
    formatter = logging.Formatter(fmt='%(asctime)s.%(msecs)03d %(levelname)-8s %(message)s', \
        datefmt='%Y-%m-%d %H:%M:%S')
    handler = logging.FileHandler(name + '.log', mode='w')
    handler.setFormatter(formatter)
    custom_logger = logging.getLogger(name)
    custom_logger.setLevel(logging.DEBUG)
    custom_logger.addHandler(handler)
    return custom_logger


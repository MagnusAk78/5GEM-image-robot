import logging

def setup_normal_logger(name):
    formatter = logging.Formatter(fmt='%(asctime)s.%(msecs)03d %(levelname)-8s %(message)s', \
        datefmt='%Y-%m-%d %H:%M:%S')
    handler = logging.FileHandler(name + '.log', mode='w')
    handler.setFormatter(formatter)
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)
    logger.addHandler(handler)
    return logger


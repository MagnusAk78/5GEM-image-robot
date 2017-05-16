import mjpeg_stream_reader
import Queue
import custom_logger

READ_CHUNK_SIZE = 32768

#stream_url = 'http://pr_nh_webcam.axiscam.net:8000/mjpg/video.mjpg?resolution=704x480'
stream_url = 'http://webcam.st-malo.com/axis-cgi/mjpg/video.cgi?resolution=352x288'

queue = Queue.Queue()

logger = custom_logger.setup('mjpeg_stream_reader_test')

reader = mjpeg_stream_reader.MjpegStreamReader(stream_url, READ_CHUNK_SIZE, queue, 120, logger, 3)
reader.start()
reader.join()
print('Done')
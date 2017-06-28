import Queue
import time
import helpers.logger
import mjpeg.mjpeg_stream_reader

READ_CHUNK_SIZE = 32768
LOG_INTERVAL = 3

stream_url = 'http://pr_nh_webcam.axiscam.net:8000/mjpg/video.mjpg?resolution=704x480'
#stream_url = 'http://webcam.st-malo.com/axis-cgi/mjpg/video.cgi?resolution=352x288'

queue = Queue.Queue()

info_logger = helpers.logger.setup_normal_logger('test_mjpeg_stream_reader_info')
statistics_logger = helpers.logger.setup_normal_logger('test_mjpeg_stream_reader_stats')

reader = mjpeg.mjpeg_stream_reader.MjpegStreamReader(stream_url, READ_CHUNK_SIZE, queue, info_logger, statistics_logger, LOG_INTERVAL)
reader.start()

while True:
    time.sleep(0.3)
    #if key pressed
        #break

reader.stop_thread()
reader.join()
print('Done')
import Queue
import time
import socket
import SocketServer
import math
import cv2
import helpers.logger
import datagram.image_reader
import tcp.image_reader
import processing.face_detector
import processing.face

#Constants

LOG_INTERVAL = 10
WRITE_IMAGE_INTERVAL = 0
KEEP_ALIVE_INTERVAL = 1.0
SHOW_IMAGE_ON_SCREEN = False
FAKED_DELAY = 0.0

LISTEN_ROBOT_CLIENT_ADDRESS = ("", 3000)

# TCP VERSION
TCP_IP = ""
TCP_PORT = 3001
READ_BUFFER_SIZE = 16535
TCP_ADDRESS = (TCP_IP, TCP_PORT)

# UDP VERSION
DATAGRAM_IP = ""
DATAGRAM_PORT = 5000
DATAGRAM_ADDRESS = (DATAGRAM_IP, DATAGRAM_PORT)

# STREAM VERSION
STREAM_URL = 'http://127.0.0.1:9090/stream/video.mjpeg'
READ_CHUNK_SIZE = 32768

# Robot control and image setup (depends on image sender)
RAD_TO_DEG_CONV = 57.2958
PI = math.pi
MINIMUM_ANGLE_MOVEMENT = PI / 30
IMAGE_WIDTH = 640
CENTER_X = IMAGE_WIDTH / 2
IMAGE_TOTAL_ANGLE = PI / 3
ANGLE_MIN = PI / 2
ANGLE_MAX = 5 * PI / 4

# Logging
info_logger = helpers.logger.setup_normal_logger('5GEM_robot_demonstrator_info')
statistics_logger = helpers.logger.setup_normal_logger('5GEM_robot_demonstrator_stats')

# square                Tuple of square (x, y, width, height)
# screen_width          Screen width in pixels
# angle_screen          Total angle in radians over the screen width (float)
def convert_face_on_screen_to_angle_in_x(face, screen_width, angle_screen, logger):
    xDiff = float(CENTER_X - face.centerX())
    diffAngle = xDiff * PI / (IMAGE_WIDTH * 8)
    logger.info('xDiff: ' + str(xDiff) + ', diffAngle (deg): ' + str(diffAngle * RAD_TO_DEG_CONV))
    return diffAngle
    
class MyRobotConnection():
    
    def __init__(self, connection, client_address): 
        self.connection = connection
        self.client_address = client_address
        self.image_queue = Queue.Queue()
        self.face_queue = Queue.Queue()
        self.show_image_queue = Queue.Queue()
        self.faceDetector = processing.face_detector.FaceDetector(self.image_queue, self.face_queue, self.show_image_queue, SHOW_IMAGE_ON_SCREEN, FAKED_DELAY, info_logger, LOG_INTERVAL, WRITE_IMAGE_INTERVAL)
        # TCP VERSION
        self.imageReader = tcp.image_reader.ImageReader(TCP_ADDRESS, READ_BUFFER_SIZE, self.image_queue, info_logger, statistics_logger, LOG_INTERVAL)
        # UDP VERSION
        #self.imageReader = datagram.image_reader.ImageReader(DATAGRAM_ADDRESS, self.image_queue, info_logger, statistics_logger, LOG_INTERVAL)
        # STREAM VERSION
        #self.imageReader = mjpeg.mjpeg_stream_reader.MjpegStreamReader(STREAM_URL, READ_CHUNK_SIZE, self.image_queue, info_logger, statistics_logger, LOG_INTERVAL)        
        
    def handle_connection(self):
        print('Client connected: ' + self.client_address[0] + ':' + str(self.client_address[1]))
        self.faceDetector.start()
        self.imageReader.start()
        
        currentRadianValue = float(PI)
        lastSentValue = currentRadianValue
        lastSentTime = time.time()
        faces = 0
        facesSkipped = 0
        dataSent = True
        connectionOpen = True
        
        while connectionOpen:
            now = time.time()
            if dataSent:
                self.data = self.connection.recv(1024).strip()
            if self.data == '':
                connectionOpen = False
            elif(self.data == "OK" or dataSent == False):
                dataSent = False
                if(self.face_queue.empty() == False):
                    while(self.face_queue.empty() == False):
                        facesSkipped += 1
                        face = self.face_queue.get()
                    
                    if isinstance(face, processing.face.Face):
                        currentRadianValue = currentRadianValue + convert_face_on_screen_to_angle_in_x(face, IMAGE_WIDTH, IMAGE_TOTAL_ANGLE, info_logger)
                    else:
                        print("Something is very wrong")
                        break
                        
                    #Make sure the angle is within min/max
                    if(currentRadianValue < ANGLE_MIN):
                        currentRadianValue = ANGLE_MIN
                    if(currentRadianValue > ANGLE_MAX):
                        currentRadianValue = ANGLE_MAX
                        
                    if(abs(currentRadianValue - lastSentValue) > MINIMUM_ANGLE_MOVEMENT):
                        info_logger.info('Sending value = ' + str(currentRadianValue))
                        self.connection.sendall("(" + str(currentRadianValue) + ",0.300,-0.100,0.300,0,0,0)" + '\n')
                        dataSent = True
                        lastSentTime = now
                        lastSentValue = currentRadianValue
                
                #If nothing happens we need to send something to keep the connection alive
                if((now - lastSentTime) > KEEP_ALIVE_INTERVAL):
                        info_logger.info('Sending value = ' + str(currentRadianValue) + ', *** keep alive ***')
                        self.connection.sendall("(" + str(currentRadianValue) + ",0.300,-0.100,0.300,0,0,0)" + '\n')
                        dataSent = True
                        lastSentTime = now
                        lastSentValue = currentRadianValue
                
                if SHOW_IMAGE_ON_SCREEN and self.show_image_queue.empty() == False:
                    while self.show_image_queue.empty() == False:
                        img = self.show_image_queue.get()
                    cv2.imshow('Image', img)
                    cv2.waitKey(1)
            #End of while loop

        #Now we die!
        print('Client disconnecting')
        print 'faces skipped: ' + str(facesSkipped)        
        
        if SHOW_IMAGE_ON_SCREEN:
            cv2.destroyAllWindows()
        
        self.faceDetector.stop_thread()
        self.faceDetector.join()
        print('faceDetector stopped')
        self.imageReader.stop_thread()
        self.imageReader.join()
        print('imageReader stopped')
        print('Client disconnected')

if __name__ == "__main__":
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    # Disable Nagle's algorithm
    server_socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
    server_socket.bind(LISTEN_ROBOT_CLIENT_ADDRESS)
    
    try:
        server_socket.listen(1)
        print "Listening for client . . ."
        connection, client_address = server_socket.accept()
        new_robot_connection = MyRobotConnection(connection, client_address)
        new_robot_connection.handle_connection()
        connection.close()
    except KeyboardInterrupt:
        exit()

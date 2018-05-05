import Queue
import timeit
import socket
import math
import cv2
import helpers.logger
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
DEG_TO_RAD_CONV = 0.01744
PI = float(math.pi)
MINIMUM_ANGLE_MOVEMENT_X = 1 * DEG_TO_RAD_CONV
MAXIMUM_ANGLE_MOVEMENT_X = 20 * DEG_TO_RAD_CONV
MINIMUM_ANGLE_MOVEMENT_Y = 1 * DEG_TO_RAD_CONV
MAXIMUM_ANGLE_MOVEMENT_Y = 20 * DEG_TO_RAD_CONV
IMAGE_WIDTH = 640
IMAGE_HEIGHT = 480
CENTER_X = IMAGE_WIDTH / 2
CENTER_Y = IMAGE_HEIGHT / 2
IMAGE_TOTAL_ANGLE_X = 65 * DEG_TO_RAD_CONV
IMAGE_TOTAL_ANGLE_Y = 40 * DEG_TO_RAD_CONV
ANGLE_MIN_X = 90 * DEG_TO_RAD_CONV
ANGLE_MAX_X = 275 * DEG_TO_RAD_CONV
ANGLE_MIN_Y = -35 * DEG_TO_RAD_CONV
ANGLE_MAX_Y = 5 * DEG_TO_RAD_CONV
STARTING_ANGLE_X =  PI
STARTING_ANGLE_Y = -15 * DEG_TO_RAD_CONV

# Logging
info_logger = helpers.logger.setup_normal_logger('5GEM_robot_demonstrator_info')
statistics_logger = helpers.logger.setup_normal_logger('5GEM_robot_demonstrator_stats')

# square                Tuple of square (x, y, width, height)
# screen_width          Screen width in pixels
# angle_screen          Total angle in radians over the screen width (float)
def convert_face_on_screen_to_angle_in_x(face, screen_width, angle_screen, logger):
    xDiff = float(CENTER_X - face.centerX())
    diffAngleX = xDiff * angle_screen / IMAGE_WIDTH
    if diffAngleX > MAXIMUM_ANGLE_MOVEMENT_X:
        diffAngleX = MAXIMUM_ANGLE_MOVEMENT_X
    logger.info('xDiff: ' + str(xDiff) + ', diffAngleX (deg): ' + str(diffAngleX * RAD_TO_DEG_CONV) + ' AND diffAngleX (rad): ' + str(diffAngleX))
    return diffAngleX
    
def convert_face_on_screen_to_angle_in_y(face, screen_height, angle_screen, logger):
    yDiff = float(CENTER_Y - face.centerY())
    diffAngleY = yDiff * angle_screen / IMAGE_HEIGHT
    if diffAngleY > MAXIMUM_ANGLE_MOVEMENT_Y:
        diffAngleY = MAXIMUM_ANGLE_MOVEMENT_Y
    logger.info('yDiff: ' + str(yDiff) + ', diffAngleY (deg): ' + str(diffAngleY * RAD_TO_DEG_CONV) + ' AND diffAngleY (rad): ' + str(diffAngleY))
    return diffAngleY
    
class MyRobotConnection():
    
    def __init__(self, server_socket): 
        self.server_socket = server_socket
        self.connection = None
        #self.client_address = client_address
        self.image_queue = Queue.Queue()
        self.face_queue = Queue.Queue()
        self.show_image_queue = Queue.Queue()
        self.faceDetector = processing.face_detector.FaceDetector(self.image_queue, self.face_queue, self.show_image_queue, SHOW_IMAGE_ON_SCREEN, FAKED_DELAY, info_logger, LOG_INTERVAL, WRITE_IMAGE_INTERVAL)
        self.running = True
        self.robot_connected = False
        self.imageReader = tcp.image_reader.ImageReader(TCP_ADDRESS, READ_BUFFER_SIZE, self.image_queue, info_logger, statistics_logger, LOG_INTERVAL)
        
    def wait_for_robot_client(self):
        try:
            self.server_socket.listen(1)
            print "Listening for client . . ."
            self.connection, client_address = self.server_socket.accept()
            print('Client connected: ' + client_address[0] + ':' + str(client_address[1]))
            self.robot_connected = True
        except socket.error, exc:
            print('socket.error: %s' % exc)
            self.connection.close()
            self.robot_connected = False
            pass
        except KeyboardInterrupt:
            print('KeyboardInterrupt')
            self.running = False
        
    def run(self):
        self.faceDetector.start()
        self.imageReader.start()
    
        while self.running:
            if not self.robot_connected:
                self.wait_for_robot_client()
            try:
                if self.robot_connected:
                    self.handle_connection()
            except socket.error, exc:
                print('socket.error: %s' % exc)
                self.connection.close()
                self.robot_connected = False
                pass
            except KeyboardInterrupt:
                print('KeyboardInterrupt')
                self.running = False
            
        #This is the end!
        print('Closing the server')
        
        if self.connection != None:
            self.connection.close()
        self.server_socket.close()
        if SHOW_IMAGE_ON_SCREEN:
            cv2.destroyAllWindows()
    
        self.faceDetector.stop_thread()
        self.faceDetector.join(3.0)
        print('faceDetector stopped')
        self.imageReader.stop_thread()
        self.imageReader.join(3.0)
        print('imageReader stopped')
        print('Client disconnected')
        
    def handle_connection(self):
        currentRadianValueX = STARTING_ANGLE_X
        currentRadianValueY = STARTING_ANGLE_Y
        lastSentValueX = currentRadianValueX
        lastSentValueY = currentRadianValueY
        lastSentTime = timeit.default_timer()
        faces = 0
        facesSkipped = 0
        dataSent = True
        
        while self.running and self.robot_connected:
            now = timeit.default_timer()
            if dataSent:
                self.data = self.connection.recv(1024).strip()
            if self.data == '':
                self.connection.close()
                self.robot_connected = False
            elif(self.data == "OK" or dataSent == False):
                dataSent = False
                if(self.face_queue.empty() == False):
                    while(self.face_queue.empty() == False):
                        facesSkipped += 1
                        face = self.face_queue.get()
                    
                    if isinstance(face, processing.face.Face):
                        currentRadianValueX = currentRadianValueX + convert_face_on_screen_to_angle_in_x(face, IMAGE_WIDTH, IMAGE_TOTAL_ANGLE_X, info_logger)
                        currentRadianValueY = currentRadianValueY - convert_face_on_screen_to_angle_in_y(face, IMAGE_HEIGHT, IMAGE_TOTAL_ANGLE_Y, info_logger)
                    else:
                        print("Something is very wrong")
                        break
                        
                    #Make sure the angle is within min/max
                    if(currentRadianValueX < ANGLE_MIN_X):
                        currentRadianValueX = ANGLE_MIN_X
                    if(currentRadianValueX > ANGLE_MAX_X):
                        currentRadianValueX = ANGLE_MAX_X
                    #For the axe 4, we change the inequality because we are negative
                    if(currentRadianValueY < ANGLE_MIN_Y):
                        currentRadianValueY = ANGLE_MIN_Y
                    if(currentRadianValueY > ANGLE_MAX_Y):
                        currentRadianValueY = ANGLE_MAX_Y
                        
                    if((abs(currentRadianValueX - lastSentValueX)> MINIMUM_ANGLE_MOVEMENT_X or abs(currentRadianValueY - lastSentValueY) > MINIMUM_ANGLE_MOVEMENT_Y)):
                        info_logger.info('Sending value for X = ' + str(currentRadianValueX) + ' AND ' + \
                                        'sending value for Y = ' + str(currentRadianValueY))
                        self.connection.sendall("(" + str(currentRadianValueX) + "," + str(currentRadianValueY) + ")" + '\n')
                        dataSent = True
                        lastSentTime = now
                        lastSentValueX = currentRadianValueX
                        lastSentValueY = currentRadianValueY
                
                #If nothing happens we need to send something to keep the connection alive
                if((now - lastSentTime) > KEEP_ALIVE_INTERVAL):
                        info_logger.info('Sending values = ' + str(currentRadianValueX) + ' AND ' + str(currentRadianValueY) + ', *** keep alive ***')
                        self.connection.sendall("(" + str(currentRadianValueX) + "," + str(currentRadianValueY) + ")" + '\n')
                        dataSent = True
                        lastSentTime = now
                        lastSentValueX = currentRadianValueX
                        lastSentValueY = currentRadianValueY
                
                if SHOW_IMAGE_ON_SCREEN and self.show_image_queue.empty() == False:
                    while self.show_image_queue.empty() == False:
                        img = self.show_image_queue.get()
                    cv2.imshow('Image', img)
                    cv2.waitKey(1)
            #End of while loop

if __name__ == "__main__":
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    # Disable Nagle's algorithm
    server_socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
    server_socket.bind(LISTEN_ROBOT_CLIENT_ADDRESS)
    
    robot_connection = MyRobotConnection(server_socket)
    robot_connection.run()
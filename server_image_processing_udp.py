import Queue
import time
import socket
import math
import SocketServer
import helpers.logger
import datagram.image_reader
import processing.face_detector
import processing.face

#Constants

LISTEN_ROBOT_CLIENT_ADDRESS = ("17.0.0.6", 3000)

DATAGRAM_IP = "127.0.0.1"
DATAGRAM_PORT = 5000
DATAGRAM_ADDRESS = (DATAGRAM_IP, DATAGRAM_PORT)

LOG_INTERVAL = 10
WRITE_IMAGE_INTERVAL = 0
KEEP_ALIVE_INTERVAL = 1.0

RAD_TO_DEG_CONV = 57.2958
PI = math.pi
MINIMUM_ANGLE_MOVEMENT = PI / 30
IMAGE_WIDTH = 640
CENTER_X = IMAGE_WIDTH / 2
IMAGE_TOTAL_ANGLE = PI / 3

ANGLE_MIN = PI / 2
ANGLE_MAX = 5 * PI / 4

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
    
class MyTCPHandler(SocketServer.BaseRequestHandler):
    """
    The request handler class for our server.

    It is instantiated once per connection to the server, and must
    override the handle() method to implement communication to the
    client.
    """

    def handle(self):
        print('Client connected')
        imageQueue = Queue.Queue()
        faceQueue = Queue.Queue()
        faceDetector = processing.face_detector.FaceDetector(imageQueue, faceQueue, info_logger, LOG_INTERVAL, WRITE_IMAGE_INTERVAL)
        faceDetector.start()
        imageReader = datagram.image_reader.ImageReader(DATAGRAM_ADDRESS, imageQueue, info_logger, statistics_logger, LOG_INTERVAL)
        imageReader.start()
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
                self.data = self.request.recv(1024).strip()
            if self.data == '':
                connectionOpen = False
            elif(self.data == "OK" or dataSent == False):
                dataSent = False
                if(faceQueue.empty() == False):
                    while(faceQueue.empty() == False):
                        facesSkipped += 1
                        face = faceQueue.get()
                    
                    # Checks if the current message is the "Poison Pill"
                    if isinstance(face, str) and face == 'quit':
                        # if so, exit the loop
                        break
                    elif isinstance(face, processing.face.Face):
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
                        self.request.sendall("(" + str(currentRadianValue) + ",0.300,-0.100,0.300,0,0,0)" + '\n')
                        dataSent = True
                        lastSentTime = now
                        lastSentValue = currentRadianValue
                
                #If nothing happens we need to send something to keep the connection alive
                if((now - lastSentTime) > KEEP_ALIVE_INTERVAL):
                        info_logger.info('Sending value = ' + str(currentRadianValue) + ', *** keep alive ***')
                        self.request.sendall("(" + str(currentRadianValue) + ",0.300,-0.100,0.300,0,0,0)" + '\n')
                        dataSent = True
                        lastSentTime = now
                        lastSentValue = currentRadianValue
            #End of while loop

        #Now we die!
        if dataSent:
            self.data = self.request.recv(1024).strip()
        self.request.sendall("(3,0.300,-0.100,0.300,0,0,0)" + '\n')
        
        print('Client disconnected')
        print 'faces skipped: ' + str(facesSkipped)
        
        faceDetector.stop_thread()
        faceDetector.join()
        print('faceDetector stopped')
        imageReader.stop_thread()
        imageReader.join()
        print('imageReader stopped')

if __name__ == "__main__":
    # Create the server, binding to localhost
    server = SocketServer.TCPServer(LISTEN_ROBOT_CLIENT_ADDRESS, MyTCPHandler)
    
    # Disable Nagle's algorithm
    server.socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)

    # Activate the server; this will keep running until you
    # interrupt the program with Ctrl-C
    server.serve_forever()

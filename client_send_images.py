# Use PiCamera module (camera on Raspberry Pi)
PICAMERA = False

if PICAMERA:
    from picamera.array import PiRGBArray
    from picamera import PiCamera
import numpy as np
import cv2
import socket
import math
import struct
import time
import timeit
import helpers.logger
import tcp.data_transfer

# How often the client should print to notify it's alive
PRINT_INTERVAL = 5.0

# Image resoulution, frames per second, and image quality
X_RES = 640
Y_RES = 480
FPS = 10
TIME_BETWEEN_FRAMES = 1.0 / FPS
JPEG_QUALITY = 75

# TCP
TCP_HOST = "127.0.0.1"
TCP_PORT = 3001
TCP_ADDRESS = (TCP_HOST, TCP_PORT)

# UDP
UDP_HOST = "127.0.0.1"
UDP_PORT = 5000
UDP_ADDRESS = (UDP_HOST, UDP_PORT)

if PICAMERA:
    camera = PiCamera()
    camera.resolution = (X_RES, Y_RES)
    camera.framerate = FPS
    raw_capture = PiRGBArray(camera, size=(X_RES, Y_RES))
    print("x res: " + str(X_RES))
    print("y res: " + str(Y_RES))    
else:
    cap = cv2.VideoCapture(0)
    ret = cap.set(3, X_RES)
    ret = cap.set(4, Y_RES)
    print("x res: " + str(cap.get(3)))
    print("y res: " + str(cap.get(4)))
    
print("FPS: " + str(FPS))
print("JPEG_QUALITY: " + str(JPEG_QUALITY))    



sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
sock.connect(TCP_ADDRESS)

#
# Function handle_image
# Takes an image and sends it over TCP or UDP
#
def handle_image(image):
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    ret, buf = cv2.imencode('.jpeg', gray, [cv2.IMWRITE_JPEG_QUALITY, JPEG_QUALITY])

    if ret == True:
        npString = buf.tostring()
        #TCP
        tcp.data_transfer.send_dataset(sock, npString)
    else:
        print("cv2.imencode('.jpeg', gray, [cv2.IMWRITE_JPEG_QUALITY, JPEG_QUALITY]) failed")
        print("")

#
# Function handle_print
# Checks if it is time to print an I'm alive message with some info
#    
def handle_print(last_print_time, images_handled_since_last_print):
    now = timeit.default_timer()
    print_diff_time = now - last_print_time
    if print_diff_time > PRINT_INTERVAL:
        last_print_time = now
        print("Client is running. The last " + str(print_diff_time) + " seconds it has handled " + str(images_handled_since_last_print) + " images")
        images_handled_since_last_print = 0
    return last_print_time, images_handled_since_last_print

#
# main code starts here
#    
    
# allow the camera to warmup
time.sleep(0.1)

# reset vars
images_handled_since_last_print = 0
last_print_time = timeit.default_timer()

print("Client is starting. If nothing more is seen within " + str(PRINT_INTERVAL) + " seconds, the client probably failed to read any images.")
        
# If the client runs on a Raspberry Pi with a camera module
if PICAMERA:
    for frame in camera.capture_continuous(raw_capture, format="rgb", use_video_port=True):
        image = frame.array
        # Run the handle_image function
        handle_image(image)
        images_handled_since_last_print += 1
        last_print_time, images_handled_since_last_print = handle_print(last_print_time, images_handled_since_last_print)
        
        # clear the stream in preparation for the next frame
        raw_capture.truncate(0)

# If the client runs on a computer with a normal webcam        
else:        
    while(True):
        before = timeit.default_timer()
        ret, image = cap.read()
        if ret:
            # Run the handle_image function
            handle_image(image)
            images_handled_since_last_print += 1
            last_print_time, images_handled_since_last_print = handle_print(last_print_time, images_handled_since_last_print)
            
            # Sleep if needed so that images are handled approximately in the correct FPS 
            now = timeit.default_timer()
            diffTime = now - before
            sleepTime = TIME_BETWEEN_FRAMES - diffTime
            if sleepTime > 0:
                time.sleep(sleepTime)
                
    cap.release()

# Exiting
sock.close()


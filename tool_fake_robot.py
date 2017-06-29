import time
import socket
import helpers.logger
import datagram.image_reader
import processing.face_detector

#Constants

ADDRESS = ('127.0.0.1', 3000)

LOG_INTERVAL = 10

OK = 'OK'

info_logger = helpers.logger.setup_normal_logger('Fake_Robot')
    
if __name__ == "__main__":

    # Create the server, binding to localhost
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.connect(ADDRESS)
    
    while True:
        try:
            # Send data
            sock.sendall(OK)
            data = sock.recv(1024).strip()
            info_logger.info('received "%s"' % data)
            print('received "%s"' % data)
            time.sleep(0.3)
        except Error:
            print('Error' + Error)
    
    #End While
    print('closing socket')
    sock.close()

import time
import socket
import helpers.logger
import server_image_processing

#Constants

ADDRESS = ('127.0.0.1', 3000)

LOG_INTERVAL = 10

info_logger = helpers.logger.setup_normal_logger('Fake_Robot')
    
if __name__ == "__main__":

    # Create the server, binding to localhost
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    
    # Disable Nagle's algorithm
    # This should not be active since the robot probably doesn't support this
    # sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
    
    sock.settimeout(10)
    sock.connect(ADDRESS)
    
    while True:
        try:
            # Send data
            sock.sendall(server_image_processing.ROBOT_ACK)
            data = sock.recv(1024).strip()
            info_logger.info('received "%s"' % data)
            print 'received "%s"' % data
            time.sleep(0.2)
        except socket.error, exc:
            print "Caught exception socket.error : %s" % exc
            break
    
    #End While
    print('closing socket')
    sock.close()
    
    print('exiting')

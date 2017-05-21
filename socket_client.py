import socket
import sys

HOST, PORT = "localhost", 3000
data = " ".join(sys.argv[1:])

# Create a socket (SOCK_STREAM means a TCP socket)
sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

mess1 = "OK"

try:
    # Connect to server and send data
    sock.connect((HOST, PORT))
    i=10
    
    while i>0:
        sock.sendall(mess1)
        # Receive data from the server and shut down
        received = sock.recv(1024)
        print "Received: {}".format(received)    
        i-=1
    
    
finally:
    sock.close()


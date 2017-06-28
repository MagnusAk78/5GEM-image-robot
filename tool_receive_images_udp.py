import numpy as np
import cv2
import socket
import datagram.data_transfer

TIMEOUT = 1.0

HOST = "127.0.0.1"
PORT = 5000
ADDRESS = (HOST, PORT)

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.bind(ADDRESS)

sock.settimeout(TIMEOUT)

print("Receiving frames")

while(True):
    ret, datagram_number, npString = datagram.data_transfer.receive_dataset(sock)

    if ret:        
        #Unpack
        nparr = np.fromstring(npString, np.uint8)
        #img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        img = cv2.imdecode(nparr, cv2.IMREAD_GRAYSCALE)

        # Display the resulting frame
        cv2.imshow('img', img)
    
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

# When everything done, release the capture
cv2.destroyAllWindows()
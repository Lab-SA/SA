# Example: echo server
import socket

HOST, PORT = 'localhost', 7
SIZE = 1024
ENCODING = 'ascii'
data = 'testing'

sckt = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

try:
    print('[Echo Client] request:',data)
    sckt.connect((HOST, PORT))
    sckt.sendall(bytes(data + "\n", ENCODING))

    received = str(sckt.recv(SIZE), ENCODING)

    print("[EchoClient] Server response: ", received)
except:
    print("[EchoClient] Error: receive from server")
finally:
    sckt.close()

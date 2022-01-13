# Example: echo server with thread
import socketserver

HOST, PORT = 'localhost', 7
SIZE = 1024
ENCODING = 'ascii'

class EchoHandler(socketserver.BaseRequestHandler):
    def handle(self): # handle client's request
        print('[Echo Server] Client: ', self.client_address[0])
        self.data = str(self.request.recv(SIZE), ENCODING)  # receive client data
        print('[Echo Server] Client request: ', self.data)

        # send response
        response = self.data
        self.request.sendall(bytes(response, ENCODING))

class ThreadTCPServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
    pass

if __name__ == "__main__":
    with ThreadTCPServer((HOST, PORT), EchoHandler) as server:
        server.serve_forever()

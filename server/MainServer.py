import socket
import json
import time

class MainServer:
    host, port = 'localhost', 20
    SIZE = 1024
    ENCODING = 'ascii'
    t = 0 # threshold #temp
    interval = 10 # server waits in one round # second
    timeout = 10 #temp

    userNum = 0
    requests = []

    def __init__(self, tag) -> None:
        self.tag = tag
        pass

    def start(self):
        self.startTime = self.endTime = time.time()
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            self.serverSocket = s
            s.bind((self.host, self.port))
            s.settimeout(self.timeout)
            s.listen()
            print('[{0}] Server started'.format(self.tag))

            while (self.endTime - self.startTime) < self.interval:
                try:
                    clientSocket, addr = s.accept()
                    request = str(clientSocket.recv(self.SIZE), self.ENCODING)  # receive client data
                    print('[{0}] Client: {1}'.format(self.tag, addr))
                    print('[{0}] Client request: {1}'.format(self.tag, request))
                    self.userNum = self.userNum + 1

                    requestData = json.loads(request)
                    self.requests.append((clientSocket, requestData))
                except socket.timeout:
                    pass
                
                self.endTime = time.time()

        # check threshold
        if self.t > self.userNum:
            print('[{0}] Exception: insufficient {1} users with {2} threshold'.format(self.tag, self.userNum, self.t))
            raise Exception("Need at least {0} users, but only {1} user(s) responsed".format(self.t, self.userNum))
    
    # broadcast to all client (same response)
    def broadcast(self, response): # send response (broadcast)
        response_json = json.dumps(response)
        for client in self.requests:
            clientSocket = client[0]
            clientSocket.sendall(bytes(response_json, self.ENCODING))
        
        self.serverSocket.close()
        print('[{0}] Server finished'.format(self.tag))
    
    # send response for each client (different response)
    def foreach(self, response):
        # 'response' must be: { index: [response], ... }
        # 'requestData' must be: [ index, [...data] ... ]
        for (clientSocket, requestData) in self.requests:
            idx = requestData[0]
            response_json = json.dumps(response[idx])
            clientSocket.sendall(bytes(response_json, self.ENCODING))
        
        self.serverSocket.close()
        print('[{0}] Server finished'.format(self.tag))

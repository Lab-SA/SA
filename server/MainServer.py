from http import client
import socket
import json
import time

### deprecated
class MainServer:
    host = 'localhost'
    port = 20
    SIZE = 2048
    ENCODING = 'utf-8'
    t = 1 # threshold
    interval = 60 * 10 # server waits in one round # second
    timeout = 3 #temp

    userNum = 0
    requests = []

    def __init__(self, tag, port, num):
        self.tag = tag
        self.port = port
        self.num = num

    def start(self):
        self.requests = []
        self.startTime = self.endTime = time.time()
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            self.serverSocket = s
            s.bind((self.host, self.port))
            s.settimeout(self.timeout)
            s.listen()
            print(f'[{self.tag}] Server started')

            while (self.endTime - self.startTime) < self.interval:
                currentClient = socket
                try:
                    clientSocket, addr = s.accept()
                    currentClient = clientSocket

                    # receive client data
                    # client request must ends with "\r\n"
                    request = ''
                    while True:
                        received = str(clientSocket.recv(self.SIZE), self.ENCODING)
                        if received.endswith("\r\n"):
                            received = received.replace("\r\n", "")
                            request = request + received
                            break
                        request = request + received

                    requestData = json.loads(request)
                    if requestData['request'] != self.tag: # check request
                        # request must contain {request: tag}
                        raise AttributeError
                    else:
                        requestData.pop('request')
                    
                    print(f'[{self.tag}] Client: {addr}')
                    # print(f'[{self.tag}] Client request: {request}')

                    self.userNum = self.userNum + 1
                    self.requests.append((clientSocket, requestData))
                except socket.timeout:
                    pass
                except AttributeError:
                    print(f'[{self.tag}] Exception: invalid request at {self.tag}')
                    currentClient.sendall(bytes(f'Exception: invalid request at {self.tag}\r\n', self.ENCODING))
                    pass
                except:
                    print(f'[{self.tag}] Exception: invalid request or unknown server error')
                    currentClient.sendall(bytes('Exception: invalid request or unknown server error\r\n', self.ENCODING))
                    pass
                
                self.endTime = time.time()
                if self.userNum >= self.num:
                    break

        # check threshold
        if self.t > self.userNum:
            print(f'[{self.tag}] Exception: insufficient {self.userNum} users with {self.t} threshold')
            raise Exception(f"Need at least {self.t} users, but only {self.userNum} user(s) responsed")
    
    # broadcast to all client (same response)
    def broadcast(self, response): # send response (broadcast)
        response_json = json.dumps(response)
        for client in self.requests:
            clientSocket = client[0]
            clientSocket.sendall(bytes(response_json + "\r\n", self.ENCODING))
        
        self.serverSocket.close()
        print(f'[{self.tag}] Server finished')
    
    # send response for each client (different response)
    def foreach(self, response):
        # 'response' must be: { index: [response], ... }
        # 'requestData' must be: { index: [...data], ... }
        for (clientSocket, requestData) in self.requests:
            idx = 0
            for data in requestData.keys():
                idx = data
            response_json = json.dumps(response[idx])
            clientSocket.sendall(bytes(response_json + "\r\n", self.ENCODING))
        
        self.serverSocket.close()
        print(f'[{self.tag}] Server finished')
    
    # send response for each client (different response) with index
    def foreachIndex(self, response):
        # requestData and response's order MUST be same
        for idx, (clientSocket, requestData) in enumerate(self.requests):
            response_json = json.dumps(response[idx])
            clientSocket.sendall(bytes(response_json + "\r\n", self.ENCODING))

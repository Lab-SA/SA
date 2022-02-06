from http import client
import socket
import json
import time

class MainServer:
    host = 'localhost'
    port = 20
    SIZE = 2048
    ENCODING = 'utf-8'
    t = 1 # threshold
    interval = 5 # server waits in one round # second
    timeout = 3 #temp

    userNum = 0
    requests = []

    def __init__(self, tag, port):
        self.tag = tag
        self.port = port

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

                    request = str(clientSocket.recv(self.SIZE), self.ENCODING)  # receive client data
                    requestData = json.loads(request)
                    if requestData['request'] != self.tag: # check request
                        # request must contain {request: tag}
                        print(requestData)
                        print(self.tag)
                        raise AttributeError
                    else:
                        requestData.pop('request')
                    
                    print(f'[{self.tag}] Client: {addr}')
                    print(f'[{self.tag}] Client request: {request}')

                    self.userNum = self.userNum + 1
                    self.requests.append((clientSocket, requestData))
                except socket.timeout:
                    pass
                except AttributeError:
                    print(f'[{self.tag}] Exception: invalid request at {self.tag}')
                    currentClient.sendall(bytes(f'Exception: invalid request at {self.tag}', self.ENCODING))
                    pass
                except:
                    print(f'[{self.tag}] Exception: invalid request or unknown server error')
                    currentClient.sendall(bytes('Exception: invalid request or unknown server error', self.ENCODING))
                    pass
                
                self.endTime = time.time()

        # check threshold
        if self.t > self.userNum:
            print(f'[{self.tag}] Exception: insufficient {self.userNum} users with {self.t} threshold')
            raise Exception(f"Need at least {self.t} users, but only {self.userNum} user(s) responsed")
    
    # broadcast to all client (same response)
    def broadcast(self, response): # send response (broadcast)
        response_json = json.dumps(response)
        for client in self.requests:
            clientSocket = client[0]
            clientSocket.sendall(bytes(response_json, self.ENCODING))
        
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
            clientSocket.sendall(bytes(response_json, self.ENCODING))
        
        self.serverSocket.close()
        print(f'[{self.tag}] Server finished')

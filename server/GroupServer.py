import socket, json, time, threading

class GroupServer:
    host = 'localhost'
    port = 20
    SIZE = 2048
    ENCODING = 'utf-8'
    t = 1 # threshold
    interval = 5 # server waits in one round # second
    timeout = 3 #temp

    userNum = userNow = 0
    requests = {}
    requests_value = []

    def __init__(self, tag, tag_value, port, groupNum, userNum):
        self.tag = tag
        self.tag_value = tag_value
        self.port = port
        self.groupNum = groupNum
        self.userNum = userNum
        self.requests = { idx: [] for idx in range(groupNum) }

    def start(self):
        self.startTime = self.endTime = time.time()
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            self.serverSocket = s
            s.bind((self.host, self.port))
            s.settimeout(self.timeout)
            s.listen()
            print(f'[{self.tag}] Server started')

            for i in range(self.groupNum):
                # for each one group

                while (self.endTime - self.startTime) < self.interval:
                    currentClient = socket
                    try:
                        clientSocket, addr = s.accept()
                        currentClient = clientSocket

                        request = str(clientSocket.recv(self.SIZE), self.ENCODING)  # receive client data
                        requestData = json.loads(request)
                        if requestData['request'] == self.tag:
                            # {request: TAG, group: GROUP_INDEX, index: INDEX}
                            requestGroup = int(requestData['group'])
                            if requestGroup < i:
                                raise ValueError
                            self.requests[requestGroup].append((clientSocket, requestData))
                        elif requestData['request'] == self.tag_value and requestData['group'] == i: # check request and group
                            # {request: TAG_VALUE, group: GROUP_INDEX, index: INDEX, maskedxij: {idx: , ...}, encodedxij: {idx: , ...}, si: VALUE, codedsi: VALUE}
                            self.userNow = self.userNow + 1
                            self.requests_value.append((clientSocket, requestData))
                        else:
                            raise AttributeError
                        
                        requestData.pop('request')
                        print(f'[{self.tag}] Client: {addr}')
                        print(f'[{self.tag}] Client request: {request}')

                    except socket.timeout:
                        pass
                    except AttributeError:
                        print(f'[{self.tag}] Exception: invalid request at {self.tag}')
                        currentClient.sendall(bytes(f'Exception: invalid request at {self.tag}', self.ENCODING))
                        pass
                    except ValueError:
                        print(f'[{self.tag}] Exception: invalid request at group {i}')
                        currentClient.sendall(bytes(f'Exception: requested group is over', self.ENCODING))
                    except:
                        print(f'[{self.tag}] Exception: invalid request or unknown server error')
                        currentClient.sendall(bytes('Exception: invalid request or unknown server error', self.ENCODING))
                        pass
                    
                    self.endTime = time.time()

                # check threshold
                nextGroupRequests = len(self.requests[i+1])
                if self.t > self.userNow and self.t > nextGroupRequests:
                    print(f'[{self.tag}] Exception: insufficient {self.userNow} or {nextGroupRequests} users with {self.t} threshold')
                    raise Exception(f"Need at least {self.t} users, but only {self.userNow} in L and {nextGroupRequests} in L+1.")
                
                # send data of group l-1 to group L
                threading.Thread(target=self.foreach, args=(self.requests[i+1], self.requests_value))
    
    # send response to requests-client
    def foreach(self, requests, requests_value):
        for (clientSocket, requestData) in requests:
            response = {"maskedxij": {}, "encodedxij": {}, "si": {}, "codedsi": {}}
            targetIndex = requestData["index"]
            for value in requests_value:
                idx = value["index"]
                response["maskedxij"][idx] = value["maskedxij"][targetIndex]
                response["encodedxij"][idx] = value["encodedxij"][targetIndex]
                response["si"][idx] = value["si"]
                response["codedsi"][idx] = value["codedsi"]
            response_json = json.dumps(response)
            clientSocket.sendall(bytes(response_json, self.ENCODING))
    
    def close(self):
        self.serverSocket.close()
        print(f'[{self.tag}] Server finished')    

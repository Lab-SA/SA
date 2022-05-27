import socket, json, time, threading, random

class TurboBaseServer:
    host = 'localhost'
    port = 20
    SIZE = 2048
    ENCODING = 'utf-8'
    t = 1 # threshold
    interval = 100 # server waits in one round # second 5
    timeout = 100 #temp 3

    userNum = userNow = 0
    requests = {}
    requests_value = []
    drop_out = {}

    def __init__(self, tag, tag_value, tag_final, port, groupNum, userNum, perGroup):
        self.tag = tag
        self.tag_value = tag_value
        self.tag_final = tag_final
        self.port = port
        self.groupNum = groupNum
        self.userNum = userNum
        self.perGroup = perGroup
        self.finalUserNum = 0
        self.requests = [[] for i in range(groupNum+1)] # temp +1
        self.requestsNum = [0 for i in range(groupNum+1)] # temp +1
        self.requests_final = []

    def start(self):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            self.serverSocket = s
            s.bind((self.host, self.port))
            s.settimeout(self.timeout)
            s.listen()
            print(f'[{self.tag}] Server started')

            for i in range(self.groupNum):
                # for each one group
                self.startTime = self.endTime = time.time()
                self.requests_value = []

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
                        if requestData['request'] == self.tag:
                            # {request: TAG, group: GROUP_INDEX, index: INDEX}
                            requestGroup = int(requestData['group'])
                            if requestGroup < i:
                                raise ValueError
                            self.requests[requestGroup].append((clientSocket, requestData))
                            self.requestsNum[requestGroup] = self.requestsNum[requestGroup] + 1
                        elif requestData['request'] == self.tag_value and requestData['group'] == i: # check request and group
                            # {request: TAG_VALUE, group: GROUP_INDEX, index: INDEX, maskedxij: {idx: , ...}, encodedxij: {idx: , ...}, si: VALUE, codedsi: VALUE}
                            self.userNow = self.userNow + 1
                            self.requests_value.append(requestData)
                            self.drop_out[i-1] = requestData['drop_out']
                            currentClient.sendall(bytes(f'[{self.tag}] OK \r\n', self.ENCODING))
                        elif requestData['request'] == self.tag_final:
                            self.finalUserNum = self.finalUserNum + 1
                            self.requests_final.append(clientSocket)
                        else:
                            raise AttributeError
                        
                        requestData.pop('request')
                        print(f'[{self.tag}] Client: {addr}')
                        print(f'[{self.tag}] Client request: {request}')

                    except socket.timeout:
                        pass
                    except AttributeError:
                        print(f'[{self.tag}] Exception: invalid request at {self.tag}')
                        currentClient.sendall(bytes(f'Exception: invalid request at {self.tag} \r\n', self.ENCODING))
                        pass
                    except ValueError:
                        print(f'[{self.tag}] Exception: invalid request at group {i}')
                        currentClient.sendall(bytes(f'Exception: requested group is over \r\n', self.ENCODING))
                    except:
                        print(f'[{self.tag}] Exception: invalid request or unknown server error')
                        currentClient.sendall(bytes('Exception: invalid request or unknown server error \r\n', self.ENCODING))
                        pass
                    
                    self.endTime = time.time()
                    if self.userNow >= self.perGroup and self.requestsNum[i+1] >= self.perGroup:
                        break

                # check threshold
                nextGroupRequests = self.requestsNum[i+1]
                if self.t > self.userNow and self.t > nextGroupRequests:
                    print(f'[{self.tag}] Exception: insufficient {self.userNow} or {nextGroupRequests} users with {self.t} threshold')
                    raise Exception(f"Need at least {self.t} users, but only {self.userNow} in L and {nextGroupRequests} in L+1.")
                
                # send data of group L-1 to group L
                # threading.Thread(target=self.foreach, args=(self.requests[i+1], self.requests_value))
                self.sendTurboValue(self.requests[i+1], self.requests_value)
            
            # End of for loop
            # final stage
            self.sendFinalValue(self.finalUserNum, self.requests_final, self.requests_value)

            # close
            self.close()

    
    # send response to requests-client
    def sendTurboValue(self, requests, requests_value):
        for (clientSocket, requestData) in requests:
            response = {"maskedxij": {}, "encodedxij": {}, "si": {}, "codedsi": {}}
            targetIndex = str(requestData["index"])
            for value in requests_value:
                idx = value["index"]
                response["maskedxij"][idx] = value["maskedxij"][targetIndex]
                response["encodedxij"][idx] = value["encodedxij"][targetIndex]
                response["si"][idx] = value["si"]
                response["codedsi"][idx] = value["codedsi"]
            response_json = json.dumps(response)
            clientSocket.sendall(bytes(response_json + "\r\n", self.ENCODING))
    

    def sendFinalValue(self, finalUserNum, requests, requests_value):
        if finalUserNum < self.perGroup:
            raise Exception(f"Need at least {self.perGroup} users at final stage.")
        
        # random perGroup users
        finalGroup = random.sample(requests, self.perGroup)
        for i, clientSocket in enumerate(finalGroup):
            # Send final values to final group (size: perGroup)
            response = {"chosen": True, "maskedxij": {}, "encodedxij": {}, "si": {}, "codedsi": {}}
            for value in requests_value: # final values
                idx = value["index"]
                response["index"] = i
                response["maskedxij"][idx] = value["maskedxij"][str(i)]
                response["encodedxij"][idx] = value["encodedxij"][str(i)]
                response["si"][idx] = value["si"]
                response["codedsi"][idx] = value["codedsi"]
            response_json = json.dumps(response)
            clientSocket.sendall(bytes(response_json + "\r\n", self.ENCODING))
            requests.remove(clientSocket)

        # to other users
        for clientSocket in requests:
            clientSocket.sendall(bytes(json.dumps({"chosen": False}) + "\r\n", self.ENCODING))
    
        
    def close(self):
        self.serverSocket.close()
        print(f'[{self.tag}] Server finished')    

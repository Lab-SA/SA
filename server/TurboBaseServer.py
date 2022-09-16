import socket, json, time, random, sys, os, copy

sys.path.append(os.path.dirname(os.path.abspath(os.path.dirname(__file__))))

from BasicSA import getCommonValues
from Turbo import generateRandomVectorSet, reconstruct, computeFinalOutput
from CommonValue import TurboRound
import learning.federated_main as fl
import learning.models_helper as mhelper
from common import writeToExcel

class TurboServer:
    host = 'localhost'
    port = 7001
    SIZE = 2048
    ENCODING = 'utf-8'
    t = 1 # threshold
    interval = 60 * 10 # server waits in one round # second 5
    timeout = 3
    
    model = {}
    requests = []
    run_data = []

    requests_next = {}
    requests_value = []
    requests_final = []

    groupNum = 0
    perGroup = 0
    usersNum = 0
    R = 0

    n = userNow = 0
    users_keys = {}
    mask_u_dic = {}
    drop_out = {}
    alpha = beta = []

    def __init__(self, n, k, t, perGroup):
        self.n = n # MUST be multiple of perGroup
        self.k = k # Repeat the entire process k times
        self.t = t # threshold
        self.perGroup = perGroup # number of clients per group

    def start(self):
        self.serverSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.serverSocket.bind((self.host, self.port))
        self.serverSocket.settimeout(self.timeout)
        self.serverSocket.listen()
        print(f'[Turbo] Server started')

        # self.requests = {round.name: [] for round in TurboRound}
        self.requests = {TurboRound.SetUp.name: [], TurboRound.Final.name: []}
        self.userNum = {i: 0 for i in range(len(self.requests))} # only need 2 (setup, final)
        self.userNum[-1] = self.n

        for j in range(self.k): # for k times
            # time
            self.start = time.time()
            self.setupTime = 0
            self.totalTime = 0

            # init
            self.users_keys = {}
            self.mask_u_dic = {}
            self.drop_out = {}
            self.alpha = self.beta = []
            
            self.requests_value = []
            self.requests_final = []

            self.requests[TurboRound.Final.name] = []
            self.userNum[1] = 0

            # execute Turbo round
            for i, r in enumerate(TurboRound):
                if r.name == TurboRound.Turbo.name:
                    self.turbo()
                    continue
                elif r.name == TurboRound.TurboValue.name or r.name == TurboRound.TurboFinal.name:
                    continue
                elif r.name == TurboRound.Final.name: # range of i: [0, 1]
                    self.requests[TurboRound.SetUp.name] = []
                    self.userNum[0] = 0
                    i = 1
                
                self.startTime = self.endTime = time.time()
                while (self.endTime - self.startTime) < self.interval:
                    currentClient = socket
                    try:
                        clientSocket, addr = self.serverSocket.accept()
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
                        # request must contain {request: tag}
                        clientTag = requestData['request']
                        requestData.pop('request')
                        self.requests[clientTag].append((clientSocket, requestData))

                        print(f'[{r.name}] Client: {clientTag}/{addr}')

                        if TurboRound.SetUp.name == clientTag:
                            self.userNum[0] = self.userNum[0] + 1
                        elif TurboRound.Final.name == clientTag:
                            self.userNum[1] = self.userNum[1] + 1
                        
                    except socket.timeout:
                        pass
                    except:
                        print(f'[{self.__class__.__name__}] Exception: invalid request or unknown server error')
                        currentClient.sendall(bytes('Exception: invalid request or unknown server error\r\n', self.ENCODING))
                        pass
                    
                    self.endTime = time.time()
                    if r.name == TurboRound.Final.name:
                        if self.userNum[i] >= self.perGroup:
                            break
                    elif self.userNum[i] >= self.userNum[i-1]:
                        break

                # check threshold
                if self.t > self.userNum[i]:
                    print(f'[{self.__class__.__name__}] Exception: insufficient {self.userNum[i]} users with {self.t} threshold')
                    raise Exception(f"Need at least {self.t} users, but only {self.userNum[i]} user(s) responsed")
            
                # do
                self.saRound(r.name, self.requests[r.name])
            
            # End
            self.totalTime = round(time.time() - self.start, 4)
            self.run_data.append([j+1, self.accuracy, self.setupTime, self.totalTime])
            print("\n|---- {}: setupTime: {} totalTime: {} accuracy: {}%".format(j+1, self.setupTime, self.totalTime, self.accuracy))

        # End
        print(f'[{self.__class__.__name__}] Server finished')

        # write to excel
        writeToExcel('../../results/turbo.xlsx', self.run_data)

    def turbo(self):
        tag = TurboRound.Turbo.name
        tag_value = TurboRound.TurboValue.name
        tag_final = TurboRound.TurboFinal.name
        for i in range(self.groupNum):
            # for each one group
            self.startTime = self.endTime = time.time()
            self.requests_value = []
            self.userNow = 0

            while (self.endTime - self.startTime) < self.interval:
                currentClient = socket
                try:
                    clientSocket, addr = self.serverSocket.accept()
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
                    clientTag = requestData['request']
                    
                    print(f'[{tag}] Client: {clientTag}/{addr}')

                    if clientTag == tag:
                        # {request: TAG, group: GROUP_INDEX, index: INDEX}
                        requestGroup = int(requestData['group'])
                        if requestGroup < i:
                            raise ValueError
                        self.requests_next[requestGroup].append((clientSocket, requestData))
                        self.requestsNum[requestGroup] = self.requestsNum[requestGroup] + 1
                    elif clientTag == tag_value and requestData['group'] == i: # check request and group
                        # {request: TAG_VALUE, group: GROUP_INDEX, index: INDEX, maskedxij: {idx: , ...}, encodedxij: {idx: , ...}, si: VALUE, codedsi: VALUE}
                        self.userNow = self.userNow + 1
                        self.requests_value.append(requestData)
                        self.drop_out[i-1] = requestData['drop_out']
                        currentClient.sendall(bytes(f'[{tag}] OK \r\n', self.ENCODING))
                    elif clientTag == tag_final:
                        self.requestsNum[len(self.requestsNum)-1] = self.requestsNum[len(self.requestsNum)-1] + 1
                        self.requests_final.append(clientSocket)
                    else:
                        raise AttributeError
                    
                    requestData.pop('request')
                    #print(f'[{tag}] Client request: {request}')

                except socket.timeout:
                    pass
                except AttributeError:
                    print(f'[{tag}] Exception: invalid request at {tag}')
                    currentClient.sendall(bytes(f'Exception: invalid request at {tag} \r\n', self.ENCODING))
                    pass
                except ValueError:
                    print(f'[{tag}] Exception: invalid request at group {i}')
                    currentClient.sendall(bytes(f'Exception: requested group is over \r\n', self.ENCODING))
                except:
                    print(f'[{tag}] Exception: invalid request or unknown server error')
                    currentClient.sendall(bytes('Exception: invalid request or unknown server error \r\n', self.ENCODING))
                    pass
                
                self.endTime = time.time()
                if self.userNow >= self.perGroup and self.requestsNum[i+1] >= self.perGroup:
                    if i == self.groupNum-1 and self.requestsNum[i+1] < self.n: # temp
                        continue
                    break

            # check threshold
            nextGroupRequests = self.requestsNum[i+1]
            if self.t > self.userNow and self.t > nextGroupRequests:
                print(f'[{tag}] Exception: insufficient {self.userNow} or {nextGroupRequests} users with {self.t} threshold')
                raise Exception(f"Need at least {self.t} users, but only {self.userNow} in L and {nextGroupRequests} in L+1.")
            
            # send data of group L-1 to group L
            self.sendTurboValue(self.requests_next[i+1], self.requests_value)
        
        # End of for loop
        # final stage
        self.sendFinalValue(self.requests_final, self.requests_value)

    def saRound(self, tag, requests):
        if tag == TurboRound.SetUp.name:
            self.setUp(requests)
        elif tag == TurboRound.Final.name:
            self.final(requests)
    
    def setUp(self, requests):
        commonValues = getCommonValues()
        self.R = commonValues["R"]
        commonValues["n"] = self.n
        commonValues["t"] = self.t
        commonValues["perGroup"] = self.perGroup

        # generate common alpha/beta
        commonValues["alpha"], commonValues["beta"] = self.alpha, self.beta = generateRandomVectorSet(self.perGroup, commonValues["p"])

        usersNow = len(requests) # MUST be multiple of perGroup
        self.groupNum = int(usersNow / self.perGroup)
        self.mask_u_dic = {i:{} for i in range(self.groupNum)}
        self.requests_next = [[] for i in range(self.groupNum+1)]
        self.requestsNum = [0 for i in range(self.groupNum+1)]

        if self.model == {}:
            self.model = fl.setup()
        model_weights_list = mhelper.weights_to_dic_of_list(self.model.state_dict())
        user_groups = fl.get_user_dataset(usersNow)

        for i in range(self.groupNum):
            for j in range(self.perGroup):
                idx = i * self.perGroup + j

                response_ij = copy.deepcopy(commonValues)
                response_ij["group"] = i
                response_ij["index"] = j
                mask_u = random.randrange(1, self.R) # 1~R
                self.mask_u_dic[i][j] = mask_u
                response_ij["mask_u"] = mask_u
                response_ij["data"] = [int(k) for k in user_groups[idx]]
                response_ij["weights"] = model_weights_list

                response_json = json.dumps(response_ij)
                clientSocket = requests[idx][0]
                clientSocket.sendall(bytes(response_json + "\r\n", self.ENCODING))

        self.setupTime = round(time.time() - self.start, 4)

    def final(self, requests):
        final_tildeS = {}
        final_barS = {}

        for request in requests:
            requestData = request[1]  # (socket, data)
            index = int(requestData["index"])
            final_tildeS[index] = requestData["final_tildeS"]
            final_barS[index] = requestData["final_barS"]
            self.drop_out[self.groupNum-1] = requestData["drop_out"] # last group
        
        # reconstruct
        reconstruct(self.alpha, self.beta, final_tildeS, final_barS)

        # calculate sum of surviving user's mask_u
        for group, item in self.drop_out.items():
            group = int(group)
            for i in item: # drop out
                i = int(i)
                del self.mask_u_dic[group][i]
        
        # final value
        sum_weights = computeFinalOutput(final_tildeS, self.mask_u_dic)
        avg_weights = list(x/self.n for x in sum_weights)
        new_weights = mhelper.restore_weights_tensor(mhelper.default_weights_info, avg_weights)

        # update global model
        self.model.load_state_dict(new_weights)

        # End
        self.broadcast(requests, "[Server] End protocol")
        self.accuracy = round(fl.test_model(self.model), 4)
    
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
    

    def sendFinalValue(self, requests, requests_value):
        if len(requests) < self.perGroup:
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
    
    # broadcast to all client (same response)
    def broadcast(self, requests, response): # send response (broadcast)
        response_json = json.dumps(response)
        for client in requests:
            clientSocket = client[0]
            clientSocket.sendall(bytes(response_json + "\r\n", self.ENCODING))

    def close(self):
        self.serverSocket.close()
        print(f'[Turbo] Server finished')

if __name__ == "__main__":
    server = TurboServer(n=4, k=3, t=2, perGroup=2)
    server.start()

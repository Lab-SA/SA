import socket, json, time, sys, os

sys.path.append(os.path.dirname(os.path.abspath(os.path.dirname(__file__))))

import BalancedSA
from BasicSA import getCommonValues
from CommonValue import BalancedSARound
from dto.BalancedSetupDto import BalancedSetupDto
from ast import literal_eval
import learning.federated_main as fl
import learning.models_helper as mhelper
import learning.utils as utils

class BalancedSAServer:
    host = 'localhost'
    port = 7000
    SIZE = 2048
    ENCODING = 'utf-8'
    interval = 10 # server waits in one round # second
    timeout = 3
    totalRound = 4 # BalancedSA has 4 rounds

    userNum = {}
    requests = []

    model = {}
    users_keys = {}
    R = 0

    def __init__(self, n, k):
        self.n = n
        self.k = k # Repeat the entire process k times
        self.serverSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.serverSocket.bind((self.host, self.port))
        self.serverSocket.settimeout(self.timeout)

    def start(self):
        # start!
        self.serverSocket.listen()
        print(f'[{self.__class__.__name__}] Server started')
            
        for j in range(self.k): # for k times        
            # init
            self.users_keys = {}
            self.yu_list = []

            self.requests = {round.name: [] for round in BalancedSARound}
            self.userNum = {i: 0 for i in range(len(BalancedSARound))}
            self.userNum[-1] = self.n

            # execute BasicSA round (total 5)
            for i, r in enumerate(BalancedSARound):
                round = r.name
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

                        print(f'[{round}] Client: {clientTag}/{addr}')

                        if round == clientTag:
                            self.userNum[i] = self.userNum[i] + 1
                    except socket.timeout:
                        pass
                    except:
                        print(f'[{self.__class__.__name__}] Exception: invalid request or unknown server error')
                        currentClient.sendall(bytes('Exception: invalid request or unknown server error\r\n', self.ENCODING))
                        pass
                    
                    self.endTime = time.time()
                    if self.userNum[i] >= self.userNum[i-1]:
                        break

                # check time
                #if self.t > self.userNum[i]:
                #    print(f'[{self.__class__.__name__}] Exception: insufficient {self.userNum[i]} users with {self.t} threshold')
                #    raise Exception(f"Need at least {self.t} users, but only {self.userNum[i]} user(s) responsed")
            
                # do
                self.saRound(round, self.requests[round])
        
        # End
        # serverSocket.close()
        print(f'[{self.__class__.__name__}] Server finished')

    # broadcast to all client (same response)
    def broadcast(self, requests, response): # send response (broadcast)
        response_json = json.dumps(response)
        for client in requests:
            clientSocket = client[0]
            clientSocket.sendall(bytes(response_json + "\r\n", self.ENCODING))

    def saRound(self, tag, requests):
        if tag == BalancedSARound.SetUp.name:
            self.setUp(requests)
        elif tag == BalancedSARound.ShareMasks.name:
            self.shareMasks(requests)
        elif tag == BalancedSARound.Aggregation.name:
            self.aggregationInCluster(requests)
        elif tag == BalancedSARound.RemoveMasks.name:
            self.finalAggregation(requests)


    # broadcast common value
    def setUp(self, requests):
        usersNow = len(requests)
        
        commonValues = getCommonValues()
        self.g = commonValues["g"]
        self.p = commonValues["p"]
        self.R = commonValues["R"]

        if self.model == {}:
            self.model = fl.setup()
        model_weights_list = mhelper.weights_to_dic_of_list(self.model.state_dict())
        user_groups = fl.get_user_dataset(usersNow)

        self.clusterNum = 1                                         # temp
        self.perGroup = {i: 4 for i in range(self.clusterNum)}      # at least 4 nodes # TODO balanced clustering
        self.users_keys = {i: {} for i in range(self.clusterNum)}   # {clusterNum: {index: pk(:bytes)}}
        hex_keys = {i: {} for i in range(self.clusterNum)}          # {clusterNum: {index: pk(:hex)}}

        list_ri, list_Ri = BalancedSA.generateRandomNonce(self.clusterNum, self.g, self.p, self.R)
        c = 0
        for i in range(self.clusterNum): # get all users' public key
            ri = list_ri[i]
            for j in range(self.perGroup[i]):
                hex_keys[i][j] = requests[c][1]['pk']
                self.users_keys[i][j] = bytes.fromhex(hex_keys[i][j])
                c += 1
        
        c = 0
        for i in range(self.clusterNum):
            ri = list_ri[i]
            for j in range(self.perGroup[i]):
                response_ij = BalancedSetupDto(
                    n = usersNow, 
                    g = self.g, 
                    p = self.p, 
                    R = self.R, 
                    encrypted_ri = BalancedSA.encrypt(self.users_keys[i][j], bytes(str(ri), 'ascii')).hex(),
                    Ri = list_Ri[i],
                    cluster = i,
                    clusterN = self.perGroup[i],
                    cluster_keys = str(hex_keys[i]), # node's id and public key
                    index = j,
                    data = [int(k) for k in user_groups[c]],
                    weights= str(model_weights_list),
                )._asdict()
                response_json = json.dumps(response_ij)
                clientSocket = requests[c][0]
                clientSocket.sendall(bytes(response_json + "\r\n", self.ENCODING))
                c += 1
    

    def shareMasks(self, requests):
        response = {}


    def aggregationInCluster(self, requests):
        response = {}
    

    def finalAggregation(self, requests):
        response = {}
    

    def close(self):
        self.serverSocket.close()


if __name__ == "__main__":
    server = BalancedSAServer(n=4, k=1)
    server.start()

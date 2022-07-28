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
    requests = {}

    model = {}
    users_keys = {}
    R = 0

    IS = {} # intermediate sum
    RS = {} # reconstruction value

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

            requests = {round.name: {} for round in BalancedSARound}
            self.requests_clusters = {round.name: {} for round in BalancedSARound} # check completion of clusters
            requests[BalancedSARound.SetUp.name][0] = []

            # execute BasicSA round (total 5)
            for i, r in enumerate(BalancedSARound):
                round = r.name
                # self.startTime = self.endTime = time.time()
                # (self.endTime - self.startTime) < self.interval
                while True:
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
                        if clientTag == BalancedSARound.SetUp.name:
                            cluster = 0
                        else:
                            cluster = int(requestData['cluster'])
                        requests[clientTag][cluster].append((clientSocket, requestData))

                        print(f'[{round}] Client: {clientTag}/{addr}/{cluster}')

                    except socket.timeout:
                        # TODO check time
                        pass
                    except:
                        print(f'[{self.__class__.__name__}] Exception: invalid request or unknown server error')
                        currentClient.sendall(bytes('Exception: invalid request or unknown server error\r\n', self.ENCODING))
                        pass
        
                    if round == BalancedSARound.SetUp.name:
                        if len(requests[round][0]) >= self.n:
                            self.setUp(requests[round][0])
                            for round_t in BalancedSARound:
                                for c in range(self.clusterNum):
                                    requests[round_t.name][c] = []
                                    self.requests_clusters[round_t.name][c] = 1
                            break
                    else: # check all nodes in cluster sent request
                        for c in range(self.clusterNum):
                            if self.requests_clusters[round][c] == 1 and len(requests[round][c]) >= self.perGroup[c]:
                                self.saRound(round, requests[round][c], c)
                                self.requests_clusters[round][c] = 0
                        if sum(self.requests_clusters[round].values()) == 0:
                            if round == BalancedSARound.RemoveMasks.name:
                                self.finalAggregation()
                            break # end of this round

        # End
        # serverSocket.close()
        print(f'[{self.__class__.__name__}] Server finished')

    def saRound(self, tag, requests, cluster):
        if tag == BalancedSARound.ShareMasks.name:
            self.shareMasks(requests, cluster)
        elif tag == BalancedSARound.Aggregation.name:
            self.aggregationInCluster(requests, cluster)
        elif tag == BalancedSARound.RemoveMasks.name:
            self.removeDropoutMasks(requests, cluster)

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
    
    def shareMasks(self, requests, cluster):
        emask = {i: {} for i in range(self.perGroup[cluster])}
        pmask = {}
        for (clientSocket, requestData) in requests:
            index = requestData['index']
            pmask[index] = requestData['pmask']
            for k, mjk in requestData['emask'].items():
                emask[int(k)][index] = mjk

        # send response
        for (clientSocket, requestData) in requests:
            index = requestData['index']
            response = {"emask": emask[index], "pmask": pmask}
            response_json = json.dumps(response)
            clientSocket.sendall(bytes(response_json + "\r\n", self.ENCODING))

    def aggregationInCluster(self, requests, cluster):
        all_users = [i for i in range(self.perGroup[cluster])]
        survived = []
        for (clientSocket, requestData) in requests:
            survived.append(int(requestData['index']))
        dropout = list(set(all_users)-set(survived))

        response = {'dropout': dropout}
        response_json = json.dumps(response)
        if len(dropout) == 0: # no need RemoveMasks stage in this cluster (step3-1 x)
            self.requests_clusters[BalancedSARound.RemoveMasks.name][cluster] = 0

        S_list = []
        for (clientSocket, requestData) in requests:
            S_list.append(requestData['S'])
            clientSocket.sendall(bytes(response_json + "\r\n", self.ENCODING))

        self.IS[cluster] = list(sum(x) for x in zip(*S_list)) # sum

    def removeDropoutMasks(self, requests, cluster):
        RS = 0
        for (clientSocket, requestData) in requests:
            RS += int(requestData['RS'])
            clientSocket.sendall(bytes("OK" + "\r\n", self.ENCODING))
        self.IS[cluster] = list(map(lambda x : x + RS, self.IS[cluster]))
    
    def finalAggregation(self):
        new_weights = list(sum(x) for x in zip(*self.IS.values())) # sum
        print(new_weights)

    def close(self):
        self.serverSocket.close()


if __name__ == "__main__":
    server = BalancedSAServer(n=4, k=1)
    server.start()

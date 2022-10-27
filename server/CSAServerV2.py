import socket, json, time, sys, os, select

sys.path.append(os.path.dirname(os.path.abspath(os.path.dirname(__file__))))

import CSA
from CSAServer import CSAServer
from BasicSA import getCommonValues, convertToRealDomain
from CommonValue import CSARound
from dto.CSASetupDto import CSASetupDto
import learning.federated_main as fl
import learning.models_helper as mhelper
import learning.utils as utils

class CSAServerV2(CSAServer):
    def setUp(self, requests):
        usersNow = len(requests)

        commonValues = getCommonValues()
        self.g = commonValues["g"]
        self.p = commonValues["p"]
        self.R = commonValues["R"]

        if self.model == {}:
            self.model = fl.setup()
            # optional
            # prev_weights = mhelper.restore_weights_tensor(mhelper.default_weights_info, readWeightsFromFile())
            # self.model.load_state_dict(prev_weights)

        model_weights_list = mhelper.weights_to_dic_of_list(self.model.state_dict())

        U = {}
        for i, request in enumerate(requests):
            #1. PS, GPS 받기
            socket, requestData = request
            gi = requestData['GPS_i']
            gj = requestData['GPS_j']
            PS = requestData['PS']
            U[i] = [gi, gj, PS, request]

        a = 6
        b = 8
        k = 3
        rf = 2
        cf = 1
        t = 4
        C = CSA.clustering(a, b, k, rf, cf, U, t)

        self.clusterNum = len(C)
        self.clusters = []     # list of clusters' index
        self.perLatency = {}   # define maximum latency(latency level) per cluster
        self.num_items = {}    # number of dataset in cluster
        self.users_keys = {}   # {clusterIndex: {index: pk(:bytes)}}
        hex_keys = {}          # {clusterIndex: {index: pk(:hex)}}

        for i, cluster in C.items(): # get all users' public key
            self.clusters.append(i) # store clusters' index
            hex_keys[i] = {}
            self.users_keys[i] = {}
            self.perLatency[i] = 50 + i*5
            self.num_items[i] = 5000 - i * 1000
            self.survived[i] = [j for j, request in cluster]
            for j, request in cluster:
                hex_keys[i][j] = request[1]['pk']
                self.users_keys[i][j] = bytes.fromhex(hex_keys[i][j])

        user_groups = fl.get_user_dataset(self.survived, True, self.clusters, self.num_items)
        list_ri, list_Ri = CSA.generateRandomNonce(self.clusters, self.g, self.p)

        for i, cluster in C.items():
            ri = list_ri[i]
            clusterN = len(cluster)
            training_weight = self.num_items[i] / (self.num_items[i] * clusterN)
            for j, request in cluster:
                response_ij = CSASetupDto(
                    n = usersNow, 
                    g = self.g, 
                    p = self.p, 
                    R = self.R, 
                    encrypted_ri = CSA.encrypt(self.users_keys[i][j], bytes(str(ri), 'ascii')).hex(),
                    Ri = list_Ri[i],
                    cluster = i,
                    clusterN = clusterN,
                    cluster_indexes = self.survived[i],
                    cluster_keys = str(hex_keys[i]), # node's id and public key
                    index = j,
                    qLevel = self.quantizationLevel,
                    data = [int(k) for k in user_groups[i][j]],
                    weights= str(model_weights_list),
                    training_weight=training_weight,
                )._asdict()
                response_json = json.dumps(response_ij)
                clientSocket = request[0]
                clientSocket.sendall(bytes(response_json + "\r\n", self.ENCODING))


        # init
        self.isSetupOk = True
        for round_t in CSARound:
            for c in self.clusters:
                self.requests_clusters[round_t.name][c] = 1
                self.startTime[c] = time.time()
        for c in self.clusters:
            self.requests_clusters[CSARound.SetUp.name][c] = 0

        self.setupTime = round(time.time() - self.start, 4)

    def aggregationInCluster(self, requests, cluster):
        beforeN = len(self.survived[cluster])
        self.survived[cluster] = []
        for (clientSocket, requestData) in requests:
            self.survived[cluster].append(int(requestData['index']))

        # print(self.survived[cluster])
        response = {'survived': self.survived[cluster]}
        response_json = json.dumps(response)

        self.S_list[cluster] = {}
        for (clientSocket, requestData) in requests:
            self.S_list[cluster][int(requestData['index'])] = requestData['S']
            clientSocket.sendall(bytes(response_json + "\r\n", self.ENCODING))
        
        if len(self.survived[cluster]) == beforeN and self.isBasic: # no need RemoveMasks stage in this cluster (step3-1 x)
            self.requests_clusters[CSARound.RemoveMasks.name][cluster] = 0
            self.IS[cluster] = list(sum(x) % self.p for x in zip(*self.S_list[cluster].values())) # sum

        self.requests_clusters[CSARound.Aggregation.name][cluster] = 0
        self.startTime[cluster] = time.time() # reset start time

    def removeDropoutMasks(self, requests, cluster):
        if len(requests) != len(self.survived[cluster]): # dropout happened in recovery phase
            self.survived[cluster] = []
            for (clientSocket, requestData) in requests:
                self.survived[cluster].append(int(requestData['index']))
            response = {'survived': self.survived[cluster]}
            response_json = bytes(json.dumps(response) + "\r\n", self.ENCODING)
            for (clientSocket, requestData) in requests:
                clientSocket.sendall(response_json)
        else:
            surv_S_list = []
            RS = 0
            a = 0
            response = {'survived': []} # means no need to send RS
            response_json = bytes(json.dumps(response) + "\r\n", self.ENCODING)
            for (clientSocket, requestData) in requests:
                surv_S_list.append(self.S_list[cluster][int(requestData['index'])])
                RS += int(requestData['RS'])
                if not self.isBasic:
                    a += int(requestData['a'])
                clientSocket.sendall(response_json)
            self.IS[cluster] = list((sum(x) + RS - a) % self.p for x in zip(*surv_S_list))
            self.requests_clusters[CSARound.RemoveMasks.name][cluster] = 0

        self.startTime[cluster] = time.time() # reset start time
    
    def finalAggregation(self):
        sum_weights = list(sum(x) % self.p for x in zip(*self.IS.values())) # sum
        sum_weights = convertToRealDomain(sum_weights, self.quantizationLevel, self.p)

        # update global model
        new_weight = mhelper.restore_weights_tensor(mhelper.default_weights_info, sum_weights)
        final_userNum = sum(list(map(lambda c: len(self.survived[c]), self.survived.keys())))
        #self.n = final_userNum
        #average_weight = utils.average_weight(new_weight, final_userNum)
        #print(average_weight['conv1.bias'])

        #self.model.load_state_dict(average_weight)
        self.model.load_state_dict(new_weight)
        self.accuracy = round(fl.test_model(self.model), 4)

        self.totalTime = round(time.time() - self.start, 4)
        self.allTime = round(self.allTime + self.totalTime, 4)

if __name__ == "__main__":
    server = ''
    try:
        server = CSAServerV2(n=4, k=3, isBasic = True, qLevel=30) # Basic CSA
        server.start()
    except (KeyboardInterrupt, RuntimeError):
        server.writeResults()

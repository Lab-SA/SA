import socket, json, time, sys, os, select

sys.path.append(os.path.dirname(os.path.abspath(os.path.dirname(__file__))))

import CSA
from BasicSA import getCommonValues, convertToRealDomain
from CommonValue import CSARound
from dto.CSASetupDto import CSASetupDto
import learning.federated_main as fl
import learning.models_helper as mhelper
import learning.utils as utils
from common import writeToExcel, writeWeightsToFile, readWeightsFromFile

class CSAServer:
    host = 'localhost'
    port = 8000
    SIZE = 2048
    ENCODING = 'utf-8'
    interval = 10       # server waits in one round # second
    timeout = 3
    totalRound = 4      # CSA has 4 rounds
    verifyRound = 'verify'
    isBasic = True      # true if BasicCSA, else FullCSA
    quantizationLevel = 30
    filename = '../../results/csa.xlsx'

    startTime = {}
    clusterTime = {}
    userNum = {}
    requests = {}
    run_data = []

    model = {}
    clusters = []       # list of cluster index
    users_keys = {}     # clients' public key
    R = 0

    survived = {}       # active user group per cluster
    S_list = {}
    IS = {}             # intermediate sum

    def __init__(self, n, k, isBasic, qLevel):
        self.n = n
        self.k = k # Repeat the entire process k times
        self.quantizationLevel = qLevel
        self.isBasic = isBasic
        self.serverSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.serverSocket.bind((self.host, self.port))
        self.serverSocket.setblocking(False)

    def start(self):
        # start!
        self.serverSocket.listen(200)
        print(f'[{self.__class__.__name__}] Server started')

        requests = {r.name: {} for r in CSARound}
        self.requests_clusters = {r.name: {} for r in CSARound} # check completion of clusters
        requests[CSARound.SetUp.name][0] = []
        requests[self.verifyRound] = {} # for step 2: repete until all member share valid masks
        self.allTime = 0
        connections = [self.serverSocket]

        for j in range(self.k): # for k times
            # time
            self.start = time.time()
            self.setupTime = 0
            self.totalTime = 0
            self.isSetupOk = False

            # init
            self.users_keys = {}
            self.survived = {}
            self.S_list = {}
            self.IS = {}

            timeout = 3
            while True: # always listen
                readable, writable, exceptional = select.select(connections, [], [], timeout)

                if self.serverSocket in readable: # new connection on the listening socket
                    clientSocket, addr = self.serverSocket.accept()
                    clientSocket.setblocking(True)
                    clientSocket.settimeout(2)
                    connections.append(clientSocket)

                else: # reading from an established connection
                    for clientSocket in readable:
                        # receive client data
                        # client request must ends with "\r\n"
                        requestData = ''
                        try:
                            while True:
                                received = str(clientSocket.recv(self.SIZE), self.ENCODING)
                                #print(clientSocket.getpeername(), received, len(received))
                                if len(received) == 0: break
                                if received.endswith("\r\n"):
                                    received = received[:-2]
                                    requestData = requestData + received
                                    break
                                requestData = requestData + received
                        except socket.timeout:
                            if requestData.endswith("\r\n"):
                                requestData = requestData[:-2]

                        if len(requestData) == 0: break
                        if requestData.find('}\r\n{') > 0: # for multiple requests at once
                            requestData_all = requestData.split('\r\n')
                        else:
                            requestData_all = [requestData]

                        for requestOne in requestData_all:
                            requestData = json.loads(requestOne)
                            clientTag = requestData['request']
                            requestData.pop('request')
                            if clientTag == CSARound.SetUp.name:
                                cluster = 0
                            else:
                                cluster = int(requestData['cluster'])
                            requests[clientTag][cluster].append((clientSocket, requestData))

                            print(f'[{clientTag}] Client: {clientTag}/{cluster}')


                if not self.isSetupOk: # not yet setup this round
                    if len(requests[CSARound.SetUp.name][0]) >= self.n:
                        self.setUp(requests[CSARound.SetUp.name][0])
                        for round_t in CSARound:
                            for c in self.clusters:
                                requests[round_t.name][c] = []
                        requests[self.verifyRound] = {c: [] for c in self.clusters}
                        requests[CSARound.SetUp.name][0] = [] # clear
                else: # check all nodes in cluster sent request
                    now = time.time()

                    for c in self.clusters:
                        # check number of requests
                        nowN = len(self.survived[c])

                        if len(requests[self.verifyRound][c]) >= nowN: # verify ok
                            self.requests_clusters[CSARound.ShareMasks.name][c] = 0

                        for r in CSARound:
                            if self.requests_clusters[r.name][c] == 1 and len(requests[r.name][c]) >= nowN:
                                self.saRound(r.name, requests[r.name][c], c)
                                requests[r.name][c] = [] # clear

                        # check latency
                        if (now - self.startTime[c]) >= self.perLatency[c]: # exceed
                            print(now - self.startTime[c], self.perLatency[c])
                            for r in CSARound:
                                if r.name == CSARound.ShareMasks.name and len(requests[self.verifyRound][c]) >= 1:
                                    self.requests_clusters[CSARound.ShareMasks.name][c] = 0
                                    requests[self.verifyRound][c] = [] # clear
                                    break
                                elif self.requests_clusters[r.name][c] == 1:
                                    self.saRound(r.name, requests[r.name][c], c)
                                    requests[r.name][c] = [] # clear
                                    break

                    if sum(self.requests_clusters[CSARound.RemoveMasks.name].values()) == 0:
                        self.finalAggregation()
                        clusterData = []
                        for c in self.clusters:
                            clusterData.append(round(self.clusterTime[c] - self.start, 4))
                        self.run_data.append([j+1, self.accuracy, self.setupTime, self.totalTime] + clusterData)
                        print("\n|---- {}: setupTime: {} totalTime: {} accuracy: {}%".format(j+1, self.setupTime, self.totalTime, self.accuracy))
                        break # end of this round

        # End
        # serverSocket.close()
        print(f'[{self.__class__.__name__}] Server finished')
        print('\n|---- Total Time: ', self.allTime)

        # write to excel
        writeToExcel('../../results/csa.xlsx', self.run_data)

    def saRound(self, tag, requests, cluster):
        if tag == CSARound.ShareMasks.name:
            self.shareMasks(requests, cluster)
        elif tag == CSARound.Aggregation.name:
            self.aggregationInCluster(requests, cluster)
        elif tag == CSARound.RemoveMasks.name:
            self.removeDropoutMasks(requests, cluster)

    def setUp(self, requests):
        usersNow = len(requests)
        print('usersNow:', usersNow)

        self.clusterTime = {}

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
        user_groups = fl.get_user_dataset(usersNow)

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
        self.num_items = {}  # number of dataset in cluster
        self.users_keys = {}   # {clusterIndex: {index: pk(:bytes)}}
        hex_keys = {}          # {clusterIndex: {index: pk(:hex)}}

        for i, cluster in C.items(): # get all users' public key
            self.clusters.append(i) # store clusters' index
            hex_keys[i] = {}
            self.users_keys[i] = {}
            self.perLatency[i] = 15 + i*5
            self.num_items[i] = 400 + i * 50
            self.survived[i] = [j for j, request in cluster]
            for j, request in cluster:
                hex_keys[i][j] = request[1]['pk']
                self.users_keys[i][j] = bytes.fromhex(hex_keys[i][j])
        self.clusters.sort()

        user_groups = fl.get_user_dataset(self.survived, True, self.clusters, self.num_items)
        list_ri, list_Ri = CSA.generateRandomNonce(self.clusters, self.g, self.p)

        for i, cluster in C.items():
            ri = list_ri[i]
            #self.survived[i] = [j for j, request in cluster]
            clusterN = len(cluster)
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
                    training_weight=0,
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

    def shareMasks(self, requests, cluster):
        if len(requests) < 4: # remove this cluster if nodes < 4 (threshold)
            for (clientSocket, requestData) in requests:
                clientSocket.sendall(bytes(json.dumps({"process": False}) + "\r\n", self.ENCODING))
                self.clusters.remove(cluster)
                return

        emask = {}
        pmask = {}
        prev_survived = len(self.survived[cluster])
        self.survived[cluster] = []
        for (clientSocket, requestData) in requests:
            index = requestData['index']
            self.survived[cluster].append(int(index))
            pmask[index] = requestData['pmask']
            for k, mjk in requestData['emask'].items():
                k = int(k)
                if emask.get(k) is None:
                    emask[k] = {}
                emask[k][index] = mjk
        # print(self.survived[cluster])

        now_survived = len(self.survived[cluster])
        if prev_survived != now_survived and now_survived < 4: # remove this cluster if nodes < 4 (threshold)
            for (clientSocket, requestData) in requests:
                clientSocket.sendall(bytes(json.dumps({"process": False}) + "\r\n", self.ENCODING))
                self.clusters.remove(cluster)
                return

        # send response
        for (clientSocket, requestData) in requests:
            index = requestData['index']
            response = {'survived': self.survived[cluster], 'emask': emask[index], 'pmask': pmask}
            response_json = json.dumps(response)
            clientSocket.sendall(bytes(response_json + "\r\n", self.ENCODING))

        self.startTime[cluster] = time.time() # reset start time

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
            self.clusterTime[cluster] = time.time()

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
        self.clusterTime[cluster] = time.time()

    def finalAggregation(self):
        sum_weights = list(sum(x) % self.p for x in zip(*self.IS.values())) # sum
        sum_weights = convertToRealDomain(sum_weights, self.quantizationLevel, self.p)

        # update global model
        new_weight = mhelper.restore_weights_tensor(mhelper.default_weights_info, sum_weights)
        final_userNum = sum(list(map(lambda c: len(self.survived[c]), self.survived.keys())))
        #self.n = final_userNum
        average_weight = utils.average_weight(new_weight, final_userNum)
        #print(average_weight['conv1.bias'])

        self.model.load_state_dict(average_weight)
        self.accuracy = round(fl.test_model(self.model), 4)

        self.totalTime = round(time.time() - self.start, 4)
        self.allTime = round(self.allTime + self.totalTime, 4)

    def close(self):
        self.serverSocket.close()

    def writeResults(self):
        print(f'[{self.__class__.__name__}] Server finished cause by Interrupt')
        print('\n|---- Total Time: ', self.allTime)

        # write to excel
        writeToExcel(self.filename, self.run_data)
        writeWeightsToFile(mhelper.flatten_tensor(self.model.state_dict())[1])

if __name__ == "__main__":
    try:
        server = CSAServer(n=100, k=101, isBasic = True, qLevel=300) # Basic CSA
        # server = CSAServer(n=4, k=1, isBasic = False, qLevel=30) # Full CSA
        server.start()
    except (KeyboardInterrupt, RuntimeError):
        server.writeResults()

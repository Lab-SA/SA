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


class CSAServer:  # no training weight
    host = 'localhost'
    port = 8000
    SIZE = 2048
    ENCODING = 'utf-8'
    interval = 10  # server waits in one round # second
    totalRound = 4  # CSA has 4 rounds
    verifyRound = 'verify'
    isBasic = True  # true if BCSA, else FCSA
    quantizationLevel = 30
    filename = '../../results/csa.xlsx'  # save result of CSA

    startTime = {}  # start time of each step for checking latency
    clusterTime = {}  # running time for a cluster in one round
    userNum = {}
    requests = {}  # collection of requests from users
    run_data = []  # record and save the time during the entire run

    model = {}
    clusters = []  # list of cluster index
    users_keys = {}  # clients' public key
    R = 0

    survived = {}  # active user group per cluster
    S_list = {}
    IS = {}  # intermediate sum

    isFirst = True  # setup model at first

    def __init__(self, n, k, isBasic, qLevel):
        self.n = n
        self.k = k  # Repeat the entire process k times
        self.quantizationLevel = qLevel
        self.isBasic = isBasic  # isBasic == Ture: BCSA / False: FCSA

        # init server socket with non-blocking mode
        self.serverSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.serverSocket.bind((self.host, self.port))
        self.serverSocket.setblocking(False)
        self.isFirst = True

    def start(self):
        # start!
        self.serverSocket.listen(200)  # set queue size and listen requests
        print(f'[{self.__class__.__name__}] Server started')

        # keep requests by steps
        requests = {r.name: {} for r in CSARound}
        requests[CSARound.SetUp.name][0] = []  # in setup, cluster index is only 1 (clustering not yet done)
        requests[self.verifyRound] = {}  # for step 2: repeat until all member share valid masks

        # check completion of clusters
        # - requests_clusters[ROUND][CLUSTER_INDEX] == 0 means ROUND has been completed on that cluster(CLUSTER_INDEX)
        self.requests_clusters = {r.name: {} for r in CSARound}

        self.allTime = 0  # total running time of all rounds

        # use select for non-blocking mode
        connections = [self.serverSocket]

        for j in range(self.k):  # for k times
            # init time
            self.start = time.time()
            self.setupTime = 0
            self.totalTime = 0
            self.isSetupOk = False

            # init
            self.users_keys = {}
            self.survived = {}
            self.S_list = {}
            self.IS = {}

            timeout = 3  # socket timeout
            while True:  # always listen requests
                # select available requests
                readable, writable, exceptional = select.select(connections, [], [], timeout)

                if self.serverSocket in readable:  # new connection on the listening socket
                    # keep new client socket in collections
                    clientSocket, addr = self.serverSocket.accept()
                    clientSocket.setblocking(True)
                    clientSocket.settimeout(2)
                    connections.append(clientSocket)

                else:  # reading from an established connection
                    # this means client sends a new data through their socket
                    for clientSocket in readable:
                        # receive client data
                        # [RULE] client request must ends with "\r\n"
                        requestData = ''
                        try:
                            while True:
                                received = str(clientSocket.recv(self.SIZE), self.ENCODING)
                                if len(received) == 0: break
                                if received.endswith("\r\n"):
                                    received = received[:-2]  # remove "\r\n"
                                    requestData = requestData + received
                                    break
                                requestData = requestData + received
                        except socket.timeout:
                            if requestData.endswith("\r\n"):
                                requestData = requestData[:-2]

                        if len(requestData) == 0: break  # invalid socket/request
                        if requestData.find('}\r\n{') > 0:  # for multiple requests at once
                            requestData_all = requestData.split('\r\n')
                        else:
                            requestData_all = [requestData]

                        # handle all requests
                        for requestOne in requestData_all:
                            requestData = json.loads(requestOne)  # using JSON format
                            # [RULE] client must sends request with a TAG(: indicates what round the request is)
                            clientTag = requestData['request']
                            requestData.pop('request')
                            if clientTag == CSARound.SetUp.name:
                                cluster = 0
                            else:
                                cluster = int(requestData['cluster'])

                            # keep request by TAG(round info) and cluster index
                            requests[clientTag][cluster].append((clientSocket, requestData))

                            print(f'[{clientTag}] Client: {clientTag}/{cluster}')  # log

                if not self.isSetupOk:  # not yet setup this round
                    # set model at first of all round (this phase only runs once)
                    if len(requests[CSARound.SetUp.name][
                               0]) >= self.n:  # wait for the desired number of users(: n) to arrive
                        self.setUp(requests[CSARound.SetUp.name][0])

                        # init requests(dict) according to cluster information
                        for round_t in CSARound:
                            for c in self.clusters:
                                requests[round_t.name][c] = []
                        requests[self.verifyRound] = {c: [] for c in self.clusters}
                        requests[CSARound.SetUp.name][0] = []  # clear

                else:  # check all nodes in cluster sent request
                    now = time.time()

                    for c in self.clusters:
                        # check number of requests
                        nowN = len(self.survived[c])

                        if len(requests[self.verifyRound][c]) >= nowN:  # verify ok
                            self.requests_clusters[CSARound.ShareMasks.name][c] = 0

                        for r in CSARound:
                            if self.requests_clusters[r.name][c] == 1 and len(requests[r.name][c]) >= nowN:
                                self.saRound(r.name, requests[r.name][c], c)
                                requests[r.name][c] = []  # clear

                        # check latency
                        if (now - self.startTime[c]) >= self.perLatency[c]:  # exceed
                            for r in CSARound:
                                if r.name == CSARound.ShareMasks.name and len(requests[self.verifyRound][c]) >= 1:
                                    self.requests_clusters[CSARound.ShareMasks.name][c] = 0
                                    requests[self.verifyRound][c] = []  # clear
                                    break
                                elif self.requests_clusters[r.name][c] == 1:
                                    self.saRound(r.name, requests[r.name][c], c)
                                    requests[r.name][c] = []  # clear
                                    break

                    if sum(self.requests_clusters[CSARound.RemoveMasks.name].values()) == 0:
                        # this means all rounds have been completed before the final aggregation
                        self.finalAggregation()

                        # save running data
                        clusterData = []
                        for c in self.clusters:
                            clusterData.append(round(self.clusterTime[c] - self.start, 4))
                        self.run_data.append([j + 1, self.accuracy, self.setupTime, self.totalTime] + clusterData)
                        print("\n|---- {}: setupTime: {} totalTime: {} accuracy: {}%".format(j + 1,
                                                                                             self.setupTime,
                                                                                             self.totalTime,
                                                                                             self.accuracy))

                        break  # end of this round

        # End
        print(f'[{self.__class__.__name__}] Server finished')
        print('\n|---- Total Time: ', self.allTime)

        # write running data to excel
        writeToExcel('../../results/csa.xlsx', self.run_data)

    def saRound(self, tag, requests, cluster):
        # handle requests according to TAG(round)
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

        if self.isFirst:
            self.isFirst = False

            commonValues = getCommonValues()
            self.g = commonValues["g"]
            self.p = commonValues["p"]
            self.R = commonValues["R"]

            self.model = fl.setup()
            ### optional
            # : Use when you want to define base weights of model
            prev_weights = mhelper.restore_weights_tensor(mhelper.default_weights_info, readWeightsFromFile())
            self.model.load_state_dict(prev_weights)

            model_weights_list = mhelper.weights_to_dic_of_list(self.model.state_dict())

            U = {}
            for i, request in enumerate(requests):
                # get PS, GPS info
                socket, requestData = request
                gi = requestData['GPS_i']
                gj = requestData['GPS_j']
                PS = requestData['PS']
                U[i] = [gi, gj, PS, request]

            # set clustering parameters and do clustering
            a = 6
            b = 8
            k = 3  # means there are k+1 clusters levels
            rf = 2
            cf = 1
            t = 4  # constraint
            self.C = CSA.clustering(a, b, k, rf, cf, U, t)

            # init
            self.clusterNum = len(self.C)
            self.clusters = []      # list of clusters' index
            self.perLatency = {}    # define maximum latency(latency level) per cluster
            self.num_items = {}     # number of dataset in cluster
            self.users_keys = {}    # {clusterIndex: {index: pk(:bytes)}}
            hex_keys = {}           # {clusterIndex: {index: pk(:hex)}}

            # get all users' public key
            for i, cluster in self.C.items():
                self.clusters.append(i)  # store clusters' index
                hex_keys[i] = {}
                self.users_keys[i] = {}
                self.perLatency[i] = 10 + i * 5
                self.num_items[i] = 100 + i * 300
                self.survived[i] = [j for j, request in cluster]
                for j, request in cluster:
                    hex_keys[i][j] = request[1]['pk']
                    self.users_keys[i][j] = bytes.fromhex(hex_keys[i][j])
            self.clusters.sort()

            # get data set for each users
            user_groups = fl.get_user_dataset(self.survived, True, self.clusters, self.num_items)

            # generate ri and Ri
            list_ri, list_Ri = CSA.generateRandomNonce(self.clusters, self.g, self.p)

            # send init info to clients
            for i, cluster in self.C.items():
                ri = list_ri[i]
                clusterN = len(cluster)
                for j, request in cluster:
                    response_ij = CSASetupDto(
                        n=usersNow,
                        g=self.g,
                        p=self.p,
                        R=self.R,
                        encrypted_ri=CSA.encrypt(self.users_keys[i][j], bytes(str(ri), 'ascii')).hex(),
                        Ri=list_Ri[i],
                        cluster=i,
                        clusterN=clusterN,
                        cluster_indexes=self.survived[i],
                        cluster_keys=str(hex_keys[i]),  # node's id and public key
                        index=j,
                        qLevel=self.quantizationLevel,
                        data=[int(k) for k in user_groups[i][j]],
                        weights=str(model_weights_list),
                        training_weight=0,
                    )._asdict()
                    response_json = json.dumps(response_ij)
                    clientSocket = request[0]
                    clientSocket.sendall(bytes(response_json + "\r\n", self.ENCODING))
        else:  # just send weights of global model
            for i, cluster in self.C.items():
                self.survived[i] = [j for j, request in cluster]

            model_weights_list = mhelper.weights_to_dic_of_list(self.model.state_dict())
            response_json = bytes(json.dumps({'weights': str(model_weights_list)}) + "\r\n", self.ENCODING)
            for (clientSocket, requestData) in requests:
                clientSocket.sendall(response_json)

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
        if len(requests) < 4:  # remove this cluster if nodes < 4 (threshold)
            for (clientSocket, requestData) in requests:
                clientSocket.sendall(bytes(json.dumps({"process": False}) + "\r\n", self.ENCODING))
                self.clusters.remove(cluster)
                return

        # get encrypted masks and public masks of users
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

        # check threshold
        now_survived = len(self.survived[cluster])
        if prev_survived != now_survived and now_survived < 4:  # remove this cluster if nodes < 4 (threshold)
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

        self.startTime[cluster] = time.time()  # reset start time

    def aggregationInCluster(self, requests, cluster):
        # aggregate in a cluster using secure weight S

        # check survived users in cluster
        beforeN = len(self.survived[cluster])
        self.survived[cluster] = []
        for (clientSocket, requestData) in requests:
            self.survived[cluster].append(int(requestData['index']))
        response = {'survived': self.survived[cluster]}
        response_json = json.dumps(response)

        # get all S value and send survived users list
        self.S_list[cluster] = {}
        for (clientSocket, requestData) in requests:
            self.S_list[cluster][int(requestData['index'])] = requestData['S']
            clientSocket.sendall(bytes(response_json + "\r\n", self.ENCODING))

        # check threshold
        if len(self.survived[
                   cluster]) == beforeN and self.isBasic:  # no need RemoveMasks stage in this cluster (step3-1 x)
            self.requests_clusters[CSARound.RemoveMasks.name][cluster] = 0
            self.IS[cluster] = list(sum(x) % self.p for x in zip(*self.S_list[cluster].values()))  # sum
            self.clusterTime[cluster] = time.time()

        self.requests_clusters[CSARound.Aggregation.name][cluster] = 0
        self.startTime[cluster] = time.time()  # reset start time

    def removeDropoutMasks(self, requests, cluster):
        # recovery phase due to drop out or FCSA

        if len(requests) != len(self.survived[cluster]):  # dropout happened in recovery phase
            # repeat previous phase
            self.survived[cluster] = []
            for (clientSocket, requestData) in requests:
                self.survived[cluster].append(int(requestData['index']))
            response = {'survived': self.survived[cluster]}
            response_json = bytes(json.dumps(response) + "\r\n", self.ENCODING)
            for (clientSocket, requestData) in requests:
                clientSocket.sendall(response_json)
        else:
            # get RS and alpha value
            surv_S_list = []
            RS = 0
            a = 0
            response = {'survived': []}  # means no need to send RS
            response_json = bytes(json.dumps(response) + "\r\n", self.ENCODING)
            for (clientSocket, requestData) in requests:
                surv_S_list.append(self.S_list[cluster][int(requestData['index'])])
                RS += int(requestData['RS'])
                if not self.isBasic:
                    a += int(requestData['a'])
                clientSocket.sendall(response_json)

            # calculate IS value
            self.IS[cluster] = list((sum(x) + RS - a) % self.p for x in zip(*surv_S_list))
            self.requests_clusters[CSARound.RemoveMasks.name][cluster] = 0

        self.startTime[cluster] = time.time()  # reset start time
        self.clusterTime[cluster] = time.time()

    def finalAggregation(self):
        # do final aggregation: aggergate all IS value

        ### Use when you want to drop out one cluster for testing
        # del self.IS[1]

        # 1. sum all IS value
        sum_weights = list(sum(x) % self.p for x in zip(*self.IS.values()))  # sum

        # 2. dequantization (convert to real domain)
        sum_weights = convertToRealDomain(sum_weights, self.quantizationLevel, self.p)

        # 3. update global model
        new_weight = mhelper.restore_weights_tensor(mhelper.default_weights_info, sum_weights)
        final_userNum = sum(list(map(lambda c: len(self.survived[c]), self.survived.keys())))
        average_weight = utils.average_weight(new_weight, final_userNum)
        self.model.load_state_dict(average_weight)

        # 4. test model
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
        # writeWeightsToFile(mhelper.flatten_tensor(self.model.state_dict())[1])


if __name__ == "__main__":
    try:
        server = CSAServer(n=100, k=101, isBasic=True, qLevel=300)  # BCSA
        # server = CSAServer(n=4, k=1, isBasic = False, qLevel=30) # FCSA
        server.start()
    except (KeyboardInterrupt, RuntimeError, ZeroDivisionError):
        server.writeResults()

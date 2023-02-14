import json, time, sys, os

sys.path.append(os.path.dirname(os.path.abspath(os.path.dirname(__file__))))

import CSA
from CSAServer import CSAServer
from BasicSA import getCommonValues, convertToRealDomain
from CommonValue import CSARound
from dto.CSASetupDto import CSASetupDto
import learning.federated_main as fl
import learning.models_helper as mhelper
from common import readWeightsFromFile


class CSAServerV2(CSAServer):  # involves training weights based on CSAServer
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
            k = 3   # means there are k+1 clusters levels
            rf = 2  # the row index of the server cell
            cf = 1  # the column index of the server cell
            t = 4   # constraint
            self.C = CSA.clustering(a, b, k, rf, cf, U, t)

            # init
            self.clusterNum = len(self.C)
            self.clusters = []      # list of clusters' index
            self.clusterN = {}      # number of clients in cluster
            self.perLatency = {}    # define maximum latency(latency level) per cluster
            self.num_items = {}     # number of dataset in cluster
            self.users_keys = {}    # {clusterIndex: {index: pk(:bytes)}}
            hex_keys = {}           # {clusterIndex: {index: pk(:hex)}}

            # get all users' public key
            for i, cluster in self.C.items():
                self.clusters.append(i)  # store clusters' index
                hex_keys[i] = {}
                self.users_keys[i] = {}
                self.perLatency[i] = 30 + i * 5
                self.num_items[i] = 550 + i * 300
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
                self.clusterN[i] = clusterN = len(cluster)
                training_weight = self.num_items[i] / (self.num_items[i] * clusterN)
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
                        training_weight=training_weight,
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
        if len(self.survived[cluster]) == beforeN and self.isBasic:  # no need RemoveMasks stage in this cluster (step3-1 x)
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
        # do final aggregation: aggregate all IS value

        # 1. calculate sum of active items for aggregation with training weight
        sum_active_items = 0
        for c in self.clusters:
            sum_active_items += self.num_items[c] * len(self.survived[c])

        for c in self.clusters:
            ### Use when you want to drop out one cluster for testing
            # if c==1:
            #    del self.IS[c]
            #    continue

            # 2. dequantization (convert to real domain)
            self.IS[c] = convertToRealDomain(self.IS[c], self.quantizationLevel, self.p)

            # 3. apply training weight to IS value
            f = (self.num_items[c] * self.clusterN[c]) / sum_active_items
            self.IS[c] = list(f * x for x in self.IS[c])

        # 4. sum all IS value
        sum_weights = list(sum(x) for x in zip(*self.IS.values()))  # sum

        # 5. update global model
        new_weight = mhelper.restore_weights_tensor(mhelper.default_weights_info, sum_weights)
        self.model.load_state_dict(new_weight)

        # 6. test model
        self.accuracy = round(fl.test_model(self.model), 4)

        self.totalTime = round(time.time() - self.start, 4)
        self.allTime = round(self.allTime + self.totalTime, 4)


if __name__ == "__main__":
    server = ''
    try:
        server = CSAServerV2(n=100, k=101, isBasic=True, qLevel=300)  # BCSA
        # server = CSAServerV2(n=100, k=101, isBasic=False, qLevel=300)  # FCSA
        server.start()
    except (KeyboardInterrupt, RuntimeError, ZeroDivisionError):
        server.writeResults()

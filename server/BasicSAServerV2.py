import socket, json, time, copy, sys, os

sys.path.append(os.path.dirname(os.path.abspath(os.path.dirname(__file__))))

from BasicSA import getCommonValues, reconstructPvu, reconstructPu, reconstruct, generatingOutput
from CommonValue import BasicSARound
from ast import literal_eval
import learning.federated_main as fl
import learning.models_helper as mhelper
import learning.utils as utils

class BasicSAServerV2:
    host = 'localhost'
    port = 7000
    SIZE = 2048
    ENCODING = 'utf-8'
    t = 1 # threshold
    interval = 60 * 10 # server waits in one round # second
    timeout = 3 #temp
    totalRound = 5 # BasicSA has 5 rounds

    userNum = {}
    requests = []

    model = {}
    users_keys = {}
    yu_list = []
    R = 0

    def __init__(self, n, k, t):
        self.n = n
        self.k = k # Repeat the entire process k times
        self.t = t # threshold
        self.serverSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.serverSocket.bind((self.host, self.port))
        self.serverSocket.settimeout(self.timeout)
        self.serverSocket.listen()

    def start(self):
        # start!
        print(f'[{self.__class__.__name__}] Server started')
            
        for j in range(self.k): # for k times        
            # init
            self.users_keys = {}
            self.yu_list = []

            self.requests = {round.name: [] for round in BasicSARound}
            self.userNum = {i: 0 for i in range(len(BasicSARound))}
            self.userNum[-1] = self.n

            # execute BasicSA round (total 5)
            for i, r in enumerate(BasicSARound):
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

                # check threshold
                if self.t > self.userNum[i]:
                    print(f'[{self.__class__.__name__}] Exception: insufficient {self.userNum[i]} users with {self.t} threshold')
                    raise Exception(f"Need at least {self.t} users, but only {self.userNum[i]} user(s) responsed")
            
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
    
    # send response for each client (different response)
    def foreach(self, requests, response):
        # 'response' must be: { index: [response], ... }
        # 'requestData' must be: { index: [...data], ... }
        for (clientSocket, requestData) in requests:

            idx = 0
            for data in requestData.keys():
                idx = data
            response_json = json.dumps(response[idx])
            clientSocket.sendall(bytes(response_json + "\r\n", self.ENCODING))

    def saRound(self, tag, requests):
        if tag == BasicSARound.SetUp.name:
            self.setUp(requests)
        elif tag == BasicSARound.AdvertiseKeys.name:
            self.advertiseKeys(requests)
        elif tag == BasicSARound.ShareKeys.name:
            self.shareKeys(requests)
        elif tag == BasicSARound.MaskedInputCollection.name:
            self.maskedInputCollection(requests)
        else:
            self.unmasking(requests)

    # broadcast common value
    def setUp(self, requests):
        usersNow = len(requests)
        
        commonValues = getCommonValues()
        self.R = commonValues["R"]
        commonValues["n"] = usersNow
        commonValues["t"] = self.t

        if self.model == {}:
            self.model = fl.setup()
        model_weights_list = mhelper.weights_to_dic_of_list(self.model.state_dict())
        user_groups = fl.get_user_dataset(self.n)

        for idx, (clientSocket, requestData) in enumerate(requests):
            response_i = copy.deepcopy(commonValues)
            response_i["index"] = idx
            response_i["data"] = [int(k) for k in user_groups[idx]]
            response_i["weights"] = model_weights_list
            response_json = json.dumps(response_i)

            # response
            clientSocket.sendall(bytes(response_json + "\r\n", self.ENCODING))

    def advertiseKeys(self, requests):
        # requests example: {"c_pk":"VALUE", "s_pk": "VALUE"}
        
        # response example: {0: {"index":0, "c_pk":"VALUE", "s_pk": "VALUE"}, 1: {"index":0, "c_pk":"VALUE", "s_pk": "VALUE"} }
        response = {}
        for _, requestData in requests: # (socket, data)
            index = requestData['index']
            self.users_keys[index] = requestData  # store on server
            response[index] = requestData
        self.broadcast(requests, response)

    def shareKeys(self, requests):
        # (one) request example: {0: [(0, 0, e00), (0, 1, e01) ... ]}
        # requests example: [{0: [(0, 0, e00), ... ]}, {1: [(1, 0, e10), ... ]}, ... ]
        # response example: { 0: [e00, e10, e20, ...], 1: [e01, e11, e21, ... ] ... }

        euvs = {}
        for _, requestData in requests: # (socket, data)
            for u, v, euv in requestData['euv']:
                if euvs.get(v) is None:
                    euvs[v] = {}
                euvs[v][u] = euv

        # send response
        for clientSocket, requestData in requests:
            index = requestData['index']
            response_json = json.dumps(euvs[index])
            clientSocket.sendall(bytes(response_json + "\r\n", self.ENCODING))
        
    def maskedInputCollection(self, requests):
        # if u3 dropped
        # (one) request example: {"idx":0, "yu":y0}

        # response example: { "users": [0, 1, 2 ... ] }
        response = []
        for _, requestData in requests: # (socket, data)
            response.append(int(requestData["index"]))
            yu_ = mhelper.dic_of_list_to_weights(requestData["yu"])
            self.yu_list.append(yu_)

        self.broadcast(requests, {"users": response})

    def unmasking(self, requests):
        # (one) request: {"index": u, "ssk_shares": s_sk_shares_dic, "bu_shares": bu_shares_dic}
        # if u2, u3 dropped, requests: [{"index": 0, "ssk_shares": {2: s20_sk, 3: s30_sk}, "bu_shares": {1: b10, 4: b40}}, ...]

        s_sk_shares_dic = {}     # {2: [s20_sk, s21_sk, ... ], 3: [s30_sk, s31_sk, ... ], ... }
        bu_shares_dic = {}       # {0: [b10, b04, ... ], 1: [b10, b14, ... ], ... }

        # get s_sk_shares_dic, bu_shares_dic of user2\3, user3
        for _, requestData in requests: # (socket, data)
            ssk_shares = literal_eval(requestData["ssk_shares"])
            for i, share in ssk_shares.items():
                try: 
                    s_sk_shares_dic[i].append(share)
                except KeyError:
                    s_sk_shares_dic[i] = [share]
                    pass
            bu_shares = literal_eval(requestData["bu_shares"])
            for i, share in bu_shares.items():
                try: 
                    bu_shares_dic[i].append(share)
                except KeyError:
                    bu_shares_dic[i] = [share]
                    pass
        
        # reconstruct s_sk of users2\3
        s_sk_dic = {}
        for i, ssk_shares in s_sk_shares_dic.items(): # first, reconstruct ssk_u <- ssk_u,v
            s_sk_dic[i] = reconstruct(ssk_shares)
        # recompute p_vu
        user3list = list(bu_shares_dic.keys())
        sum_pvu = 0
        for u in user3list:
            for v, s_sk in s_sk_dic.items():
                pvu = reconstructPvu(v, u, s_sk, self.users_keys[u]["s_pk"], self.R)
                sum_pvu = sum_pvu + pvu
                #sum_xu = sum_xu + pvu
        
        sum_pu = 0
        # recompute p_u of users3
        for i, bu_shares in bu_shares_dic.items(): # first, reconstruct ssk_u <- ssk_u,v
            pu = reconstructPu(bu_shares, self.R)
            sum_pu = sum_pu + pu
            #sum_xu = sum_xu - pu
        
        # sum_yu
        mask = sum_pvu - sum_pu
        sum_xu = generatingOutput(self.yu_list, mask)
        
        # update global model
        final_userNum = len(self.yu_list)
        average_weight = utils.average_weight(sum_xu, final_userNum)
        self.model.load_state_dict(average_weight)
        
        # End
        self.broadcast(requests, "[Server] End protocol")
        fl.test_model(self.model)
    
    def close(self):
        self.serverSocket.close()

if __name__ == "__main__":
    server = BasicSAServerV2(n=3, k=5, t=1)
    server.start()

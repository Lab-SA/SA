import os, sys, json
from ast import literal_eval

sys.path.append(os.path.dirname(os.path.abspath(os.path.dirname(__file__))))

from BasicSAServerV2 import BasicSAServerV2
from BasicSA import getCommonValues
import HeteroSAg as hetero
from dto.HeteroSetupDto import HeteroSetupDto, HeteroKeysRequestDto
from CommonValue import BasicSARound
import learning.federated_main as fl
import learning.models_helper as mhelper
import SecureProtocol as sp

class HeteroSAServer(BasicSAServerV2):
    users_keys = {}
    n = 4 # expected (== G * perGroup == G * G)
    t = 1
    R = 0
    B = [] # The SS Matrix B
    G = 2 # group num
    perGroup = 2
    usersNow = 0
    segment_yu = {}
    surviving_users = []

    def __init__(self, n, k):
        super().__init__(n, k)

    # broadcast common value
    def setUp(self, requests):
        self.usersNow = len(requests)
        self.t = int(self.usersNow / 2) # threshold

        commonValues = getCommonValues()
        self.R = commonValues["R"]
        self.g = commonValues["g"]
        self.p = commonValues["p"]

        # Segment Grouping Strategy: G x G Segment selection matrix B
        self.B = hetero.SS_Matrix(self.G)
        
        # model
        if self.model == {}:
            self.model = fl.setup()
        model_weights_list = mhelper.weights_to_dic_of_list(self.model.state_dict())
        user_groups = fl.get_user_dataset(self.usersNow)

        for i in range(self.G):
            for j in range(self.perGroup):
                idx = i*self.perGroup + j
                response_ij = HeteroSetupDto(
                    n = self.usersNow, 
                    t = self.t,
                    g = self.g, 
                    p = self.p, 
                    R = self.R, 
                    group = i, 
                    index = idx, 
                    B = self.B, 
                    G = self.G,
                    data = [int(k) for k in user_groups[idx]],
                    weights= str(model_weights_list)
                )._asdict()
                response_json = json.dumps(response_ij)
                clientSocket = requests[idx][0]
                clientSocket.sendall(bytes(response_json + "\r\n", self.ENCODING))

    def advertiseKeys(self, requests):
        # requests example: {"group":, "index":, "c_pk":"VALUE", "s_pk": "VALUE"}

        # make response
        # response example: {"INDEX": ("c_pk":"VALUE", "s_pk": "VALUE")}
        for request in requests:
            requestData = request[1]  # (socket, data)
            index = requestData["index"]
            self.users_keys[index] = {"c_pk": requestData["c_pk"], "s_pk": requestData["s_pk"]}
        self.broadcast(requests, self.users_keys)


    def shareKeys(self, requests):
        # (one) request example: {0: [(0, 0, e00), (0, 1, e01) ... ]}
        # requests example: [{0: [(0, 0, e00), ... ]}, {1: [(1, 0, e10), ... ]}, ... ]

        # response example: { 0: [e00, e10, e20, ...], 1: [e01, e11, e21, ... ] ... }
        response = {}
        requests_euv = []
        for request in requests:
            requestData = request[1]  # (socket, data)
            for idx, data in requestData.items(): #only one
                response[idx] = {}  # make dic
                requests_euv.append(data)
        for request in requests_euv:
            for (u, v, euv) in request:
                try:
                    response[str(v)][u] = euv
                except KeyError:  # drop-out
                    print("KeyError: drop-out!")
                    pass

        self.foreach(requests, response)
    

    def maskedInputCollection(self, requests):
        # if u3 dropped
        # (one) request example: {"group":0, "index":0, "segment_yu":{0: y0, 1: y1}}

        # response example: { "users": [0, 1, 2 ... ] }
        self.segment_yu = {i: {j: [] for j in range(self.G)} for i in range(self.G)} # i: segment level, j: quantization level
        for request in requests:
            requestData = request[1]  # (socket, data)
            index = int(requestData["index"])
            self.surviving_users.append(index)
            for i, segment in requestData["segment_yu"].items():
                for q, yu in segment.items():
                    yu_ = mhelper.dic_of_list_to_weights(yu)
                    self.segment_yu[int(i)][int(q)].append(yu_)

        self.broadcast(requests, {"users": self.surviving_users})
        print(f'surviving_users: {self.surviving_users}')
        #print(f'segment_yu: {self.segment_yu}')

    def unmasking(self, requests):
        # (one) request: {"index": u, "ssk_shares": s_sk_shares_dic, "bu_shares": bu_shares_dic}
        # if u2, u3 dropped, requests: [{"idx": 0, "ssk_shares": {2: s20_sk, 3: s30_sk}, "bu_shares": {1: b10, 4: b40}}, ...]

        s_sk_shares_dic = {}     # {2: [s20_sk, s21_sk, ... ], 3: [s30_sk, s31_sk, ... ], ... }
        bu_shares_dic = {}       # {0: [b10, b04, ... ], 1: [b10, b14, ... ], ... }

        # get s_sk_shares_dic, bu_shares_dic of user2\3, user3
        for request in requests:
            requestData = request[1]  # (socket, data)

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
        
        # reconstruct s_sk of drop-out users
        s_sk_dic = hetero.reconstructSSKofSegments(self.B, self.G, self.perGroup, s_sk_shares_dic)
        
        # unmasking
        segment_xu = hetero.unmasking(
            hetero.getSegmentInfoFromB(self.B, self.G, self.perGroup), 
            self.G, 
            self.segment_yu, 
            self.surviving_users, 
            self.users_keys, 
            s_sk_dic,
            bu_shares_dic, 
            self.R
        )
        #print(f'segment_xu: {segment_xu}')

        # TODO dequantization encoded xu

        # update global model

        # End
        self.broadcast(requests, "[Server] End protocol")

if __name__ == "__main__":
    server = HeteroSAServer(n=4, k=1)
    server.start()
    
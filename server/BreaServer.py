import os, sys, copy, json
sys.path.append(os.path.dirname(os.path.abspath(os.path.dirname(__file__))))

from BasicSAServerV2 import BasicSAServerV2
from MainServer import MainServer
from BasicSA import getCommonValues
from dto.BreaSetupDto import BreaSetupDto
import learning.federated_main as fl
import learning.models_helper as mhelper
import Brea as br

class BreaServer(BasicSAServerV2):
    users_keys = {}
    n = 4
    t = 1
    R = 0
    usersNow = 0
    surviving_users = []

    def __init__(self, n, k):
        super().__init__(n, k)
        

    def setUp(self, requests):
        # init
        self.surviving_users = []

        self.usersNow = len(requests)
        self.t = int(self.usersNow / 2) # threshold

        commonValues = getCommonValues()
        self.R = commonValues["R"]
        self.g = commonValues["g"]
        self.p = commonValues["p"]

        # model
        if self.model == {}:
            self.model = fl.setup()
        model_weights_list = mhelper.weights_to_dic_of_list(self.model.state_dict())
        user_groups = fl.get_user_dataset(self.usersNow)

        for i in range(self.n):
            response_ij = BreaSetupDto(
                n = self.usersNow, 
                t = self.t,
                g = self.g, 
                p = self.p, 
                R = self.R, 
                index = i, 
                data = [int(k) for k in user_groups[i]],
                weights= str(model_weights_list)
            )._asdict()
            response_json = json.dumps(response_ij)
            clientSocket = requests[i][0]
            clientSocket.sendall(bytes(response_json + "\r\n", self.ENCODING))


    # def secretSharing():
    #     global usersNum

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


    def advertiseKeys(self, requests):
        # (one) request example: {0: [(0, 0, c00), (0, 1, c01) ... ]}
        # requests example: [{0: [(0, 0, c00), ... ]}, {1: [(1, 0, c10), ... ]}, ... ]

        # response example: { 0: [c00, c10, c20, ...], 1: [c01, c11, c21, ... ] ... }
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

        self.broadcast(requests, response)


    def selectUsers(self, requests):
        # (one) request example: {0: [(1, 2, d12), (1, 3, d13) ... ]}
        # requests example: [{0: [(1, 2, d12), ... ]}, {1: [(0, 2, d02), ... ]}, ... ]
        
        # if u0, u2, ... selected,
        # response example: [0, 2, ... ]    # selected user index
        for request in requests:
            requestData = request[1]  # (socket, data)



    def unmasking(self, requests):
        # requests example: {0: s0, 1: s1, 2: s2, ... }

        w_i = {}

        # reconstruct w_i of selected users
        
        new_weights = mhelper.restore_weights_tensor(mhelper.default_weights_info, w_i)

        # update global model
        fl.update_model(self.model, new_weights)

        # End
        self.broadcast(requests, "[Server] End protocol")
        fl.test_model(self.model)

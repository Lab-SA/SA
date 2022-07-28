import os, sys, copy, json
sys.path.append(os.path.dirname(os.path.abspath(os.path.dirname(__file__))))

from BasicSAServerV2 import BasicSAServerV2
from MainServer import MainServer
from BasicSA import getCommonValues
from dto.BreaSetupDto import BreaSetupDto
import learning.federated_main as fl
import learning.models_helper as mhelper
import Brea


class BreaServer(BasicSAServerV2):
    users_keys = {}
    n = 4
    t = 1
    R = 0
    usersNow = 0  # number of users survived
    surviving_users = []

    def __init__(self, n, k):
        super().__init__(n, k)

    def setUp(self, requests):
        # init
        self.surviving_users = []

        self.usersNow = len(requests)
        self.t = int(self.usersNow / 2)  # threshold

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
        # (one) request example: {"index": index, "shares": sij }
        # requests example: [{0: [([13]), ... ]}, {1: [(0), ... ]}, ... ]
        # sij : secret share from i for j

        # response example: { 0: [([13]), ... ] 1: [([10]), ... }
        # sji : secret share from j for i

        response = {}
        for request in requests:
            requestData = request[1]  # (socket, data)
            for idx, data in requestData.items():
                for j in range(len(data)):
                    response[j][idx] = data[j]

        self.foreach(requests, response)


    def shareCommitmentsVerifyShares(self, requests):
        # (one) request example: {"index": index, "commitment": cij }
        # requests example: [{0: [([1]), ... ]}, {1: [(2187), ... ]}, ... ]
        # cij : commitment from i

        # response example: { 0: [([13]), ... ] 1: [([10]), ... }
        response = {}
        for request in requests:
            requestData = request[1]
            for idx, data in requestData.items():
                for j in range(len(data)):
                    response[idx][j] = data[j] # cij

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

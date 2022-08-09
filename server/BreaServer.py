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
    m = 4   # number of selecting user
    usersNow = 0  # number of users survived
    surviving_users = []
    theta_list = {}

    def __init__(self, n, k):
        super().__init__(n, k)

    def setUp(self, requests):
        # init
        self.surviving_users = []

        self.usersNow = len(requests)
        self.t = int(self.usersNow / 2)  # threshold
        self.theta_list = Brea.make_theta(self.usersNow)

        commonValues = getCommonValues()
        self.R = commonValues["R"]
        self.g = commonValues["g"]
        self.p = commonValues["p"]

        # model
        if self.model == {}:
            self.model = fl.setup()
        self.model_weights_list = mhelper.weights_to_dic_of_list(self.model.state_dict())
        user_groups = fl.get_user_dataset(self.usersNow)

        for i in range(self.n):
            response_ij = BreaSetupDto(
                n = self.usersNow, 
                t = self.t,
                g = self.g, 
                p = self.p, 
                R = self.R,
                theta = self.theta_list[i],
                index = i, 
                data = [int(k) for k in user_groups[i]],
                weights= str(self.model_weights_list)
            )._asdict()
            response_json = json.dumps(response_ij)
            clientSocket = requests[i][0]
            clientSocket.sendall(bytes(response_json + "\r\n", self.ENCODING))

    # def secretSharing():
    #     global usersNum

    def shareKeys(self, requests):
        # (one) request example: {"index": index, "shares": sij, "theta": theta }
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
                response[idx] = {}
                for j in range(len(data)):
                    response[idx][j] = data[j]  # cij

        self.broadcast(requests, response)


    def computeDistanceSelectUser(self, requests):

        # d(i)jk 받아서 jk를 기준으로 d(i)를 배열로 만든다. (쳌)
        # 그러고 그를 바탕으로 _djk를 만든다
        # real domain의 djk를 만든다
        # multi krum을 실시한다
        # 선택된 유저를 클라이언트에 보낸다

        # (one) request example: {0: [(0, 1, 2, d(0)12), (0, 1, 3, d(0)13) ... ]} // d(i)jk
        # requests example: [{0: [(0, 1, 2, d(0)12), ... ]}, {1: [(1, 0, 2, d(1)02), ... ]}, ... ]

        # if u0, u2, ... selected,
        # response example: [0, 2, ... ]    # selected user index
        response = {}
        djk = {}
        requests_djk = []
        for request in requests:
            requestData = request[1]  # (socket, data)
            for idx, data in requestData.items():
                requests_djk.append(data)
        for request in requests_djk:
            for (i, j, k, d) in request:
                try:
                    djk[(j,k)][i] = d
                except KeyError:
                    print("KeyError")
                    pass

        real_djk = {}
        for idx, data in djk.items():
            _djk = Brea.calculate_djk_from_h_polynomial(self.theta_list, data)
            real_djk = Brea.real_domain_djk(_djk)

        response = Brea.multi_krum(self.n, self.m, real_djk)


    def unmasking(self, requests):
        # requests example: {0: s0, 1: s1, 2: s2, ... }
        si = []
        for request in requests:
            requestData = request[1]
            for idx, data in requestData.items():
                si.append(data)

        # reconstruct _wj of selected users
        # by recovering h with theta and si
        _wj = Brea.calculate_djk_from_h_polynomial(self.theta_list, si)

        _wjt = Brea.update_weight(_wj, self.model_weights_list)
        new_weights = mhelper.restore_weights_tensor(mhelper.default_weights_info, _wjt)

        # update global model
        fl.update_model(self.model, new_weights)

        # End
        self.broadcast(requests, "[Server] End protocol")
        fl.test_model(self.model)


if __name__ == "__main__":
    server = BreaServer(n=4, k=1)
    for i in range(5):  # round
        server.start()

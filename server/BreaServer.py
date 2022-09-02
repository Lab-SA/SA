import os, sys, copy, json

from CommonValue import BreaRound

sys.path.append(os.path.dirname(os.path.abspath(os.path.dirname(__file__))))

from BasicSAServerV2 import BasicSAServerV2
from BasicSA import getCommonValues
import learning.federated_main as fl
import learning.models_helper as mhelper
import Brea

class BreaServer(BasicSAServerV2):
    users_keys = {}
    n = 4
    t = 1
    R = 0
    m = 3   # number of selecting user
    quantization_level = 30
    usersNow = 0  # number of users survived
    surviving_users = []
    theta_list = {}

    def __init__(self, n, k):
        super().__init__(n, k, isBrea=True)

    def saRound(self, tag, requests):
        if tag == BreaRound.SetUp.name:
            self.setUp(requests)
        elif tag == BreaRound.ShareKeys.name:
            self.ShareKeys(requests)
        elif tag == BreaRound.ShareCommitmentsVerifyShares.name:
            self.ShareCommitmentsVerifyShares(requests)
        elif tag == BreaRound.ComputeDistance.name:
            self.ComputeDistance(requests)
        elif tag == BreaRound.Unmasking.name:
            self.Unmasking(requests)

    def setUp(self, requests):
        # init
        self.surviving_users = []

        self.usersNow = len(requests)
        self.t = int(self.usersNow / 2)  # threshold

        commonValues = getCommonValues()
        self.R = commonValues["R"]
        self.g = commonValues["g"]
        self.p = commonValues["p"]
        self.theta_list = Brea.make_theta(self.usersNow, self.p)

        # model
        if self.model == {}:
            self.model = fl.setup()
        self.model_weights_list = mhelper.weights_to_dic_of_list(self.model.state_dict())
        user_groups = fl.get_user_dataset(self.usersNow)

        for i in range(self.n):
            response_ij = copy.deepcopy(commonValues)
            response_ij["n"] = self.usersNow
            response_ij["t"] = self.t
            response_ij["q"] = self.quantization_level
            response_ij["theta"] = self.theta_list
            response_ij["index"] = i
            response_ij["data"] = [int(k) for k in user_groups[i]]
            response_ij["weights"] = self.model_weights_list

            response_json = json.dumps(response_ij)
            clientSocket = requests[i][0]
            clientSocket.sendall(bytes(response_json + "\r\n", self.ENCODING))

    def ShareKeys(self, requests):
        # (one) request example: {"index": index, "shares": sij}
        # requests example: [{0: [([13]), ... ]}, {1: [(0), ... ]}, ... ]
        # sij : secret share from i for j

        # response example: { 0: [([13]), ... ] 1: [([10]), ... }
        # sji : secret share from j for i

        response = {}
        response_shares = []
        for request in requests:
            requestData = request[1]  # (socket, data)
            shares = requestData["shares"]
            response_shares.append(requestData)
            for idx in range(len(shares)):
                response[idx] = {}

        for request in response_shares:
            i = int(request["index"])
            shares = request["shares"]
            for idx in range(len(shares)):
                response[idx][i] = shares[idx]

        self.foreach_share(requests, response)


    def ShareCommitmentsVerifyShares(self, requests):
        # (one) request example: {"index": index, "commitment": cij }
        # requests example: [{0: [([1]), ... ]}, {1: [(2187), ... ]}, ... ]
        # cij : commitment from i

        # response example: { 0: [([13]), ... ] 1: [([10]), ... }
        response = {}
        response_commit = []
        for request in requests:
            requestData = request[1]
            commit = requestData["commitment"]
            response_commit.append(requestData)
            for idx in range(len(commit)):
                response[idx] = {}

        for request in response_commit:
            i = int(request["index"])
            commit = request["commitment"]
            for idx in range(len(commit)):
                response[idx][i] = commit[idx]

        self.broadcast(requests, response)


    def ComputeDistance(self, requests):
        # (one) request example: {"index": index, "distance": djk(i) }

        djk = {}
        requests_djk = []
        real_djk = {}
        for request in requests:
            requestData = request[1]  # (socket, data)
            requests_djk.append(requestData)
            distance = requestData["distance"]
            for (j, k, d) in distance:
                djk[(j, k)] = {}

        for request in requests_djk:
            index = request["index"]
            distance = request["distance"]
            for(j, k, d) in distance:
                try:
                    real_djk[j] = {}
                    djk[(j, k)][index] = d
                except KeyError:
                    print("KeyError")
                    pass


        for (j, k), data in djk.items():
            tmp_djk = []
            tmp_theta = []
            for index, dis in data.items():
                tmp_theta.append(self.theta_list[index])
                tmp_djk.append(dis)

            d = tmp_djk[0]
            h = []

            for x in range(len(d)):
                d_one = []
                for u in range(self.usersNow):
                    d_one.append(tmp_djk[u][x])
                # reconstruct with theta and djk(i)
                _h = Brea.calculate_djk_from_h_polynomial(tmp_theta, d_one)
                # djk to real domain
                h.append(Brea.real_domain_djk(_h, self.p, self.q))
            real_djk[j][k] = h

        response = Brea.multi_krum(self.n, self.m, real_djk)

        self.broadcast(requests, response)


    def Unmasking(self, requests):
        # requests example: {0: s0, 1: s1, 2: s2, ... }

        _si = {}
        for request in requests:
            requestData = request[1]  # (socket, data)
            index = requestData["index"]
            si = requestData["si"]
            _si[index] = si

        si_list = []
        for key, value in sorted(_si.items()):
            si_list.append(value)

        # reconstruct _wj of selected users
        # by recovering h with theta and si
        _wj = Brea.calculate_djk_from_h_polynomial(self.theta_list, si_list)

        _wjt = Brea.update_weight(_wj, self.model_weights_list, self.p, self.q, self.usersNow)
        new_weights = mhelper.restore_weights_tensor(mhelper.default_weights_info, _wjt)

        # update global model
        fl.update_model(self.model, new_weights)

        # End
        self.broadcast(requests, "[Server] End protocol")
        fl.test_model(self.model)


if __name__ == "__main__":
    server = BreaServer(n=3, k=5)
    server.start()

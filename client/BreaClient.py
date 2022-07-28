import json
import os
import sys
import numpy as np

import Brea
from dto.BreaSetupDto import BreaSetupDto
from BasicSAClient import sendRequestAndReceive
from CommonValue import BreaRound
import learning.federated_main as fl
import learning.models_helper as mhelper

SIZE = 2048
ENCODING = 'utf-8'


class BreaClient:
    HOST = 'localhost'
    PORT = 7000
    xu = 0

    index = 0  # user index
    n = t = g = p = R = 0  # common values
    model = {}
    weight = {}
    quantized_weight = {}
    rij = {}
    shares = {}
    theta = {}
    others_shares = {}
    commitment = {}
    distance = {}
    selected_user = {}

    def setUp(self):
        tag = BreaRound.SetUp.name

        # response: {"n": n, "t": t, "g": g, "p": p, "R": R, "data", "weights"}
        response = sendRequestAndReceive(self.HOST, self.PORT, tag, {})
        setupDto = json.loads(json.dumps(response), object_hook=lambda d: BreaSetupDto(**d))  #

        self.n = setupDto.n  # user num
        self.t = setupDto.t  # threshold
        self.g = setupDto.g
        self.p = setupDto.p
        self.R = setupDto.R
        self.index = setupDto.index  # user index
        self.data = setupDto.data
        global_weights = mhelper.dic_of_list_to_weights(response["weights"])

        if self.model == {}:
            self.model = fl.setup()
        fl.update_model(self.model, global_weights)
        local_model, local_weight, local_loss = fl.local_update(self.model, self.data, 0)  # epoch 0 (temp)
        self.weight = local_weight
        local_weights_list = mhelper.weights_to_dic_of_list(local_weight)
        weights_info, flatten_weights = mhelper.flatten_list(local_weights_list)
        self.flatten_weights = flatten_weights

    def shareKeys(self):
        tag = BreaRound.ShareKeys.name

        # generate theta and rij list
        theta_list = Brea.make_theta(self.n)
        rij_list = Brea.generate_rij(self.t)
        self.theta = theta_list
        self.rij = rij_list

        # generate shares and commitments
        shares = Brea.make_shares(self.flatten_weights, theta_list, self.t, rij_list, self.index)
        self.shares = shares
        request = {"index": self.index, "shares": self.shares}

        # receive shares_list from server in json format
        response = sendRequestAndReceive(self.HOST, self.PORT, tag, request)

        # store others shares_list from server to client in dic
        # other shares list : sji
        for j, shares in response.items():
            self.others_shares[int(j)] = shares
        print(self.others_shares)


    def shareCommitmentsVerifyShares(self):
        tag = BreaRound.ShareCommitmentsVerifyShares.name

        commitments = Brea.generate_commitments(self.rij)
        self.commitment = commitments
        request = {"index": self.index, "commitment": self.commitment}

        # receive commitments_list from server in json format
        response = sendRequestAndReceive(self.HOST, self.PORT, tag, request)

        result = Brea.verify(self.shares[0], commitments, self.theta[0])
        print("verify result : ", result)


    def computeDistance(self):
        tag = BreaRound.ComputeDistance.name

        # d(i)jk
        distance = Brea.calculate_distance(self.others_shares, self.n, self.u)
        self.distance = distance
        request = {"distance": distance}

        #receive selected user list from server
        response = sendRequestAndReceive(self.HOST, self.PORT, tag, request)
        print("response : ", response)

        # store select user from server to client
        self.selected_user = response[0]


    def unMasking(self):
        tag = BreaRound.Unmasking.name
        si = Brea.aggregate_share(self.others_shares, self.selected_user, self.u)
        request = {"si ", si}

        response = sendRequestAndReceive(self.HOST, self.PORT, tag, request)



    
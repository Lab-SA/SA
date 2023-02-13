import json
import os
import sys
import numpy as np

import Brea
from dto.BreaSetupDto import BreaSetupDto
from BasicSAClient import sendRequestAndReceive
from CommonValue import BreaRound, BasicSARound
import learning.federated_main as fl
import learning.models_helper as mhelper
from BasicSA import stochasticQuantization

SIZE = 2048
ENCODING = 'utf-8'


class BreaClient:
    HOST = 'localhost'
    PORT = 7002
    xu = 0

    index = 0  # user index
    commonValues = {} # g = p = R = 0
    n = t = g = p = 0
    quantization_level = 0
    model = {}
    weight = {}
    quantized_weight = {}
    rij = {}
    shares = {}
    theta = {}
    others_shares = {}
    commitment = {}
    distance = []
    selected_user = {}

    def setUp(self):
        tag = BreaRound.SetUp.name

        # response: {"n": n, "t": t, "g": g, "p": p, "R": R, "data", "weights"}
        response = sendRequestAndReceive(self.HOST, self.PORT, tag, {})

        self.commonValues = response
        self.n = response["n"]
        self.t = response["t"]
        self.g = response["g"]
        self.p = response["p"]
        self.quantization_level = response["q"]
        self.theta = response["theta"]
        self.index = response["index"]
        self.data = response["data"]
        global_weights = mhelper.dic_of_list_to_weights(response["weights"])

        if self.model == {}:
            self.model = fl.setup()
        self.model.load_state_dict(global_weights)
        local_model, local_weight, local_loss = fl.local_update(self.model, self.data, 0)  # epoch 0 (temp)
        self.weight = local_weight

        local_weights_list = mhelper.weights_to_dic_of_list(local_weight)
        weights_info, flatten_weights = mhelper.flatten_list(local_weights_list)
        self.flatten_weights = stochasticQuantization(flatten_weights, self.quantization_level, self.p)


    def ShareKeys(self):
        tag = BreaRound.ShareKeys.name

        # generate theta and rij list
        self.rij_list = Brea.generate_rij(self.t, self.p)

        # generate shares and commitments
        self.shares = Brea.make_shares(self.flatten_weights, self.theta, self.t, self.rij_list, self.p)
        self.commitments = Brea.generate_commitments(self.flatten_weights, self.rij, self.g, self.p)

        request = {"index": self.index, "shares": self.shares, "commitments": self.commitments}
        # receive shares_list from server in json format
        response = sendRequestAndReceive(self.HOST, self.PORT, tag, request)

        # store others shares_dict and commitments_dict from server to client in dic
        # other shares list : sji
        shares_dict = response["shares"]
        self.others_shares = {int(idx): data for idx, data in shares_dict.items()}

        commits_dict = response["commitments"]
        commitment_all = {idx: data for idx, data in commits_dict.items()}

        result = Brea.verify(self.g, self.others_shares, commitment_all, self.theta[self.index], self.p)
        print("verify result : ", result)


    def ComputeDistance(self):
        tag = BreaRound.ComputeDistance.name

        # calculate 수정!
        distance = Brea.calculate_distance(self.others_shares)
        self.distance = distance  # (j, k, d(i)jk)
        request = {"index": self.index, "distance": self.distance}

        #receive selected user list from server
        response = sendRequestAndReceive(self.HOST, self.PORT, tag, request)

        # store select user from server to client
        self.selected_user = response
        print("selected_user : ", self.selected_user)


    def unMasking(self):
        tag = BreaRound.Unmasking.name
        si = Brea.aggregate_share(self.others_shares, self.selected_user, self.index)
        request = {"index": self.index, "si": si}

        response = sendRequestAndReceive(self.HOST, self.PORT, tag, request)


if __name__ == "__main__":
    client = BreaClient()
    for i in range(5):  # round
        client.setUp()
        client.ShareKeys()
        client.ComputeDistance()
        client.unMasking()
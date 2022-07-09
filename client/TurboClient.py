import os, sys

sys.path.append(os.path.dirname(os.path.abspath(os.path.dirname(__file__))))

import Turbo
from CommonValue import TurboRound
from BasicSAClient import sendRequestAndReceive
import learning.federated_main as fl
import learning.models_helper as mhelper

class TurboClient:
    HOST = 'localhost'
    PORT = 7000
    xu = 0  # temp. local model of this client

    u = 0  # u = user index
    n = t = g = p = R = 0  # common values
    group = 0
    index = 0
    weight = {}
    model = {}

    pre_maskedxij = pre_encodedxij = pre_si = pre_codedsi = 0  # for l-1 group
    maskedxij = encodedxij = si = codedsi = 0
    perGroup = mask_u = 0

    # alpha_list, beta_list = Turbo.generateRandomVectorSet(next_users, self.p)
    alpha = []
    beta = []
    drop_out = []

    # need?
    my_keys = {}  # c_pk, c_sk, s_pk, s_sk of this client
    others_keys = {}  # other users' public key dic
    weights_info = {}

    def setUp(self):
        tag = TurboRound.SetUp.name

        # response: {"n": n, "t": t, "g": g, "p": p, "R": R, "index": index, "group": group, "perGroup": 0, "mask_u": 0, "alpha": [], "beta": []}
        response = sendRequestAndReceive(self.HOST, self.PORT, tag, {})
        self.n = response["n"]
        self.t = response["t"]
        self.g = response["g"]
        self.p = response["p"]
        self.R = response["R"]
        self.group = response["group"]
        self.index = response["index"]
        self.perGroup = response["perGroup"]
        self.mask_u = response["mask_u"]
        self.alpha = response["alpha"]
        self.beta = response["beta"]

        self.data = response["data"]  # user_groups[idx]
        global_weights = mhelper.dic_of_list_to_weights(response["weights"])
        print(f'group: {self.group}, index: {self.index}')

        if self.model == {}:
            self.model = fl.setup()
        fl.update_model(self.model, global_weights)
        local_model, local_weight, local_loss = fl.local_update(self.model, self.data, 0)
        self.weight = local_weight

        return self.group

    def turbo(self):
        tag = TurboRound.Turbo.name

        request = {"group": self.group, "index": self.index}
        # response = {"maskedxij": {}, "encodedxij": {}, "si": {}, "codedsi": {}}
        response = sendRequestAndReceive(self.HOST, self.PORT, tag, request)

        self.pre_maskedxij = response["maskedxij"]
        self.pre_encodedxij = response["encodedxij"]
        self.pre_si = {int(k): v for k, v in response["si"].items()}
        self.pre_codedsi = response["codedsi"]

    def turbo_value(self):
        tag = TurboRound.TurboValue.name

        # this client
        # maskedxij = tildeX / encodedxij = barX / si = tildeS / codedsi = barS

        self.weights_info, flatten_weights = mhelper.flatten_tensor(self.weight)

        self.maskedxij = Turbo.computeMaskedModel(flatten_weights, self.mask_u, self.perGroup, self.p)
        self.encodedxij = Turbo.generateEncodedModel(self.alpha, self.beta, self.maskedxij)
        self.si = 0
        self.codedsi = 0

        if self.group > 0:
            self.pre_si, self.drop_out = Turbo.reconstruct(self.alpha, self.beta, self.pre_si, self.pre_codedsi)
            self.si = Turbo.partialSumofModel(self.pre_maskedxij, self.pre_si)
            self.codedsi = Turbo.partialSumofModel(self.pre_encodedxij, self.pre_si)

        request = {"group": self.group, "index": self.index, "maskedxij": self.maskedxij,
                   "encodedxij": self.encodedxij,
                   "si": self.si, "codedsi": self.codedsi, "drop_out": self.drop_out}

        sendRequestAndReceive(self.HOST, self.PORT, tag, request)


    def turbo_final(self):
        tag = TurboRound.TurboFinal.name

        response = sendRequestAndReceive(self.HOST, self.PORT, tag, {})
        print(f"response[chosen]= {response['chosen']}")

        if response["chosen"] == True:
            self.index = response["index"]
            self.pre_maskedxij = response["maskedxij"]
            self.pre_encodedxij = response["encodedxij"]
            self.pre_si = {int(k): v for k, v in response["si"].items()}
            self.pre_codedsi = response["codedsi"]
            self.final()

    def final(self):
        tag = TurboRound.Final.name
        
        self.pre_si, self.drop_out = Turbo.reconstruct(self.alpha, self.beta, self.pre_si, self.pre_codedsi)
        final_tildeS = Turbo.partialSumofModel(self.pre_maskedxij, self.pre_si)
        final_barS = Turbo.partialSumofModel(self.pre_encodedxij, self.pre_si)

        request = {"index": self.index, "final_tildeS": final_tildeS, "final_barS": final_barS,
                   "drop_out": self.drop_out}
        sendRequestAndReceive(self.HOST, self.PORT, tag, request)


if __name__ == "__main__":
    client = TurboClient()
    for i in range(3):
        group = client.setUp()
        if group != 0:
            client.turbo()
        client.turbo_value()
        client.turbo_final()

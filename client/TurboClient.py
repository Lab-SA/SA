import os, sys

sys.path.append(os.path.dirname(os.path.abspath(os.path.dirname(__file__))))

import Turbo
from CommonValue import TurboRound
from BasicSAClient import sendRequestAndReceive
import learning.federated_main as fl
import learning.models_helper as mhelper



class TurboClient:
    HOST = 'localhost'
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
        PORT = TurboRound.SetUp.value

        # response: {"n": n, "t": t, "g": g, "p": p, "R": R, "index": index, "group": group, "perGroup": 0, "mask_u": 0, "alpha": [], "beta": []}
        response = sendRequestAndReceive(self.HOST, PORT, tag, {})
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

        if self.model == {}:
            self.model = fl.setup()
        fl.update_model(self.model, global_weights)
        local_model, local_weight, local_loss = fl.local_update(self.model, self.data, 0)
        self.weight = local_weight
        # print(f"local model = {self.weight}")

        return self.group

    def turbo(self):
        tag = TurboRound.Turbo.name
        PORT = TurboRound.Turbo.value

        request = {"group": self.group, "index": self.index}
        # response = {"maskedxij": {}, "encodedxij": {}, "si": {}, "codedsi": {}}
        response = sendRequestAndReceive(self.HOST, PORT, tag, request)

        self.pre_maskedxij = response["maskedxij"]
        self.pre_encodedxij = response["encodedxij"]
        self.pre_si = {int(k): v for k, v in response["si"].items()}
        self.pre_codedsi = response["codedsi"]

    def turbo_value(self):
        tag = TurboRound.TurboValue.name
        PORT = TurboRound.Turbo.value

        # this client
        # maskedxij = tildeX / encodedxij = barX / si = tildeS / codedsi = barS

        self.weights_info, flatten_weights = mhelper.flatten_tensor(self.weight)
        # print(self.weights_info, flatten_weights)

        print(f"flatten_weights[0] = {flatten_weights[0]}")

        self.maskedxij = Turbo.computeMaskedModel(flatten_weights, self.mask_u, self.perGroup, self.p)
        # print(f"self.maskedxij={self.maskedxij}")
        self.encodedxij = Turbo.generateEncodedModel(self.alpha, self.beta, self.maskedxij)
        # print(f"self.encodedxij={self.encodedxij}")
        self.si = 0
        self.codedsi = 0

        if self.group > 0:
            print("reconstruct 시작")
            self.reconstruct(self.group)
            print("reconstruct 종료")
            self.si = Turbo.updateSumofMaskedModel(self.group, self.pre_maskedxij, self.pre_si)
            self.codedsi = Turbo.updateSumofEncodedModel(self.group, self.pre_encodedxij, self.pre_si)

        request = {"group": self.group, "index": self.index, "maskedxij": self.maskedxij,
                   "encodedxij": self.encodedxij,
                   "si": self.si, "codedsi": self.codedsi, "drop_out": self.drop_out}

        sendRequestAndReceive(self.HOST, PORT, tag, request)


    def turbo_final(self):
        tag = TurboRound.TurboFinal.name
        PORT = TurboRound.Turbo.value
        response = sendRequestAndReceive(self.HOST, PORT, tag, {})
        # print(response)
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
        PORT = TurboRound.Final.value
        self.reconstruct(2)  # any l > 1
        final_tildeS = Turbo.updateSumofMaskedModel(2, self.pre_maskedxij, self.pre_si)  # any l > 1
        final_barS = Turbo.updateSumofEncodedModel(2, self.pre_encodedxij, self.pre_si)  # any l > 1

        request = {"index": self.index, "final_tildeS": final_tildeS, "final_barS": final_barS,
                   "drop_out": self.drop_out}
        sendRequestAndReceive(self.HOST, PORT, tag, request)

    # reconstruct l-1 group's si and codedsi
    def reconstruct(self, group):
        self.pre_si, self.drop_out = Turbo.reconstruct(self.alpha, self.beta, self.pre_si, self.pre_codedsi)
        self.pre_codedsi = Turbo.updateSumofEncodedModel(group, self.pre_encodedxij, self.pre_si)


if __name__ == "__main__":
    client = TurboClient()  # test
    group = client.setUp()
    print("finished setup")
    if group != 0:
        print("start turbo")
        client.turbo()
        print("finished turbo")
    print("start turbo-value")
    client.turbo_value()
    print("finished turbo_value")
    print("start turbo-final")
    client.turbo_final()
    print("finished turbo_final")

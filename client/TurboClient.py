import json, socket, os, sys
import Turbo

sys.path.append(os.path.dirname(os.path.abspath(os.path.dirname(__file__))))

import BasicSA as sa
from CommonValue import TurboRound
from BasicSAClient import sendRequestAndReceive

SIZE = 2048
ENCODING = 'utf-8'

class TurboClient:
    HOST = 'localhost'
    xu = 0  # temp. local model of this client

    u = 0  # u = user index
    n = t = g = p = R = 0 # common values
    group = 0
    index = 0
    weights = {1: 123} # temp

    # need?
    my_keys = {}  # c_pk, c_sk, s_pk, s_sk of this client
    others_keys = {}  # other users' public key dic

    def setUp(self):
        tag = TurboRound.SetUp.name
        PORT = TurboRound.SetUp.value

        # response: {"n": n, "t": t, "g": g, "p": p, "R": R, "index": index, "group": group}
        response = sendRequestAndReceive(self.HOST, PORT, tag, {})
        self.n = response["n"]
        self.t = response["t"]
        self.g = response["g"]
        self.p = response["p"]
        self.R = response["R"]
        self.group = response["group"]
        self.index = response["index"]
        print(response)
        return self.group
    
    def turbo(self):
        tag = TurboRound.Turbo.name
        PORT = TurboRound.Turbo.value

        request = {"group": self.group, "index": self.index}
        # response = {"pre_maskedxij": {}, "pre_encodedxij": {}, "pre_si": {}, "pre_codedsi": {}, "perGroup": 0, "mask_u": 0}
        response = sendRequestAndReceive(self.HOST, PORT, tag, request)

        self.pre_maskedxij = response["maskedxij"]
        self.pre_encodedxij = response["encodedxij"]
        self.pre_si = response["si"]
        self.pre_codedsi = response["codedsi"]
        self.perGroup = response["perGroup"]
        self.mask_u = response["mask_u"]
        print(response)
        print(self.pre_maskedxij, self.pre_encodedxij, self.pre_si, self.pre_codedsi)
    
    def turbo_value(self):
        tag = TurboRound.TurboValue.name
        PORT = TurboRound.Turbo.value

        alpha_list = []
        beta_list = []
        next_users = [idx for idx in range(self.perGroup)]

        self.maskedxij = Turbo.computeMaskedModel(self.xu, self.mask_u, next_users, self.p)
        alpha_list, beta_list = Turbo.generateRandomVectorSet(next_users, self.p)
        self.encodedxij = Turbo.generateEncodedModel(alpha_list, beta_list, self.maskedxij)
        self.si = 0
        self.codedsi = 0

        if self.group > 0:
            self.si = Turbo.updateSumofMaskedModel(self.group, self.pre_maskedxij, self.pre_si)
            self.codedsi = Turbo.updateSumofEncodedModel(self.group, self.pre_codedsi, self.pre_maskedxij)

        request = {"group": self.group, "index": self.index, "maskedxij": self.maskedxij, "encodedxij": self.pre_encodedxij, "si": self.si, "codedsi": self.codedsi}
        sendRequestAndReceive(self.HOST, PORT, tag, request)

    def turbo_final(self):
        tag = TurboRound.TurboFinal.name
        PORT = TurboRound.Turbo.value
        response = sendRequestAndReceive(self.HOST, PORT, tag, {})
        if response["chosen"] == True:
            # TODO final stage
            self.pre_maskedxij = response["maskedxij"]
            self.pre_encodedxij = response["encodedxij"]
            self.pre_si = response["si"]
            self.pre_codedsi = response["codedsi"]
            self.perGroup = response["perGroup"]
            print(response)
            print(self.pre_maskedxij, self.pre_encodedxij, self.pre_si, self.pre_codedsi)
            self.final()

    def final(self):
        tag = TurboRound.Final.name
        PORT = TurboRound.Final.value
        # TODO final stage
        final_tildeS = Turbo.updateSumofMaskedModel(self.group + 1, self.pre_maskedxij, self.pre_si)
        final_barS = Turbo.updateSumofEncodedModel(self.group + 1, self.pre_encodedxij, self.pre_maskedxij)
        request = {"final_tildeS": final_tildeS, "final_barS": final_barS}
        sendRequestAndReceive(self.HOST, PORT, tag, request)

if __name__ == "__main__":
    client = TurboClient() # test
    group = client.setUp()
    if group != 0:
        client.turbo()
    client.turbo_value()
    client.turbo_final()

import json, socket, os, sys
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
        # response = {"maskedxij": {}, "encodedxij": {}, "si": {}, "codedsi": {}}
        response = sendRequestAndReceive(self.HOST, PORT, tag, request)

        self.maskedxij = response["maskedxij"]
        self.encodedxij = response["encodedxij"]
        self.si = response["si"]
        self.codedsi = response["codedsi"]
        print(response)
        print(self.maskedxij, self.encodedxij, self.si, self.codedsi)
    
    def turbo_value(self):
        tag = TurboRound.TurboValue.name
        PORT = TurboRound.Turbo.value
        request = {"group": self.group, "index": self.index, "maskedxij": {0: 1}, "encodedxij": {0: 2}, "si": 3, "codedsi": 4}
        sendRequestAndReceive(self.HOST, PORT, tag, request)

    def turbo_final(self):
        tag = TurboRound.TurboFinal.name
        PORT = TurboRound.Turbo.value
        response = sendRequestAndReceive(self.HOST, PORT, tag, {})
        if response["chosen"] == True:
            # TODO final stage
            self.final()

    def final(self):
        tag = TurboRound.Final.name
        PORT = TurboRound.Final.value
        # TODO final stage
        request = {"final_tildeS": 1, "final_barS": 2}
        sendRequestAndReceive(self.HOST, PORT, tag, request)

if __name__ == "__main__":
    client = TurboClient() # test
    group = client.setUp()
    if group != 0:
        client.turbo()
    client.turbo_value()
    client.turbo_final()

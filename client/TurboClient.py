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
        print(self.n, self.t, self.g, self.p, self.R, self.group, self.index)

if __name__ == "__main__":
    client = TurboClient() # test
    client.setUp()

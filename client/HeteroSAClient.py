import os, sys, json

sys.path.append(os.path.dirname(os.path.abspath(os.path.dirname(__file__))))

from CommonValue import BasicSARound
from BasicSAClient import sendRequestAndReceive
from dto.HeteroSetupDto import HeteroSetupDto
import BasicSA as sa

SIZE = 2048
ENCODING = 'utf-8'

class HeteroSAClient:
    HOST = 'localhost'
    xu = 0  # temp. local model of this client

    u = 0  # u = user index
    n = t = g = p = R = 0 # common values
    group = 0
    index = 0
    B = []

    perGroup  = 0
    
    my_keys = {}  # c_pk, c_sk, s_pk, s_sk of this client
    others_keys = {}  # other users' public key dic\
    euv_list = []  # euv of this client
    others_euv = {}

    def setUp(self):
        tag = BasicSARound.SetUp.name
        PORT = BasicSARound.SetUp.value

        # response: HeteroSetupDto
        response = sendRequestAndReceive(self.HOST, PORT, tag, {})
        setupDto = json.loads(json.dumps(response), object_hook=lambda d: HeteroSetupDto(**d)) #
        print(setupDto)
        
        self.n = setupDto.n
        self.t = setupDto.t
        self.g = setupDto.g
        self.p = setupDto.p
        self.R = setupDto.R
        self.group = self.perGroup = setupDto.group
        self.index = setupDto.index
        self.B = setupDto.B
    
    def advertiseKeys(self):
        tag = BasicSARound.AdvertiseKeys.name
        PORT = BasicSARound.AdvertiseKeys.value

        (c_pk, c_sk), (s_pk, s_sk) = sa.generateKeyPairs()
        self.my_keys["c_pk"] = c_pk
        self.my_keys["c_sk"] = c_sk 
        self.my_keys["s_pk"] = s_pk
        self.my_keys["s_sk"] = s_sk
        request = {"group": self.group, "index": self.index, "c_pk": c_pk, "s_pk": s_pk}

        # send {"group:, "index", "c_pk": c_pk, "s_pk": s_pk} to server in json format
        # receive other users' public keys from server in json format
        response = sendRequestAndReceive(self.HOST, PORT, tag, request)

        # store response on client
        # example: {"0": {"c_pk": "2123", "s_pk": "3333"}, "1": {"c_pk": "1111", "s_pk": "2222"}}
        self.others_keys = response


    def shareKeys(self):
        tag = BasicSARound.ShareKeys.name
        PORT = BasicSARound.ShareKeys.value

        # t = threshold, u = user index
        # request = [[u, v1, euv], [u, v2, euv], ...]
        euv_list, bu = sa.generateSharesOfMask(
            self.t,
            self.index,
            self.my_keys["s_sk"], 
            self.my_keys["c_sk"], 
            self.others_keys,
            self.R)
        self.euv_list = euv_list
        self.bu = bu
        request = {self.index: euv_list}

        # receive euv_list from server in json format
        response = sendRequestAndReceive(self.HOST, PORT, tag, request)

        # store euv from server to client in dic
        """for v, euv in enumerate(response):  # example response = ["e01", "e11"]
            others_euv[v] = euv
        """
        # if response format {v: euv}. example = {0: "e00", 1: "e10"}
        for v, euv in response.items():
            self.others_euv[int(v)] = euv
        print(self.others_euv)

if __name__ == "__main__":
    client = HeteroSAClient()
    client.setUp()
    client.advertiseKeys()
    client.shareKeys()

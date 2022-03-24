import os, sys, json

sys.path.append(os.path.dirname(os.path.abspath(os.path.dirname(__file__))))

from CommonValue import BasicSARound
from BasicSAClient import sendRequestAndReceive
from dto.HeteroSetupDto import HeteroSetupDto
import BasicSA as sa
from HeteroSAg import generateMaskedInputOfSegments
import learning.federated_main as fl

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
    G = perGroup = 0
    
    my_keys = {}  # c_pk, c_sk, s_pk, s_sk of this client
    others_keys = {}  # other users' public key dic\
    euv_list = []  # euv of this client
    others_euv = {}

    weight = 0 # temp

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
        self.group = setupDto.group
        self.index = setupDto.index
        self.B = setupDto.B
        self.G = self.perGroup = setupDto.G # (For now,) G == groups num == users num of one group
    
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

    def maskedInputCollection(self):
        tag = BasicSARound.MaskedInputCollection.name
        PORT = BasicSARound.MaskedInputCollection.value
        
        # quantization first
        # TODO quantization weights (xu)

        s_pk_dic = {}
        for i, user_dic in self.others_keys.items():
            v = int(i)
            s_pk_dic[v] = user_dic.get("s_pk")
        
        segment_yu = generateMaskedInputOfSegments(
                self.index,
                self.bu, 
                self.weight,
                self.my_keys["s_sk"], 
                self.B,
                self.G,
                self.group,
                self.perGroup,
                self.euv_list, 
                s_pk_dic,
                self.p,
                self.R
        )
        print(f'segment_yu: {segment_yu}')
        request = {"group": self.group, "index": self.index, "segment_yu": segment_yu}  # request example: {"group": 0, "index":0, "segment_yu": {0: y0}, {1: y1}}

        # receive sending_yu_list from server
        response = sendRequestAndReceive(self.HOST, PORT, tag, request)

        # U3 = survived users in round2(MaskedInputCollection) = users_last used in round4(unmasking)
        self.U3 = response['users']

if __name__ == "__main__":
    client = HeteroSAClient()
    client.setUp()
    client.advertiseKeys()
    client.shareKeys()
    client.maskedInputCollection()

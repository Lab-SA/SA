import os, sys, json

sys.path.append(os.path.dirname(os.path.abspath(os.path.dirname(__file__))))

from CommonValue import BasicSARound
from BasicSAClient import sendRequestAndReceive
from dto.HeteroSetupDto import HeteroSetupDto
import BasicSA as sa
from HeteroSAg import generateMaskedInputOfSegments
import learning.federated_main as fl
import learning.models_helper as mhelper
from ast import literal_eval

SIZE = 2048
ENCODING = 'utf-8'

class HeteroSAClient:
    HOST = 'localhost'
    PORT = 7000
    xu = 0  # temp. local model of this client

    n = t = g = p = R = 0 # common values
    group = 0
    index = 0
    B = []
    G = perGroup = 0
    
    my_keys = {}    # c_pk, c_sk, s_pk, s_sk of this client
    s_pk_dic = {}   # other users' s_pk(public key) dic
    c_pk_dic = {}   # other users' c_pk(public key) dic
    euv_list = []   # euv of this client
    others_euv = {}

    weight = 0 # temp
    model = {}

    def setUp(self):
        tag = BasicSARound.SetUp.name

        # response: HeteroSetupDto
        response = sendRequestAndReceive(self.HOST, self.PORT, tag, {})
        setupDto = json.loads(json.dumps(response), object_hook=lambda d: HeteroSetupDto(**d)) #
        #print(setupDto)
        
        self.n = setupDto.n
        self.t = setupDto.t
        self.g = setupDto.g
        self.p = setupDto.p
        self.R = setupDto.R
        self.group = setupDto.group
        self.index = setupDto.index
        self.B = setupDto.B
        self.G = self.perGroup = setupDto.G # (For now,) G == groups num == users num of one group

        self.data = setupDto.data
        global_weights = mhelper.dic_of_list_to_weights(literal_eval(setupDto.weights))
        self.weights_interval = setupDto.weights_interval

        if self.model == {}:
            self.model = fl.setup()
        fl.update_model(self.model, global_weights)
        local_model, local_weight, local_loss = fl.local_update(self.model, self.data, 0) # epoch 0 (temp)
        self.weight = local_weight
    
    def advertiseKeys(self):
        tag = BasicSARound.AdvertiseKeys.name

        (c_pk, c_sk), (s_pk, s_sk) = sa.generateKeyPairs()
        self.my_keys["c_pk"] = c_pk
        self.my_keys["c_sk"] = c_sk 
        self.my_keys["s_pk"] = s_pk
        self.my_keys["s_sk"] = s_sk
        request = {"group": self.group, "index": self.index, "c_pk": c_pk, "s_pk": s_pk}
        print(f'reqeust : {request}')
        # send {"group:, "index", "c_pk": c_pk, "s_pk": s_pk} to server in json format
        # receive other users' public keys from server in json format
        response = sendRequestAndReceive(self.HOST, self.PORT, tag, request)

        # store response on client
        # example: {"0": {"c_pk": "2123", "s_pk": "3333"}, "1": {"c_pk": "1111", "s_pk": "2222"}}
        self.s_pk_dic = {}
        self.c_pk_dic = {}
        for i, user_dic in response.items():
            v = int(i)
            self.s_pk_dic[v] = user_dic["s_pk"]
            self.c_pk_dic[v] = user_dic["c_pk"]


    def shareKeys(self):
        tag = BasicSARound.ShareKeys.name

        # t = threshold, u = user index
        # request = [[u, v1, euv], [u, v2, euv], ...]
        self.euv_list, self.bu = sa.generateSharesOfMask(
            self.t,
            self.index,
            self.my_keys["s_sk"], 
            self.my_keys["c_sk"], 
            self.c_pk_dic,
            self.R
        )
        request = {"index": self.index, "euv": self.euv_list}

        # receive euv_list from server in json format
        response = sendRequestAndReceive(self.HOST, self.PORT, tag, request)

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
        
        segment_yu = generateMaskedInputOfSegments(
                self.index,
                self.bu, 
                self.weight,
                self.my_keys["s_sk"], 
                self.B,
                self.G,
                self.group,
                self.perGroup,
                self.weights_interval,
                self.euv_list, 
                self.s_pk_dic,
                self.p,
                self.R
        )
        
        request = {"group": self.group, "index": self.index, "segment_yu": segment_yu}  # request example: {"group": 0, "index":0, "segment_yu": {0: y0}, {1: y1}}

        # receive sending_yu_list from server
        response = sendRequestAndReceive(self.HOST, self.PORT, tag, request)

        # U3 = survived users in round2(MaskedInputCollection) = users_last used in round4(unmasking)
        self.U3 = response['users']

    def unmasking(self): # same as unmasking of BasicSACLient
        tag = BasicSARound.Unmasking.name

        # U2 = survived users in round1(shareKeys) = users_previous
        U2 = list(self.others_euv.keys())

        s_sk_shares_dic, bu_shares_dic = sa.unmasking(
            self.index,
            self.my_keys["c_sk"], 
            self.others_euv, 
            self.c_pk_dic,
            U2, 
            self.U3
        )
        # requests example: {"idx": 0, "ssk_shares": {2: s20_sk, 3: s30_sk, ...}, "bu_shares": {1: b10, 4: b40, ...}]}
        request = {"index": self.index, "ssk_shares": str(s_sk_shares_dic), "bu_shares": str(bu_shares_dic)}
        print(request)

        # send u and dropped users' s_sk, survived users' bu in json format
        sendRequestAndReceive(self.HOST, self.PORT, tag, request)
    
if __name__ == "__main__":
    client = HeteroSAClient()
    for i in range(5): # round
        client.setUp()
        client.advertiseKeys()
        client.shareKeys()
        client.maskedInputCollection()
        client.unmasking()

import os, sys, copy
sys.path.append(os.path.dirname(os.path.abspath(os.path.dirname(__file__))))

from MainServer import MainServer
from BasicSA import getCommonValues, reconstructPvu, reconstructPu, reconstruct, generatingOutput
from CommonValue import BasicSARound
from ast import literal_eval
import learning.federated_main as fl
import learning.models_helper as mhelper
import SecureProtocol as sp

model = {}
users_keys = {}
yu_list = []
n = 0
threshold = 0
R = 0
usersNow = 0

### deprecated

# broadcast common value
def setUp():
    global n, threshold, R, model, usersNow

    tag = BasicSARound.SetUp.name
    port = BasicSARound.SetUp.value
    
    commonValues = getCommonValues()
    R = commonValues["R"]
    n = 4 # expected
    
    server = MainServer(tag, port, n)
    server.start()
    
    usersNow = server.userNum
    n = usersNow
    threshold = usersNow - 2 # temp
    commonValues["n"] = n
    commonValues["t"] = threshold

    if model == {}:
        model = fl.setup()
    model_weights_list = mhelper.weights_to_dic_of_list(model.state_dict())
    user_groups = fl.get_user_dataset(usersNow)

    response = []
    for i in range(usersNow):
        response_i = copy.deepcopy(commonValues)
        response_i["index"] = i
        response_i["data"] = [int(k) for k in user_groups[i]]
        response_i["weights"] = model_weights_list
        response.append(response_i)
    server.foreachIndex(response)

def advertiseKeys():
    global users_keys, usersNow

    tag = BasicSARound.AdvertiseKeys.name
    port = BasicSARound.AdvertiseKeys.value
    server = MainServer(tag, port, usersNow)
    server.start()
    usersNow = server.userNum

    # requests example: {"c_pk":"VALUE", "s_pk": "VALUE"}
    requests = server.requests

    # make response
    # response example: {0: {"index":0, "c_pk":"VALUE", "s_pk": "VALUE"}, 1: {"index":0, "c_pk":"VALUE", "s_pk": "VALUE"} }
    response = {}
    for v, request in enumerate(requests):
        requestData = request[1]  # (socket, data)
        users_keys[v] = requestData  # store on server
        requestData['index'] = v # add index
        response[v] = requestData
    server.broadcast(response)


def shareKeys():
    global usersNow

    tag = BasicSARound.ShareKeys.name
    port = BasicSARound.ShareKeys.value
    server = MainServer(tag, port, usersNow)
    server.start()
    usersNow = server.userNum

    # (one) request example: {0: [(0, 0, e00), (0, 1, e01) ... ]}
    # requests example: [{0: [(0, 0, e00), ... ]}, {1: [(1, 0, e10), ... ]}, ... ]
    requests = server.requests

    # response example: { 0: [e00, e10, e20, ...], 1: [e01, e11, e21, ... ] ... }
    response = {}
    requests_euv = []
    for request in requests:
        requestData = request[1]  # (socket, data)
        for idx, data in requestData.items(): #only one
            response[idx] = {}  # make dic
            requests_euv.append(data)
    for request in requests_euv:
        for (u, v, euv) in request:
            try:
                response[str(v)][u] = euv
            except KeyError:  # drop-out # TODO save U2
                print("KeyError")
                pass

    server.foreach(response)
    
def maskedInputCollection():
    global yu_list, usersNow

    tag = BasicSARound.MaskedInputCollection.name
    port = BasicSARound.MaskedInputCollection.value
    server = MainServer(tag, port, usersNow)
    server.start()
    usersNow = server.userNum

    # if u3 dropped
    # (one) request example: {"idx":0, "yu":y0}
    requests = server.requests

    # response example: { "users": [0, 1, 2 ... ] }
    response = []
    for request in requests:
        requestData = request[1]  # (socket, data)
        response.append(int(requestData["idx"]))
        yu_ = mhelper.dic_of_list_to_weights(requestData["yu"])
        yu_list.append(yu_)

    server.broadcast({"users": response})

def unmasking():
    global yu_list, R, users_keys, usersNow, model

    tag = BasicSARound.Unmasking.name
    port = BasicSARound.Unmasking.value
    server = MainServer(tag, port, usersNow)
    server.start()
    usersNow = server.userNum

    # (one) request: {"idx": u, "ssk_shares": s_sk_shares_dic, "bu_shares": bu_shares_dic}
    # if u2, u3 dropped, requests: [{"idx": 0, "ssk_shares": {2: s20_sk, 3: s30_sk}, "bu_shares": {1: b10, 4: b40}}, ...]
    requests = server.requests

    s_sk_shares_dic = {}     # {2: [s20_sk, s21_sk, ... ], 3: [s30_sk, s31_sk, ... ], ... }
    bu_shares_dic = {}       # {0: [b10, b04, ... ], 1: [b10, b14, ... ], ... }

    # get s_sk_shares_dic, bu_shares_dic of user2\3, user3
    for request in requests:
        requestData = request[1]  # (socket, data)
        ssk_shares = literal_eval(requestData["ssk_shares"])
        for i, share in ssk_shares.items():
            try: 
                s_sk_shares_dic[i].append(share)
            except KeyError:
                s_sk_shares_dic[i] = [share]
                pass
        bu_shares = literal_eval(requestData["bu_shares"])
        for i, share in bu_shares.items():
            try: 
                bu_shares_dic[i].append(share)
            except KeyError:
                bu_shares_dic[i] = [share]
                pass
    
    # reconstruct s_sk of users2\3
    s_sk_dic = {}
    for i, ssk_shares in s_sk_shares_dic.items(): # first, reconstruct ssk_u <- ssk_u,v
        s_sk_dic[i] = reconstruct(ssk_shares)
    # recompute p_vu
    user3list = list(bu_shares_dic.keys())
    sum_pvu = 0
    for u in user3list:
        for v, s_sk in s_sk_dic.items():
            pvu = reconstructPvu(v, u, s_sk, users_keys[u]["s_pk"], R)
            sum_pvu = sum_pvu + pvu
            #sum_xu = sum_xu + pvu
    
    sum_pu = 0
    # recompute p_u of users3
    for i, bu_shares in bu_shares_dic.items(): # first, reconstruct ssk_u <- ssk_u,v
        pu = reconstructPu(bu_shares, R)
        sum_pu = sum_pu + pu
        #sum_xu = sum_xu - pu
    
    # sum_yu
    mask = sum_pvu - sum_pu
    sum_xu = generatingOutput(yu_list, mask)
    
    # update global model with averaging
    model = fl.update_globalmodel(model, sum_xu)
    
    # End
    server.broadcast("[Server] End protocol")
    fl.test_model(model)


if __name__ == "__main__":
    for i in range(5): # 5 rounds
        setUp()
        advertiseKeys()
        shareKeys()    
        maskedInputCollection()
        unmasking()

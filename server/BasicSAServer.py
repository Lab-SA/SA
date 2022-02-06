import os, sys
sys.path.append(os.path.dirname(os.path.abspath(os.path.dirname(__file__))))

from MainServer import MainServer
from BasicSA import getCommonValues, reconstructPvu, reconstructPu, reconstruct
from CommonValue import BasicSARound
from ast import literal_eval

users_keys = {}
sum_yu = 0
usersNum = 0
threshold = 0
R = 0

# broadcast common value
def setUp():
    global usersNum, threshold, R

    tag = BasicSARound.SetUp.name
    port = BasicSARound.SetUp.value
    server = MainServer(tag, port)
    server.start()

    commonValues = getCommonValues()
    usersNum = commonValues["n"]
    threshold = commonValues["t"]
    R = commonValues["R"]
    server.broadcast(commonValues)

def advertiseKeys():
    global users_keys

    tag = BasicSARound.AdvertiseKeys.name
    port = BasicSARound.AdvertiseKeys.value
    server = MainServer(tag, port)
    server.start()

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
    tag = BasicSARound.ShareKeys.name
    port = BasicSARound.ShareKeys.value
    server = MainServer(tag, port)
    server.start()

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
    global sum_yu

    tag = BasicSARound.MaskedInputCollection.name
    port = BasicSARound.MaskedInputCollection.value
    server = MainServer(tag, port)
    server.start()

    # if u3 dropped
    # (one) request example: {"idx":0, "yu":y0}
    requests = server.requests

    # response example: { "yu_list": [{0: y0}, {1: y1}, {2: y2}, ... ] }
    response = {}
    for request in requests:
        requestData = request[1]  # (socket, data)
        response[requestData["idx"]] = requestData["yu"]
        sum_yu = sum_yu + int(requestData["yu"])

    server.broadcast({"yu_list": response})

def unmasking():
    global usersNum, sum_yu, R, users_keys
    sum_xu = sum_yu # sum(xu) is sum of user3's xu

    tag = BasicSARound.Unmasking.name
    port = BasicSARound.Unmasking.value
    server = MainServer(tag, port)
    server.start()

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
    for u in user3list:
        for v, s_sk in s_sk_dic.items():
            pvu = reconstructPvu(v, u, s_sk, users_keys[u]["s_pk"], R)
            sum_xu = sum_xu + pvu
    
    # recompute p_u of users3
    for i, bu_shares in bu_shares_dic.items(): # first, reconstruct ssk_u <- ssk_u,v
        pu = reconstructPu(bu_shares, R)
        sum_xu = sum_xu - pu
    
    return sum_xu


if __name__ == "__main__":
    setUp()
    advertiseKeys()
    shareKeys()    
    maskedInputCollection()
    final = unmasking()
    print("[Server] sum_xu: ", final)

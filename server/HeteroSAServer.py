import os, sys
from ast import literal_eval

sys.path.append(os.path.dirname(os.path.abspath(os.path.dirname(__file__))))

from MainServer import MainServer
from BasicSA import getCommonValues
import HeteroSAg as hetero
from dto.HeteroSetupDto import HeteroSetupDto, HeteroKeysRequestDto
from CommonValue import BasicSARound
import learning.federated_main as fl
import SecureProtocol as sp

users_keys = {}
n = 4 # expected (== G * perGroup == G * G)
threshold = 1
R = 0
B = [] # The SS Matrix B
G = 2 # group num
perGroup = 2
usersNow = 0
segment_yu = {}

# broadcast common value
def setUp():
    global n, threshold, R, B, usersNow, G, perGroup

    tag = BasicSARound.SetUp.name
    port = BasicSARound.SetUp.value
    
    server = MainServer(tag, port, n)
    server.start()

    usersNow = server.userNum
    n = usersNow
    threshold = usersNow - 2 # temp

    commonValues = getCommonValues()
    R = commonValues["R"]
    g = commonValues["g"]
    p = commonValues["p"]

    # Segment Grouping Strategy: G x G Segment selection matrix B
    B = hetero.SS_Matrix(G)
    
    response = []
    for i in range(G):
        for j in range(perGroup):
            response_ij = HeteroSetupDto(
                n, threshold, g, p, R, i, i*perGroup + j, B, G
            )._asdict()
            response.append(response_ij)
    server.foreachIndex(response)

def advertiseKeys():
    global users_keys, usersNow, G

    tag = BasicSARound.AdvertiseKeys.name
    port = BasicSARound.AdvertiseKeys.value
    server = MainServer(tag, port, usersNow)
    server.start()
    usersNow = server.userNum

    # requests example: {"group":, "index":, "c_pk":"VALUE", "s_pk": "VALUE"}
    requests = server.requests

    # make response
    # response example: {"INDEX": ("c_pk":"VALUE", "s_pk": "VALUE")}
    for request in requests:
        requestData = request[1]  # (socket, data)
        index = requestData["index"]
        users_keys[index] = {"c_pk": requestData["c_pk"], "s_pk": requestData["s_pk"]}
    server.broadcast(users_keys)


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
            except KeyError:  # drop-out
                print("KeyError: drop-out!")
                pass

    server.foreach(response)

surviving_users = []

def maskedInputCollection():
    global segment_yu, usersNow, G, surviving_users

    tag = BasicSARound.MaskedInputCollection.name
    port = BasicSARound.MaskedInputCollection.value
    server = MainServer(tag, port, usersNow)
    server.start()
    usersNow = server.userNum

    # if u3 dropped
    # (one) request example: {"group":0, "index":0, "segment_yu":{0: y0, 1: y1}}
    requests = server.requests

    # response example: { "users": [0, 1, 2 ... ] }
    segment_yu = {i: {j: [] for j in range(G)} for i in range(G)} # i: segment level, j: quantization level
    for request in requests:
        requestData = request[1]  # (socket, data)
        index = int(requestData["index"])
        surviving_users.append(index)
        for i, segment in requestData["segment_yu"].items():
            for q, yu in segment.items():
                # yu_ = fl.dic_of_list_to_weights(yu)
                segment_yu[int(i)][int(q)].append(yu)

    server.broadcast({"users": surviving_users})
    print(f'surviving_users: {surviving_users}')
    print(f'segment_yu: {segment_yu}')

def unmasking():
    global segment_yu, B, G, R, users_keys, usersNow, model, perGroup, surviving_users, n

    tag = BasicSARound.Unmasking.name
    port = BasicSARound.Unmasking.value
    server = MainServer(tag, port, usersNow)
    server.start()
    usersNow = server.userNum

    # (one) request: {"index": u, "ssk_shares": s_sk_shares_dic, "bu_shares": bu_shares_dic}
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
    
    # reconstruct s_sk of drop-out users
    s_sk_dic = hetero.reconstructSSKofSegments(B, G, perGroup, s_sk_shares_dic)
    
    # unmasking
    segment_xu = hetero.unmasking(
        hetero.getSegmentInfoFromB(B, G, perGroup), 
        G, 
        segment_yu, 
        surviving_users, 
        users_keys, 
        s_sk_dic,
        bu_shares_dic, 
        R
    )
    print(f'segment_xu: {segment_xu}')

    # TODO dequantization encoded xu

    # update global model

    # End
    server.broadcast("[Server] End protocol")

if __name__ == "__main__":
    setUp()
    advertiseKeys()
    shareKeys()
    maskedInputCollection()
    unmasking()
    
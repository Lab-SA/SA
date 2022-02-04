import os, sys
sys.path.append(os.path.dirname(os.path.abspath(os.path.dirname(__file__))))

from MainServer import MainServer
from BasicSA import getCommonValues, reconstructPuv, reconstructPu

users = {}
totalNum = 4
yu = 0

# broadcast common value
def setUp():
    server = MainServer('ServerSetUp', 7000)
    server.start()

    commonValues = getCommonValues()
    server.broadcast(commonValues)

def advertiseKeys():
    server = MainServer('AdvertiseKeys', 7010)
    server.start()

    # requests example: {"c_pk":"VALUE", "s_pk": "VALUE"}
    requests = server.requests

    # make response
    # response example: {0: {"index":0, "c_pk":"VALUE", "s_pk": "VALUE"}, 1: {"index":0, "c_pk":"VALUE", "s_pk": "VALUE"} }
    response = {}
    for v, request in enumerate(requests):
        requestData = request[1]  # (socket, data)
        users[v] = requestData  # store on server

        requestData['index'] = v  # add index
        response[v] = requestData

    server.broadcast(response)


def shareKeys():
    server = MainServer('ShareKeys', 7020)
    server.start()

    # (one) request example: [ 0, (0, 0, e00), (0, 1, e01) ... ]
    # requests example: [ [ 0, (0, 0, e00), ... ], [ 1, (1, 0, e10), ... ], ... ]
    requests = server.requests

    # response example: { 0: [e00, e10, e20, ...], 1: [e01, e11, e21, ... ] ... }
    response = {}
    for request in requests:
        requestData = request[1]  # (socket, data)
        idx = requestData[0]
        response[idx] = []  # make list
    for request in requests:
        requestData = request[1]  # (socket, data)
        for i, data in enumerate(requestData):
            if i == 0:
                continue
            (u, v, euv) = data
            try:
                response[v].append(euv)
            except KeyError:  # drop-out # TODO save U2
                pass

    server.foreach(response)

    
def MaskedInputCollection():
    server = MainServer('MaskedInputCollection', 7030)
    server.start()

    # if u3 dropped
    # requests example: { (0, y1), (1, y2), (3, y3), ... }
    requests = server.requests

    # response example: { 0, 1, 3, ... }
    response = {}
    for i, request in enumerate(requests):
        requestData = request[1]  # (socket, data)
        response[i] = requestData[0]
        yu = yu + requestData[1]

    server.broadcast(response)

def Unmasking():
    server = MainServer('Unmasking', 7040)
    server.start()

    # if u2, u3 dropped
    # requests example: { [{0: s02_sk, 1: s03_sk, ...}, {1: b01, 4: b04, ...}], ... }
    requests = server.requests

    drop_usr = {}       # {0: {0: s02_sk, 1: s03_sk, ...}, 1: {0: s12_sk, 1: s13_sk, ...}, ... }
    survive_usr = {}    # {0: {1: b01, 4: b04, ...}, 1: {0: b10, 4: b14, ...}, ... }
    share_list = {}     # {0: [s02_sk, s12_sk, ... ], 1: [s03_sk, s13_sk, ... ], ... }
    bu_list = {}        # {0: [b10, b40, ... ], 1: [b01, b41, ... ], 2: [], ... }
    requestData = []

    for request in requests:
        requestData.append(requests[request])
        for i, data in enumerate(requestData):
            drop_usr[i] = data[0]
            survive_usr[i] = data[1]

    drop_num = totalNum - server.userNum
    for n in range(drop_num):
        share_list[n] = []
    for n in range(totalNum):
        bu_list[n] = []
    for n in range(drop_num):
        for i in range(server.userNum):
            share_list[n].append(drop_usr[i][n])
    for n in range(totalNum):
        for i in range(server.userNum):
            if n in survive_usr[i]:
                bu_list[n].append(survive_usr[i][n])
    
    # recompute p_vu
    for d_usr in range(drop_num):
        for usr in range(server.userNum):
            p_uv = reconstructPuv(d_usr, usr, share_list[d_usr])
            yu = yu + p_uv
    
    # recompute p_u
    for i in range(totalNum):
        p_u = reconstructPu(bu_list[i])
        yu = yu - p_u

    # z = sum(yu) - sum(p_u) + sum(p_vu)
    
    
if __name__ == "__main__":
    advertiseKeys() # Round 0
    shareKeys() # Round 1
    MaskedInputCollection() # Round 2
    Unmasking() # Round 4

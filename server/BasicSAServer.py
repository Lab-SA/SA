import os, sys
sys.path.append(os.path.dirname(os.path.abspath(os.path.dirname(__file__))))

from MainServer import MainServer
from BasicSA import getCommonValues

users = {}

# broadcast common value
def setUp():
    server = MainServer('ServerSetUp')
    server.start()

    commonValues = getCommonValues()
    server.broadcast(commonValues)

def advertiseKeys():
    server = MainServer('AdvertiseKeys')
    server.start()

    # requests example: {"c_pk":"VALUE", "s_pk": "VALUE"}
    requests = server.requests

    # make response
    # response example: {0: {"index":0, "c_pk":"VALUE", "s_pk": "VALUE"}, 1: {"index":0, "c_pk":"VALUE", "s_pk": "VALUE"} }
    response = {}
    for v, request in enumerate(requests):
        requestData = request[1] # (socket, data)
        users[v] = requestData # store on server

        requestData['index'] = v # add index
        response[v] = requestData
    
    server.broadcast(response)

def shareKeys():
    server = MainServer('ShareKeys')
    server.start()

    # (one) request example: [ 0, (0, 0, e00), (0, 1, e01) ... ]
    # requests example: [ [ 0, (0, 0, e00), ... ], [ 1, (1, 0, e10), ... ], ... ]
    requests = server.requests

    # response example: { 0: [e00, e10, e20, ...], 1: [e01, e11, e21, ... ] ... }
    response = {} 
    for request in requests:
        requestData = request[1] # (socket, data)
        idx = requestData[0]
        response[idx] = [] # make list
    for request in requests:
        requestData = request[1] # (socket, data)
        for i, data in enumerate(requestData):
            if i == 0:
                continue
            (u, v, euv) = data
            try:
                response[v].append(euv)
            except KeyError: # drop-out # TODO save U2
                pass
    
    server.foreach(response)

if __name__ == "__main__":
    setUp()
    advertiseKeys() # Round 0
    shareKeys() # Round 1

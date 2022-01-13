from MainServer import MainServer

def AdvertiseKeysSocket():
    server = MainServer('AdvertiseKeys')
    server.start()
    requests = server.requests

    # make response
    # response example: {0: {"index":0, "c_pk":"VALUE", "s_pk": "VALUE"}, 1: {"index":0, "c_pk":"VALUE", "s_pk": "VALUE"} }
    response = {}
    for (v, data) in enumerate(requests):
        request_dic = data[1]
        request_dic['index'] = v # add index

        response[v] = request_dic
    
    server.broadcast(response)

if __name__ == "__main__":
    AdvertiseKeysSocket() # Round 0

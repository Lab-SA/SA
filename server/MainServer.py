import socket
import json
import time

HOST, PORT = 'localhost', 20
SIZE = 1024
ENCODING = 'ascii'
t = 4 #temp
interval = 60 # second

def AdvertiseKeysSocket():
    start = end = time.time()
    userNum = 0
    requests = []

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind((HOST, PORT))
        s.settimeout(10) #temp
        s.listen()
        print('[AdvertiseKeys] Server started')

        while (end-start) < interval:
            try:
                clientSocket, addr = s.accept()
                print('[AdvertiseKeys] Client: {0}'.format(addr))
                request = str(clientSocket.recv(SIZE), ENCODING)  # receive client data
                print('[AdvertiseKeys] Client request: {0}'.format(request))
                userNum = userNum + 1

                # request example: {"c_pk":"VALUE", "s_pk": "VALUE"}
                request_dic = json.loads(request)
                requests.append((clientSocket, request_dic))
            except socket.timeout:
                pass
            
            end = time.time()

        # check threshold
        if t > userNum:
            print('[AdvertiseKeys] Exception: insufficient {0} users with {1} threshold'.format(userNum, t))
            raise Exception("Need at least {0} users, but only {1} user(s) responsed".format(t, userNum))
        
        # make response
        # response example: {0: {"index":0, "c_pk":"VALUE", "s_pk": "VALUE"}, 1: {"index":0, "c_pk":"VALUE", "s_pk": "VALUE"} }
        response = {}
        for (v, data) in enumerate(requests):
            request_dic = data[1]
            request_dic['index'] = v # add index

            response[v] = request_dic
        
        # send response (broadcast)
        for (v, data) in enumerate(requests):
            clientSocket = data[0]
            response_json = json.dumps(response)
            clientSocket.sendall(bytes(response_json, ENCODING))

        s.close()
        print('[AdvertiseKeys] Server finished')

if __name__ == "__main__":
    AdvertiseKeysSocket() # Round 0

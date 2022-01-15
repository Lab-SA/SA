import json
import socket
import time
from MainClient import MainClient

def advertiseKeys(c_pk, s_pk):
    request = {"c_pk": c_pk, "s_pk": s_pk}  # temp
    # response = {}

    client = MainClient('AdvertiseKeys')
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect((client.HOST, client.PORT))
    print("connected!")

    # send (c_pk, s_pk) to server in json format
    s.sendall(bytes(json.dumps(request), client.ENCODING))
    print(f"[Client] send request {request}")

    s.close()


def shareKeys(euv):
    # euv(encrypted shares of bu and s_sk)
    request = euv  # temp. [] format
    response = {}

    client = MainClient('ShareKeys')
    client.startTime = client.endTime = time.time()
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect((client.HOST, client.PORT))
    print("connected!")

    # receive other users' public keys from server in json format
    while (client.endTime - client.startTime) < client.interval:
        try:
            response = json.loads(s.recv(client.SIZE, client.ENCODING))
            print(f"[Client] receive response {response}")
        except socket.timeout:
            pass
        client.endTime = time.time()

    # send euv(encrypted shares of bu and s_sk) to server
    s.sendall(bytes(request, client.ENCODING))
    print(f"[Client] send request {request}")

    s.close()
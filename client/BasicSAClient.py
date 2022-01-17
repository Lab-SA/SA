import json
import socket


HOST, PORT = 'localhost', 7
SIZE = 1024
ENCODING = 'ascii'

def advertiseKeys(c_pk, s_pk):
    request = {"c_pk": c_pk, "s_pk": s_pk}  # temp
    response = {}

    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect(HOST, PORT)
    print("connected!")

    # send (c_pk, s_pk) to server in json format
    s.sendall(bytes(json.dumps(request), ENCODING))
    print(f"[Client] send request {request}")

    # receive other users' public keys from server in json format
    response = json.loads(s.recv(SIZE, ENCODING))
    print(f"[Client] receive response {response}")

    s.close()

    return response


def shareKeys(euv):
    # euv(encrypted shares of bu and s_sk)
    request = euv  # temp. [] format
    response = []

    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect(HOST, PORT)
    print("connected!")

    # send euv(encrypted shares of bu and s_sk) to server in list format
    s.sendall(bytes(request, ENCODING))
    print(f"[Client] send request {request}")

    # receive euv_list from server in json format
    # change euv_list format from json to list and store
    response = json.loads(s.recv(SIZE, ENCODING))
    print(f"[Client] receive response {response}")

    s.close()

    return response


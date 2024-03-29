import json, socket, os, sys

sys.path.append(os.path.dirname(os.path.abspath(os.path.dirname(__file__))))
import BasicSA as sa
from CommonValue import BasicSARound
import learning.federated_main as fl
import learning.models_helper as mhelper

SIZE = 2048
ENCODING = 'utf-8'


def sendRequest(host, port, tag, request):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect((host, port))
    # print(f"[{tag}] Server connected!")

    # add tag to request
    request['request'] = tag

    # send request
    s.sendall(bytes(json.dumps(request) + "\r\n", ENCODING))
    # print(f"[{tag}] Send request (no response)")

def sendRequestAndReceive(host, port, tag, request):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect((host, port))
    # print(f"[{tag}] Server connected!")

    # add tag to request
    request['request'] = tag

    # send request
    s.sendall(bytes(json.dumps(request) + "\r\n", ENCODING))
    # print(f"[{tag}] Send request")
    # print(f"[{tag}] Send {request}")

    # receive server response
    # response must ends with "\r\n"
    receivedStr = ''
    while True:
        received = str(s.recv(SIZE), ENCODING)
        if received.endswith("\r\n"):
            received = received.replace("\r\n", "")
            receivedStr = receivedStr + received
            break
        receivedStr = receivedStr + received

    response = ''
    try:
        response = json.loads(receivedStr)
        # print(f"[{tag}] Receive response")
        # print(f"[{tag}] receive response {response}")
        return response
    except json.decoder.JSONDecodeError:
        #raise Exception(f"[{tag}] Server response with: {response}")
        print(f"[{tag}] Server response with: {receivedStr}")
        exit
    finally:
        s.close()

class BasicSAClient:
    HOST = 'localhost'
    PORT = 7000
    # xu = 0  # temp. local model of this client

    commonValues = {}  # {"n": n, "t": t, "g": g, "p": p, "R": R} from server in setup stage
    u = -1  # u = user index
    my_c_pk = my_c_sk = my_s_pk = my_s_sk = 0  # c_pk, c_sk, s_pk, s_sk of this client
    s_pk_dic = {}  # other users' s_pk(public key) dic
    c_pk_dic = {}  # other users' c_pk(public key) dic
    euv_list = []  # euv of this client
    others_euv = {}
    bu = 0  # random element to be used as a seed for PRG
    U3 = []  # survived users in round2(MaskedInputCollection)
    model = {}

    def setUp(self):
        tag = BasicSARound.SetUp.name

        # response: {"n": n, "t": t, "g": g, "p": p, "R": R, "index": index, "data", "weights"}
        response = sendRequestAndReceive(self.HOST, self.PORT, tag, {})
        self.commonValues = response
        self.u = response["index"]
        self.data = response["data"]  # user_groups[idx]
        global_weights = mhelper.dic_of_list_to_weights(response["weights"])

        if self.model == {}:
            self.model = fl.setup()
        self.model.load_state_dict(global_weights)
        local_model, local_weight, local_loss = fl.local_update(self.model, self.data, 0)  # epoch 0 (temp)
        self.weight = local_weight

    def advertiseKeys(self):
        tag = BasicSARound.AdvertiseKeys.name

        (c_pk, c_sk), (s_pk, s_sk) = sa.generateKeyPairs()
        self.my_c_pk = c_pk
        self.my_c_sk = c_sk
        self.my_s_pk = s_pk
        self.my_s_sk = s_sk
        request = {"index": self.u, "c_pk": c_pk, "s_pk": s_pk}

        # send {"c_pk": c_pk, "s_pk": s_pk} to server in json format
        # receive other users' public keys from server in json format
        response = sendRequestAndReceive(self.HOST, self.PORT, tag, request)

        # store response on clients
        # example: {"0": {"c_pk": "2123", "s_pk": "3333", "index": 0}, "1": {"c_pk": "1111", "s_pk": "2222", "index": 1}}
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
            self.commonValues["t"],
            self.u,
            # self.my_keys["s_sk"],
            # self.my_keys["c_sk"],
            self.my_s_sk,
            self.my_c_sk,
            self.c_pk_dic,
            self.commonValues["R"]
        )
        request = {"index": self.u, "euv": self.euv_list}

        # receive euv_list from server in json format
        response = sendRequestAndReceive(self.HOST, self.PORT, tag, request)

        # store euv from server to client in dic
        """for v, euv in enumerate(response):  # example response = ["e01", "e11"]
            others_euv[v] = euv
        """
        # if response format {v: euv}. example = {0: "e00", 1: "e10"}
        self.others_euv = {}
        for v, euv in response.items():
            self.others_euv[int(v)] = euv

    def maskedInputCollection(self):
        tag = BasicSARound.MaskedInputCollection.name

        yu = sa.generateMaskedInput(
            self.u,
            self.bu,
            self.weight,
            # self.my_keys["s_sk"],
            self.my_s_sk,
            self.euv_list,
            self.s_pk_dic,
            self.commonValues["R"]
        )

        request = {"index": self.u, "yu": mhelper.weights_to_dic_of_list(yu)}  # request example: {"idx":0, "yu":y0}

        # receive sending_yu_list from server
        response = sendRequestAndReceive(self.HOST, self.PORT, tag, request)

        # U3 = survived users in round2(MaskedInputCollection) = users_last used in round4(unmasking)
        self.U3 = response['users']

    def unmasking(self):
        tag = BasicSARound.Unmasking.name

        # U2 = survived users in round1(shareKeys) = users_previous
        U2 = list(self.others_euv.keys())

        s_sk_shares_dic, bu_shares_dic = sa.unmasking(
            self.u,
            # self.my_keys["c_sk"],
            self.my_c_sk,
            self.others_euv,
            self.c_pk_dic,
            U2,
            self.U3
        )
        # requests example: {"idx": 0, "ssk_shares": {2: s20_sk, 3: s30_sk, ...}, "bu_shares": {1: b10, 4: b40, ...}]}
        request = {"index": self.u, "ssk_shares": str(s_sk_shares_dic), "bu_shares": str(bu_shares_dic)}

        # send u and dropped users' s_sk, survived users' bu in json format
        sendRequestAndReceive(self.HOST, self.PORT, tag, request)


if __name__ == "__main__":
    client = BasicSAClient()  # test

    for i in range(5):  # 5 rounds
        client.setUp()
        client.advertiseKeys()
        client.shareKeys()
        client.maskedInputCollection()
        client.unmasking()

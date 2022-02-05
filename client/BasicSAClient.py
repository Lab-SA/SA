import json, socket, os, sys
sys.path.append(os.path.dirname(os.path.abspath(os.path.dirname(__file__))))
import BasicSA as sa
from CommonValue import BasicSARound

SIZE = 2048
ENCODING = 'ascii'

def sendRequestAndReceive(host, port, tag, request):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect((host, port))
    print(f"[{tag}] Server connected!")

    # add tag to request
    request['request'] = tag
    
    # send request
    s.sendall(bytes(json.dumps(request), ENCODING))
    print(f"[{tag}] Send {request}")

    # receive
    receivedStr = str(s.recv(SIZE), ENCODING)
    response = ''
    try:
        response = json.loads(receivedStr)
        print(f"[{tag}] receive response {response}")
        return response
    except json.decoder.JSONDecodeError:
        #raise Exception(f"[{tag}] Server response with: {response}")
        print(f"[{tag}][Error] Server response with: {receivedStr}")
        exit
    finally:
        s.close()

class BasicSAClient:
    HOST = 'localhost'
    xu = 0  # temp. local model of this client

    commonValues = {}  # {"n": n, "t": t, "g": g, "p": p, "R": R} from server in setup stage
    u = 0  # u = user index
    my_keys = {}  # c_pk, c_sk, s_pk, s_sk of this client
    others_keys = {}  # other users' public key dic
    euv_list = []  # euv of this client
    others_euv = {}
    bu = 0  # random element to be used as a seed for PRG
    U3 = []  # survived users in round2(MaskedInputCollection)

    def setUp(self):
        tag = BasicSARound.SetUp.name
        PORT = BasicSARound.SetUp.value

        # response: {"n": n, "t": t, "g": g, "p": p, "R": R}
        response = sendRequestAndReceive(self.HOST, PORT, tag, {})
        self.commonValues = response

    def advertiseKeys(self):
        tag = BasicSARound.AdvertiseKeys.name
        PORT = BasicSARound.AdvertiseKeys.value

        ((c_pk, c_sk), (s_pk, s_sk)) = sa.generateKeyPairs()
        self.my_keys["c_pk"] = c_pk
        self.my_keys["c_sk"] = c_sk 
        self.my_keys["s_pk"] = s_pk
        self.my_keys["s_sk"] = s_sk
        request = {"c_pk": c_pk, "s_pk": s_pk}

        # send {"c_pk": c_pk, "s_pk": s_pk} to server in json format
        # receive other users' public keys from server in json format
        response = sendRequestAndReceive(self.HOST, PORT, tag, request)

        # store response on client
        # example: {"0": {"c_pk": "2123", "s_pk": "3333", "index": 0}, "1": {"c_pk": "1111", "s_pk": "2222", "index": 1}}
        self.others_keys = response


    def shareKeys(self):
        tag = BasicSARound.ShareKeys.name
        PORT = BasicSARound.ShareKeys.value

        for i, user_dic in self.others_keys.items():
            print(user_dic)
            if self.my_keys["c_pk"] == user_dic["c_pk"] and self.my_keys["s_pk"] == user_dic["s_pk"]:
                u = user_dic["index"]  # u = user index
                break
            else:
                continue

        # t = threshold, u = user index
        # request = [[u, v1, euv], [u, v2, euv], ...]
        euv_list, bu = sa.generateSharesOfMask(
            self.commonValues["t"], 
            u, 
            self.my_keys["s_sk"], 
            self.my_keys["c_sk"], 
            self.others_keys, 
            self.commonValues["R"])
        self.bu = bu
        request = euv_list

        # receive euv_list from server in json format
        response = sendRequestAndReceive(self.HOST, PORT, tag, request)

        # store euv from server to client in dic
        """for v, euv in enumerate(response):  # example response = ["e01", "e11"]
            others_euv[v] = euv
        """
        # if response format {v: euv}. example = {0: "e00", 1: "e10"}
        for v, euv in response.items():
            self.others_euv[v] = euv


    def MaskedInputCollection(self):
        tag = BasicSARound.MaskedInputCollection.name
        PORT = BasicSARound.MaskedInputCollection.value
        request = {}
        response = {}

        s_pk_dic = {}
        for i, user_dic in self.others_keys.items():
            v = i
            s_pk_dic[i] = user_dic.get("s_pk")
        yu = sa.generateMaskedInput(
            self.u, 
            self.bu, 
            self.xu, 
            self.my_keys["s_sk"], 
            self.euv_list, 
            s_pk_dic, 
            self.commonValues["R"])
        request = {self.u: yu}  # request example: {0: y0}

        # receive sending_yu_list from server
        response = sendRequestAndReceive(self.HOST, PORT, tag, request)

        # U3 = survived users in round2(MaskedInputCollection) = users_last used in round4(unmasking)
        self.U3 = response


    def Unmasking(self):
        tag = BasicSARound.Unmasking.name
        PORT = BasicSARound.Unmasking.value
        request = {}
        s_sk_shares_dic = {}
        bu_shares_dic = {}
        temp_request = (s_sk_shares_dic, bu_shares_dic)

        c_pk_dic = {}
        for i, user_dic in self.others_keys.items():
            v = i
            c_pk_dic[i] = user_dic.get("c_pk")

        # U2 = survived users in round1(shareKeys) = users_previous
        U2 = list(self.others_euv.keys())

        # requests example: {u: [{0: s02_sk, 1: s03_sk, ...}, {1: b01, 4: b04, ...}]}
        temp_request = sa.unmasking(
            self.u, 
            self.my_keys["c_sk"], 
            self.euv_list, 
            c_pk_dic, 
            U2, 
            self.U3)
        request = {self.u: list(temp_request)}

        # send u and dropped users' s_sk, survived users' bu in json format
        sendRequestAndReceive(self.HOST, PORT, tag, request)

if __name__ == "__main__":
    client = BasicSAClient() # test

import os, sys, copy, random
sys.path.append(os.path.dirname(os.path.abspath(os.path.dirname(__file__))))

from MainServer import MainServer
from TurboBaseServer import TurboBaseServer
from BasicSA import getCommonValues
from Turbo import generateRandomVectorSet, reconstruct
from CommonValue import TurboRound

groupNum = 0
perGroup = 0
usersNum = 0
threshold = 0
R = 0
mask_u_dic = {}
drop_out = {}
alpha = beta = []

# send common values and index, group of each user
def setUp():
    global groupNum, usersNum, threshold, R, perGroup, mask_u_dic, alpha, beta

    tag = TurboRound.SetUp.name
    port = TurboRound.SetUp.value
    server = MainServer(tag, port)
    server.start()

    commonValues = getCommonValues()
    usersNum = commonValues["n"]
    threshold = commonValues["t"]
    R = commonValues["R"]

    perGroup = 2 # temp
    commonValues["perGroup"] = perGroup

    # generate common alpha/beta
    commonValues["alpha"], commonValues["beta"] = alpha, beta = generateRandomVectorSet(perGroup, commonValues["p"])

    usersNow = len(server.requests) # MUST be multiple of perGroup
    groupNum = int(usersNow / perGroup)
    response = []
    mask_u_dic = {i:{} for i in range(groupNum)}
    for i in range(groupNum):
        for j in range(perGroup):
            response_ij = copy.deepcopy(commonValues)
            response_ij["group"] = i
            response_ij["index"] = j
            mask_u = random.randrange(1, R) # 1~R
            mask_u_dic[i][j] = mask_u
            response_ij["mask_u"] = mask_u
            response.append(response_ij)
    server.foreachIndex(response)

def turbo():
    global groupNum, usersNum, perGroup, drop_out

    tag = TurboRound.Turbo.name
    tag_value = TurboRound.TurboValue.name
    tag_final = TurboRound.TurboFinal.name
    port = TurboRound.Turbo.value
    
    server = TurboBaseServer(tag, tag_value, tag_final, port, groupNum, usersNum, perGroup)
    server.start()
    drop_out = server.drop_out

def final():
    global mask_u_dic, drop_out, groupNum, alpha, beta

    tag = TurboRound.Final.name
    port = TurboRound.Final.value

    server = MainServer(tag, port)
    server.start()
    final_tildeS = {}
    final_barS = {}

    for request in server.requests:
        requestData = request[1]  # (socket, data)
        index = int(requestData["index"])
        final_tildeS[index] = int(requestData["final_tildeS"])
        final_barS[index] = int(requestData["final_barS"])
        drop_out[groupNum-1] = requestData["drop_out"] # last group
    
    # reconstruct
    reconstruct(alpha, beta, final_tildeS, final_barS)
    server.broadcast({})

    # calculate sum of surviving user's mask_u
    for group, item in drop_out.items():
        group = int(group)
        for i in item: # drop out
            i = int(i)
            del mask_u_dic[group][i]
    
    surviving_mask_u = 0
    for group, item in mask_u_dic.items():
        surviving_mask_u = surviving_mask_u + sum(item.values())
    
    # final value (sum_xu)
    return sum(final_tildeS.values()) / len(final_tildeS) - surviving_mask_u

if __name__ == "__main__":
    setUp()
    turbo()
    final_value = final()
    print(f'final value: {final_value}')

import os, sys, copy, random
sys.path.append(os.path.dirname(os.path.abspath(os.path.dirname(__file__))))

from MainServer import MainServer
from TurboBaseServer import TurboBaseServer
from BasicSA import getCommonValues
from Turbo import generateRandomVectorSet
from CommonValue import TurboRound

groupNum = 0
perGroup = 0
usersNum = 0
threshold = 0
R = 0
mask_u_list = []

# send common values and index, group of each user
def setUp():
    global groupNum, usersNum, threshold, R, perGroup, mask_u_list

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
    commonValues["alpha"], commonValues["beta"] = generateRandomVectorSet(perGroup, commonValues["p"])

    usersNow = len(server.requests) # MUST be multiple of perGroup
    groupNum = int(usersNow / perGroup)
    response = []
    for i in range(groupNum):
        for j in range(perGroup):
            response_ij = copy.deepcopy(commonValues)
            response_ij["group"] = i
            response_ij["index"] = j
            mask_u = random.randrange(1, R) # 1~R
            mask_u_list.append(mask_u)
            response_ij["mask_u"] = mask_u
            response.append(response_ij)
    server.foreachIndex(response)

def turbo():
    global groupNum, usersNum, perGroup

    tag = TurboRound.Turbo.name
    tag_value = TurboRound.TurboValue.name
    tag_final = TurboRound.TurboFinal.name
    port = TurboRound.Turbo.value
    
    server = TurboBaseServer(tag, tag_value, tag_final, port, groupNum, usersNum, perGroup)
    server.start()

def final():
    global mask_u_list

    tag = TurboRound.Final.name
    port = TurboRound.Final.value

    server = MainServer(tag, port)
    server.start()
    final_tildeS = []
    final_barS = []

    for request in server.requests:
        requestData = request[1]  # (socket, data)
        final_tildeS.append(int(requestData["final_tildeS"]))
        final_barS.append(int(requestData["final_barS"]))
    server.broadcast({})

    return sum(final_tildeS) / len(final_tildeS) - sum(mask_u_list)

if __name__ == "__main__":
    setUp()
    turbo()
    final_value = final()
    print(f'final value: {final_value}')

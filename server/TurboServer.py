import os, sys, copy
sys.path.append(os.path.dirname(os.path.abspath(os.path.dirname(__file__))))

from MainServer import MainServer
from GroupServer import GroupServer
from BasicSA import getCommonValues
from CommonValue import TurboRound

usersNum = 0
threshold = 0
R = 0

# send common values and index, group of each user
def setUp():
    global usersNum, threshold, R

    tag = TurboRound.SetUp.name
    port = TurboRound.SetUp.value
    server = MainServer(tag, port)
    server.start()

    commonValues = getCommonValues()
    usersNum = commonValues["n"]
    threshold = commonValues["t"]
    R = commonValues["R"]

    usersNow = len(server.requests)
    response = []
    for i in range(usersNow):
        response_i = copy.deepcopy(commonValues)
        response_i["group"] = 0 # TODO: grouping
        response_i["index"] = i
        response.append(response_i)
    server.foreachIndex(response)

if __name__ == "__main__":
    setUp()

import os, sys, json
sys.path.append(os.path.dirname(os.path.abspath(os.path.dirname(__file__))))

from MainServer import MainServer
from BasicSA import getCommonValues
from HeteroSAg import SS_Matrix
from dto.HeteroSetupDto import HeteroSetupDto
from CommonValue import BasicSARound
import learning.federated_main as fl
import SecureProtocol as sp

users_keys = {}
n = 4 # expected (== G * perGroup == G * G)
threshold = 1
R = 0
B = [] # The SS Matrix B
G = 2 # group num
perGroup = 2
usersNow = 0

# broadcast common value
def setUp():
    global n, threshold, R, B, usersNow, G, perGroup

    tag = BasicSARound.SetUp.name
    port = BasicSARound.SetUp.value
    
    server = MainServer(tag, port, n)
    server.start()

    usersNow = server.userNum
    n = usersNow
    threshold = usersNow - 2 # temp

    commonValues = getCommonValues()
    R = commonValues["R"]
    g = commonValues["g"]
    p = commonValues["p"]

    # Segment Grouping Strategy: G x G Segment selection matrix B
    B = SS_Matrix(G)
    
    response = []
    for i in range(G):
        for j in range(perGroup):
            response_ij = HeteroSetupDto(
                n, threshold, g, p, R, i, j, B
            )._asdict()
            response.append(response_ij)
    server.foreachIndex(response)

if __name__ == "__main__":
    setUp()
    
# Lab-SA: Turbo-Aggregate
import random
import numpy as np

def grouping(users, n):
    # users = [list] ordered user index list
    # n = the number of users per one group
    # L = the number of groups
    group_dic = {}
    L = 0

    for i in range(0, len(users), n):
        group_dic[L] = tuple(users[i:i + n])
        L += 1

    return group_dic, L

"""# compute tildeX = x + u_i + r_ij
def computeMaskedModel(x, u_i, r_ij):
    # u_i = random.randrange(1, R)  # 1~R random mask vector from server
    # tildeX = masked model

    tildeX = x + u_i + r_ij

    return tildeX

def additiveMasking(i, j):
    r_ij = 0
    # numpy?

    return r_ij
"""

# update aggregate value tildeS
def updateTildeS(l, n, tildeS_dic, tildeX_dic):
    # tildeS = a variable that each user holds corresponding to the aggregated masked models from the previous group
    # tildeS_dic = [dic] tildeS of users in l-1 group
    # tildeX_dic = [dic] tildeX between user i(this) and users in l-1

    if l == 1:
        tildeS = 0
    else:
        tildeS = sum(tildeS_dic.values()) / n + sum(tildeX_dic.values())

    return tildeS


# generate the encoded model barX
def generateEncodedModel():

    return 0


# compute the coded aggregate value barS
def computeBarS():
    return 0


def reconstruct():
    return 0


def computeFinal():
    return 0

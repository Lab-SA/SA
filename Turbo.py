import random
from scipy.interpolate import lagrange
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


# compute tildeX = x + u_i + r_ij
def computeMaskedModel(x, u_i, r_ij_dic):
    # x = local model
    # u_i 1~R random mask vector from server
    # tildeX_dic = [dic] masked model(=tildeX) between user i(this) and users in l-1
    tildeX_dic = {}

    for j in range(r_ij_dic):
        tildeX_dic[j] = x + u_i + r_ij_dic[j]

    return tildeX_dic


def additiveMasking(i, next_users, q):
    # next_users = users' index in other group (= j)
    # r_ij_dic = additive random vector dictionary by user i
    n = len(next_users)
    r_ij_dic = {}
    temp_sum = 0

    for j in next_users:
        r_ij = random.randrange(1, q) # temp
        r_ij_dic[j] = r_ij

    temp_sum = sum(r_ij_dic.values())
    r_ij_dic[n-1] = 0 - temp_sum

    return r_ij_dic


# update aggregate value tildeS
def updateSumofMaskedModel(l, n, pre_tildeS_dic, tildeX_dic, p_sum_dic):
    # l = group index of this user.  ex) 1,2,3,...,L
    # tildeS = a variable that each user holds corresponding to the aggregated masked models from the previous group
    # n = the number of users per one group
    # pre_tildeS_dic = [dic] tildeS of users in l-1 group
    # tildeX_dic = [dic] masked model(=tildeX) between user i(this) and users in l-1

    """global p_sum_dic = partial sum.
        ex) [1:0, 2:0, ..., l:s(l), l+1:s(l+1)]
    """

    if l == 1:
        p_sum_dic[l] = 0
        p_sum_dic[l+1] = computePartialSum(l, n, pre_tildeS_dic)
        tildeS = 0
    elif l > 1:
        tildeS = sum(pre_tildeS_dic.values()) / n + sum(tildeX_dic.values())
        p_sum_dic[l+1] = computePartialSum(l, n, pre_tildeS_dic)
    else:
        print("wrong group index")

    return tildeS, p_sum_dic


# compute partial summation = p_sum (= s(l+1))
def computePartialSum(l, pre_tildeS_dic):
    # initial partial sum s(1), s(2) = 0

    p_sum = sum(pre_tildeS_dic.values()) / len(pre_tildeS_dic)

    return p_sum


# generate the encoded model barX
def generateEncodedModel(next_users, q, tildeX_dic):
    """
        next_users = users' index of l+1 group
        x = 다음 그룹의 유저들 각각에 랜덤 할당된 수 (= alpha)
        y = tildeX_dic.values()
        이 (x,y)로 만들어진 보간다항식 = f_i

        alpha와 중복되지 않는 랜덤 값 = beta
        beta를 f_i에 넣어서 나오는 값들이 바로 barX (= encoded model)
        이 barX들의 모음 = barX_dic
    """
    n = len(next_users)
    barX_dic = {}

    alpha_list = random.sample(range(1, q), n)
    beta_dic = {}

    for j in next_users:
        beta = random.randrange(1, q)
        while True:
            if beta not in alpha_list and beta not in beta_dic.values():
                beta_dic[j] = beta
                break
            else:
                continue

    x = np.array(alpha_list)
    y = np.array(list(tildeX_dic.values()))
    f_i = lagrange(x, y)
    co = f_i.coef[::-1]

    for j in beta_dic.values():
        barX = 0
        for i in range(n):
            barX += co[i] * (j**i)
        barX_dic[i] = barX

    return barX_dic


# update the encoded aggregate value barS
def updateSumofEncodedModel(l, pre_barX_dic, p_sum_dic):
    # pre_barX_dic = encoded model dic of group l-1
    # barS = encoded_sum

    barS = p_sum_dic[l] + sum(pre_barX_dic.values())
    return barS


def reconstruct():
    # temp
    return 0


def computeFinalOutput(x, final_tildeS, u_i_dic):
    # final_tildeS = users' masked model dic in final stage
    # u_i_dic = all u_i (random mask from server)

    sum_x = sum(final_tildeS.values()) / len(final_tildeS) - sum(u_i_dic)
    return sum_x

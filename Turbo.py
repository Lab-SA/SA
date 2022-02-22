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

    for j in range(len(r_ij_dic)):
        tildeX_dic[j] = x + u_i + r_ij_dic[j]

    return tildeX_dic


def additiveMasking(i, next_users, q):
    # next_users = users' index in other group (= j)
    # r_ij_dic = additive random vector dictionary by user i
    n = len(next_users)
    r_ij_dic = {}
    temp_sum = 0

    for j in range(len(next_users)-1):
        r_ij = random.randrange(1, q)  # temp
        r_ij_dic[next_users[j]] = r_ij

    temp_sum = sum(r_ij_dic.values())
    r_ij_dic[next_users[n-1]] = 0 - temp_sum

    return r_ij_dic


# update aggregate value tildeS
def updateSumofMaskedModel(l, n, pre_tildeS_dic, tildeX_dic, p_sum_dic):
    # l = group index of this user.  ex) 0,1,2,...,L
    # tildeS = a variable that each user holds corresponding to the aggregated masked models from the previous group
    # n = the number of users per one group
    # pre_tildeS_dic = [dic] tildeS of users in l-1 group
    # tildeX_dic = [dic] masked model(=tildeX) between user i(this) and users in l-1

    if l == 0:
        p_sum_dic[l] = 0
        p_sum_dic[l+1] = computePartialSum(l, n, pre_tildeS_dic)
        tildeS = 0
    elif l > 0:
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
def generateEncodedModel(next_users, alpha_list, beta_list, tildeX_dic):
    """
        next_users = users' index of l+1 group
        x = 다음 그룹의 유저들 각각에 랜덤 할당된 수 (= alpha)
        y = tildeX_dic.values()
        이 (x,y)로 만들어진 보간다항식 = f_i

        alpha와 중복되지 않는 랜덤 값 = beta
        beta를 f_i에 넣어서 나오는 값들이 바로 barX (= encoded model)
        이 barX들의 모음 = barX_dic
    """
    barX_dic = {}

    f_i = generateLagrangePolynomial(alpha_list, list(tildeX_dic.values()))

    for j in range(len(beta_list)):
        barX = np.polyval(f_i, beta_list[j])
        barX_dic[j] = barX

    return barX_dic

# generate random vector alpha_list, beta_list
def generateRandomVectorSet(next_users, q):
    n = len(next_users)
    alpha_list = random.sample(range(1, q), n)
    beta_list = []

    for j in next_users:
        beta = random.randrange(1, q)
        while True:
            if beta not in alpha_list and beta not in beta_list:
                beta_list.append(beta)
                break
            else:
                continue
    return alpha_list, beta_list


def generateLagrangePolynomial(x_list, y_list):
    """
    if 1. generate f_i of user i in group l (this client),
        x_list = alpha_list, y_list = list(tildeX_dic.values())

    if 2. generate f_k of user k in group l-1 (reconstruct)
        x_list = alphat_list + beta_list, y_list = list(tildeX_dic.values()) + list(barX_dic.values())

    return Lagrange Polynomial f_i
    """

    x = np.array(x_list)
    y = np.array(y_list)
    f_i = lagrange(x, y)
    # co = f_i.coef[::-1]

    return f_i


# update the encoded aggregate value barS
def updateSumofEncodedModel(l, pre_barX_dic, p_sum_dic):
    # pre_barX_dic = encoded model dic of group l-1
    # barS = encoded_sum

    barS = p_sum_dic[l] + sum(pre_barX_dic.values())
    return barS

# reconstruct missing values of dropped users.
# and then update pre_tildeX
def reconstruct(alpha_list, beta_list, pre_tildeX, pre_barX):
    # pre_tildeX = [dic] { surviving users'(group l-1) index: surviving users' tildeX }
    # pre_barX = [dic] { surviving users'(group l-1) index: surviving users' barX }
    # f_k = lagrange polynomial of group l-1 for reconstruct

    x_list = list(pre_tildeX.keys()) + list(pre_barX.keys())
    for i in pre_tildeX.keys():
        x_list.append(alpha_list[i])
    for i in pre_barX.keys():
        x_list.append(beta_list[i])
    y_list = list(pre_tildeX.values()) + list(pre_barX.values())

    f_k = generateLagrangePolynomial(x_list, y_list)

    for index in range(len(alpha_list)):
        alpha = alpha_list[index]
        if alpha not in x_list:
            recon_tildeX = np.polyval(f_k, alpha)
            pre_tildeX[index] = recon_tildeX
        else:
            continue

    return pre_tildeX


def computeFinalOutput(x, final_tildeS, u_i_dic):
    # final_tildeS = users' masked model dic in final stage
    # u_i_dic = all u_i (random mask from server)

    sum_x = sum(final_tildeS.values()) / len(final_tildeS) - sum(u_i_dic)
    return sum_x

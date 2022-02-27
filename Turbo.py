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
def computeMaskedModel(x, u_i, next_users, q):
    # x = local model
    # u_i 1~R random mask vector from server
    # tildeX_dic = [dic] masked model(=tildeX) between user i(this) and users in l-1
    tildeX_dic = {}
    r_ij_dic = additiveMasking(next_users, q)
    print(f"r_ij_dic: {r_ij_dic}")

    for j in r_ij_dic.keys():
        temp = x + u_i + r_ij_dic[j]
        tildeX_dic[j] = temp

    return tildeX_dic


def additiveMasking(next_users, q):
    # next_users = users' index in other group (= j)
    # r_ij_dic = additive random vector dictionary by user i
    n = len(next_users)
    r_ij_dic = {}
    temp_sum = 0

    for j in range(n-1):
        r_ij = random.randrange(1, q)  # temp
        r_ij_dic[next_users[j]] = r_ij

    temp_sum = sum(r_ij_dic.values())
    temp_r = 0 - temp_sum
    r_ij_dic[next_users[n - 1]] = temp_r

    return r_ij_dic


# update aggregate value tildeS
def updateSumofMaskedModel(l, pre_tildeX_dic, pre_tildeS_dic):
    # l = group index of this user.  ex) 0,1,2,...,L
    # n = the number of users per one group
    # pre_tildeS_dic = [dic] tildeS of users in l-1 group
    # tildeX_dic = [dic] masked model(=tildeX) between user i(this) and users in l-1
    # tildeS = a variable that each user holds corresponding to the aggregated masked models from the previous group
    tildeS = 0
    n = len(pre_tildeS_dic)

    """
        initialize tildeS(0) = 0
        매개변수 때문에, group index 가 0일 때(즉 첫 번째 group 일 경우)는 사용자 측에서
        매개변수로 p_sum = 0, pre_tildeS = 0을 넣어 주어야 할 듯.
    """
    if l == 0:
        print("Initialize tildeS(0) = 0")
    elif l > 0:
        tildeS = sum(pre_tildeS_dic.values()) / n + sum(pre_tildeX_dic.values())
    else:
        print("wrong group index")

    return tildeS


# compute partial summation = p_sum (= s(l))
def computePartialSum(l, pre_tildeS_dic):
    p_sum = 0
    n = len(pre_tildeS_dic)

    # initial partial sum s(0), s(1) = 0
    if l == 0:
        print("Initialize p_sum(0) = 0")
    elif l > 0:
        p_sum = sum(pre_tildeS_dic.values()) / n
    else:
        print("wrong group index")

    return p_sum


# generate the encoded model barX
def generateEncodedModel(alpha_list, beta_list, tildeX_dic):
    """
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


def generateRandomVectorSet(next_users, q):
    # next_users = users' index of l+1 group
    n = len(next_users)
    alpha_list = random.sample(range(1, q), n)
    beta_list = []

    for j in next_users:
        while True:
            beta = random.randrange(1, q)
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

    if 2. generate g_i of user k in group l-1 (reconstruct)
        x_list = alphat_list + beta_list, y_list = list(tildeS_dic.values()) + list(barS_dic.values())

    return Lagrange Polynomial f_i
    """

    x = np.array(x_list)
    y = np.array(y_list)
    f_i = lagrange(x, y)
    # co = f_i.coef[::-1]

    return f_i


# update the encoded aggregate value barS
def updateSumofEncodedModel(pre_barX_dic, p_sum):
    # pre_barX_dic = encoded model dic of group l-1
    # barS = encoded_sum

    barS = p_sum + sum(pre_barX_dic.values())
    return barS


# reconstruct missing values of dropped users.
# and then update pre_tildeX
def reconstruct(alpha_list, beta_list, pre_tildeS_dic, pre_barS_dic):
    # pre_tildeS_dic = [dic] { surviving users'(group l-1) index: surviving users' tildeS }
    # pre_barS_dic = [dic] { surviving users'(group l-1) index: surviving users' barS }
    # g_i = lagrange polynomial of group l-1 for reconstruct
    x_list = []

    for i in pre_tildeS_dic.keys():
        x_list.append(alpha_list[i])
    for i in pre_barS_dic.keys():
        x_list.append(beta_list[i])
    y_list = list(pre_tildeS_dic.values()) + list(pre_barS_dic.values())

    g_i = generateLagrangePolynomial(x_list, y_list)

    for index in range(len(alpha_list)):
        alpha = alpha_list[index]
        if alpha not in x_list:
            recon_tildeS = np.polyval(g_i, alpha)
            pre_tildeS_dic[index] = recon_tildeS
        else:
            continue

    return pre_tildeS_dic


def computeFinalOutput(final_tildeS, u_i_dic):
    # final_tildeS = users' masked model dic in final stage
    # u_i_dic = all u_i (random mask from server)
    final_n = len(final_tildeS)

    sum_x = sum(final_tildeS.values()) / final_n - sum(u_i_dic)
    return sum_x


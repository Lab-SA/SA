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


# compute tildeX = x + u_i + r_ij => dic of 1d list
def computeMaskedModel(x, u_i, next_users, q):
    # x = [1d flatten list] local model
    # u_i 1~R [int] random mask vector from server
    # tildeX_dic = [dic] masked model(=tildeX) between user i(this) and users in l-1 group

    tildeX = {}
    r_ij_dic = additiveMasking(next_users, q)
    # print(f"r_ij_dic = {r_ij_dic}")
    for j, r_ij in r_ij_dic.items():
        mask = u_i + r_ij
        maskedx = np.array(x) + mask
        tildeX[j] = maskedx.tolist()
        print(f"mask={mask}")  # tildeX = {maskedx}
    # print(f"tildeX = {tildeX}")
    return tildeX


def additiveMasking(next_users, q):
    # next_users = number of users (-> index = j)
    # r_ij_dic = additive random vector dict
    n = next_users
    r_ij_dic = {}
    temp_sum = 0

    for j in range(n - 1):
        r_ij = random.randrange(1, q)  # temp
        r_ij_dic[j] = r_ij

    temp_sum = sum(r_ij_dic.values())
    temp_r = 0 - temp_sum
    r_ij_dic[n - 1] = temp_r

    return r_ij_dic


# update aggregate value tildeS => 0 or 1d list
def updateSumofMaskedModel(l, pre_tildeX_dic, pre_tildeS_dic):
    # l = group index of this user.  ex) 0,1,2,...,L
    # n = the number of users per one group
    # pre_tildeS_dic = [dic of list] tildeS of users in l-1 group
    # pre_tildeX_dic = [dic of list] masked model(=tildeX) between user i(this) and users in l-1
    # ex) pre_tildeX_dic={0:{0:[], 1:[]},1:{0:[], 1:[]}}
    # tildeS = a variable that each user holds corresponding to the aggregated masked models from the previous group

    # print(f"pre_tildeX_dic={pre_tildeX_dic}")

    if l == 0:
        tildeS = 0
        # int
        return tildeS

    else:
        tildeS = []
        p_sum = computePartialSum(l, pre_tildeS_dic)
        masked_sum = []
        for pair in zip(*pre_tildeX_dic.values()):
            masked_sum.append(sum(pair))

        if p_sum == 0:
            tildeS = masked_sum
        else:
            temp_sum = np.array(p_sum) + np.array(masked_sum)
            tildeS = temp_sum.tolist()
        return tildeS


# 0 or tensor
def computePartialSum(l, pre_tildeS_dic):
    # pre_tildeS_dic = [dic of list] ex) {0:[], 1: []}
    # print(f"pre_tildeS_dic = {pre_tildeS_dic}")
    # l = index of group

    if l <= 1:
        p_sum = 0
        # int
        return p_sum

    else:
        p_sum = []
        for pair in zip(*pre_tildeS_dic.values()):
            p_sum.append(sum(pair) / len(pair))
        return p_sum

# generate the encoded model barX
def generateEncodedModel(alpha_list, beta_list, tildeX):
    """
         f_i = Lagrange interpolation polynomial using the points (alpha, tildeX.values())
         => barX(=encoded model) = f_i(beta)
    """
    barX = {i: [] for i in range(len(beta_list))}

    print(f"alpha_list: {alpha_list}")
    print(f"beta_list: {beta_list}")

    cnt = 0
    for pair in zip(*tildeX.values()):
        f_i = generateLagrangePolynomial(alpha_list, list(pair))
        for idx, beta in enumerate(beta_list):
            temp = barX[idx]
            temp.append(np.polyval(f_i, beta))
            barX[idx] = temp
        cnt += 1

    return barX


def generateRandomVectorSet(next_users, q):
    # next_users = users' index of l+1 group
    alpha_list = random.sample(range(1, q), next_users)
    beta_list = []

    for j in range(next_users):
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
        x_list = alpha_list, y_list = list(tildeX.values())

    if 2. generate g_i of user k in group l-1 (reconstruct)
        x_list = alpha_list + beta_list, y_list = surviving tildeS.values()& barS.values()

    return Lagrange Polynomial f_i
    """

    x = np.array(x_list)
    y = np.array(y_list)
    f_i = lagrange(x, y)
    # co = f_i.coef[::-1]

    return f_i


# update the encoded aggregate value barS => 1d list
def updateSumofEncodedModel(l, pre_barX_dic, pre_tildeS_dic):
    # pre_barX_dic = encoded model dic of group l-1
    # barS = encoded_sum = p_sum + sum(pre_barX_dic.values())
    # print(f"pre_barX_dic={pre_barX_dic}")

    barS = []

    p_sum = computePartialSum(l, pre_tildeS_dic)
    encoded_sum = []

    for pair in zip(*pre_barX_dic.values()):
        encoded_sum.append(sum(pair))

    if p_sum == 0:
        barS = encoded_sum

    else:
        temp_sum = np.array(p_sum) + np.array(encoded_sum)
        barS = temp_sum.tolist()

    return barS


# reconstruct missing values of dropped users.
# and then update pre_tildeX
import numpy as np
from scipy.interpolate import lagrange

def reconstruct(alpha_list, beta_list, pre_tildeS_dic, pre_barS_dic):
    x_list = []
    for i in pre_tildeS_dic.keys():
        x_list.append(alpha_list[int(i)])

    drop_out = []
    pairidx = 0
    for index, alpha in enumerate(alpha_list):
        if alpha not in x_list:
            drop_out.append(index)
        else:
           pairidx = index

    if len(drop_out) == 0:
        return pre_tildeS_dic, drop_out

    for i in pre_barS_dic.keys():
        x_list.append(beta_list[int(i)])

    t = pre_tildeS_dic.get(pairidx)
    if isinstance(t, int):
        pair_dic = {0: []}
    else:
        pair_dic = {i: [] for i in range(len(t))}

    tildeS_zip = list(zip(*list(pre_tildeS_dic.values())))
    barS_zip = list(zip(*list(pre_barS_dic.values())))
    for i, pair in pair_dic.items():
        pair_dic[i] = list(tildeS_zip[i]) + list(barS_zip[i])

    gi_dic = {}
    for k, v in pair_dic.items():
        gi_dic[k] = generateLagrangePolynomial(x_list, v)

    for i in drop_out:
        recon_tildeS = []
        for g_i in gi_dic.values():
            recon_tildeS.append(np.polyval(g_i, alpha_list[i]))
        pre_tildeS_dic[i] = recon_tildeS

    return pre_tildeS_dic, drop_out


def computeFinalOutput(final_tildeS, mask_u_dic):
    # final_tildeS = users' masked model dic in final stage
    # mask_u_dic = all surviving u_l_i (random mask from server)

    surviving_mask_u = 0
    # print(f"mask_u_dic={mask_u_dic}")
    for group, item in mask_u_dic.items():
        # print(f"group={group}, sum={sum(item.values())}")
        surviving_mask_u = surviving_mask_u + sum(item.values())

    p_sum = computePartialSum(2, final_tildeS)
    sum_x = np.array(p_sum) - surviving_mask_u
    sum_x = sum_x.tolist()

    return sum_x

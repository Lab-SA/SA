import random
from scipy.interpolate import lagrange
import numpy as np
import learning.models_helper as mhelper

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


def partialSumofModel(x_dic, s_dic):
    # partial_sum = sum(s)/n + sum(x)

    x_sum = []
    for pair in zip(*x_dic.values()):
        x_sum.append(sum(pair))
    s_sum = computePartialSum(s_dic)

    if s_sum == 0:
        return x_sum
    else:
        return (np.array(s_sum) + np.array(x_sum)).tolist()


def computePartialSum(weights_dic):
    p_sum = []
    n = len(weights_dic)
    if n == 0 or weights_dic.get(0) == 0:
        return 0
    for pair in zip(*weights_dic.values()):
        p_sum.append(sum(pair) / n)
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

    for pair in zip(*tildeX.values()):
        f_i = generateLagrangePolynomial(alpha_list, list(pair))
        for idx, beta in enumerate(beta_list):
            barX[idx].append(np.polyval(f_i, beta))

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


# reconstruct missing values of dropped users.
# and then update pre_tildeX
import numpy as np
from scipy.interpolate import lagrange

def reconstruct(alpha_list, beta_list, tilde_dic, bar_dic):
    x_list = []
    for i in tilde_dic.keys():
        x_list.append(alpha_list[int(i)])

    drop_out = []
    for index, alpha in enumerate(alpha_list):
        if alpha not in x_list:
            drop_out.append(index)

    if len(drop_out) == 0:
        return tilde_dic, drop_out
    
    for i in bar_dic.keys():
        x_list.append(beta_list[int(i)])

    # generate function g
    tilde_zip = list(zip(*list(tilde_dic.values())))
    bar_zip = list(zip(*list(bar_dic.values())))
    g_list = []
    for i in range(mhelper.default_weights_size):
        g_list.append(generateLagrangePolynomial(x_list, list(tilde_zip[i]) + list(bar_zip[i])))

    for i in drop_out:
        tilde_dic[i] = [np.polyval(g, alpha_list[i]) for g in g_list] # reconstructed

    return tilde_dic, drop_out


def computeFinalOutput(final_tildeS, mask_u_dic):
    # final_tildeS = users' masked model dic in final stage
    # mask_u_dic = all surviving u_l_i (random mask from server)

    surviving_mask_u = 0
    # print(f"mask_u_dic={mask_u_dic}")
    for group, item in mask_u_dic.items():
        # print(f"group={group}, sum={sum(item.values())}")
        surviving_mask_u = surviving_mask_u + sum(item.values())

    p_sum = computePartialSum(final_tildeS)
    sum_x = np.array(p_sum) - surviving_mask_u
    sum_x = sum_x.tolist()

    return sum_x

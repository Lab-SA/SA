import random
from scipy.interpolate import lagrange
import numpy as np
from learning.utils import sum_weights, add_to_weights
from learning.federated_main import weights_to_dic_of_list, dic_of_list_to_weights
from iteration_utilities import deepflatten

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
        temp = u_i + r_ij_dic[j]
        masked_x = add_to_weights(x, temp)
        tildeX_dic[j] = masked_x

    return tildeX_dic


def additiveMasking(next_users, q):
    # next_users = number of users (-> index = j)
    # r_ij_dic = additive random vector dictionary by user i
    n = next_users
    r_ij_dic = {}
    temp_sum = 0

    for j in range(n-1):
        r_ij = random.randrange(1, q)  # temp
        r_ij_dic[j] = r_ij

    temp_sum = sum(r_ij_dic.values())
    temp_r = 0 - temp_sum
    r_ij_dic[n-1] = temp_r

    return r_ij_dic


# update aggregate value tildeS => tensor
def updateSumofMaskedModel(l, pre_tildeX_dic, pre_tildeS_dic):
    # l = group index of this user.  ex) 0,1,2,...,L
    # n = the number of users per one group
    # pre_tildeS_dic = [dic] tildeS of users in l-1 group
    # tildeX_dic = [dic] masked model(=tildeX) between user i(this) and users in l-1
    # tildeS = a variable that each user holds corresponding to the aggregated masked models from the previous group
    n = len(pre_tildeS_dic)

    """
        initialize tildeS(0) = 0
        매개변수 때문에, group index 가 0일 때(즉 첫 번째 group 일 경우)는 사용자 측에서
        매개변수로 p_sum = 0, pre_tildeS = 0을 넣어 주어야 할 듯.
    """
    if l == 0:
        print("Initialize tildeS(0) = 0")
        tildeS = 0
    elif l > 0:
        # tildeS = p_sum_dic + pre_tildeX_dic's weights_sum => [dic of list] + [dic of list]
        p_sum_dic = computePartialSum(l, pre_tildeS_dic)
        if p_sum_dic == 0:
            temp_tildeS = sum_weights(list(pre_tildeX_dic.values()))
            tildeS = dic_of_list_to_weights(temp_tildeS)
            return tildeS
        weights_sum = sum_weights(list(pre_tildeX_dic.values()))
        layer = list(weights_sum.keys())
        wArr = np.array(list(weights_sum.values()))
        pArr = np.array(list(p_sum_dic.values()))
        temp_tildeS = (wArr + pArr).tolist()
        tildeS = {lname:value for lname, value in zip(layer, temp_tildeS)}
        tildeS = dic_of_list_to_weights(tildeS)
        print(f"tildeS: {tildeS}")
    else:
        print("wrong group index")

    return tildeS


# compute partial summation = p_sum_dic (= s(l)) => dic of list type
def computePartialSum(l, pre_tildeS_dic):
    #pre_tildeS_dic = {user_idx:si_}
    print(f"l={l}, pre_tildeS_dic={pre_tildeS_dic}")
    # si_ = dic of list type
    n = len(pre_tildeS_dic)

    # initial partial sum s(0), s(1) = 0
    if l >= 1:
        p_sum = 0
        print("Initialize p_sum(0) = 0")
        return p_sum
    elif l > 1:
        tempArray = []
        for user_idx in pre_tildeS_dic.keys():
            layer = list(pre_tildeS_dic[user_idx].keys())
            temp = list(pre_tildeS_dic[user_idx].values())
            if user_idx == 0:
                tempArray = np.array(temp)
            else:
                tempArray = tempArray + np.array(temp)
        ret_list = (tempArray/n).tolist()
        # print(layer, ret_list)
        p_sum_dic = {lname: arr for lname, arr in zip(layer, ret_list)}
        print(f"p_sum_dic= {p_sum_dic}")
        return p_sum_dic
    else:
        print("wrong group index")
        return 0


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
    # tildeX_dic = maskedxij_
    # flatten_maskedxij = weights_to_1dList(tildeX_dic)
    print(f"alpha_list: {alpha_list}")
    print(f"beta_list: {beta_list}")
    # f_i = generateLagrangePolynomial(alpha_list, flatten_maskedxij)
    # print(f"flatten_maskedxij: {flatten_maskedxij}")
    # layer_shape_dic = {}
    # tildeX_changed = {}

    y = []

    layer_name = list(tildeX_dic[0].keys())
    print(layer_name)
    layer_dic = {}

    """for j, weights in tildeX_dic.items():
        j_weights = weights_to_dic_of_list(weights)
        tildeX_changed[j] = j_weights
    print(f"tildeX_changed: {tildeX_changed}")
    print(f"tildeX_changed[0] = {tildeX_changed[0]}")
    print(f"tildeX_changed[0].get(layer_name[0]) = {tildeX_changed[0].get(layer_name[0])}")
    """

    for layer in layer_name:
        a = list(deepflatten(tildeX_dic[0].get(layer)))
        b = list(deepflatten(tildeX_dic[1].get(layer)))
        layer_dic[layer] = list(zip(a, b))
    # print(f"layer_dic: {layer_dic}")

    for i in range(len(alpha_list)):
        barX_dic[i] = {}
        # barX_dic = { 0: {}, 1: {} }


    # user가 2명인 경우만 가능한 코드.. 구조수정필요
    userdic1 = {}
    userdic2 = {}
    for layer, li in layer_dic.items():
        a_ = []
        b_ = []
        for pair in li:
            y = list(pair)
            # print(f"y: {y}")
            f_i = generateLagrangePolynomial(alpha_list, y)
            a_.append(np.polyval(f_i, beta_list[0]))
            # print(f"a_={a_}")
            b_.append(np.polyval(f_i, beta_list[1]))
            # print(f"b_={b_}")
        userdic1[layer] = a_
        userdic2[layer] = b_

    barX_dic[0] = userdic1
    barX_dic[1] = userdic2
    # print(f"barX_dic: {barX_dic}")

    return barX_dic


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
        x_list = alpha_list, y_list = list(tildeX_dic.values())

    if 2. generate g_i of user k in group l-1 (reconstruct)
        x_list = alphat_list + beta_list, y_list = list(tildeS_dic.values()) + list(barS_dic.values())

    return Lagrange Polynomial f_i
    """

    x = np.array(x_list)
    y = np.array(y_list)
    f_i = lagrange(x, y)
    # co = f_i.coef[::-1]
    # print(f"라그랑제 보간다항식 f_i = {f_i}")

    return f_i


# update the encoded aggregate value barS => tensor type
def updateSumofEncodedModel(l, pre_barX_dic, pre_tildeS_dic):
    # pre_barX_dic = encoded model dic of group l-1
    # barS = encoded_sum
    p_sum_dic = computePartialSum(l, pre_tildeS_dic)
    # barS = p_sum + sum(pre_barX_dic.values())
    if p_sum_dic == 0:
        temp_barS = sum_weights(list(pre_barX_dic.values()))
        barS = dic_of_list_to_weights(temp_barS)
        return barS

    p_sum_dic = computePartialSum(l, pre_tildeS_dic)
    weights_sum = sum_weights(list(pre_tildeS_dic.values()))
    layer = list(weights_sum.keys())
    wArr = np.array(list(weights_sum.values()))
    pArr = np.array(list(p_sum_dic.values()))
    temp_barS = (wArr + pArr).tolist()
    barS = {lname: value for lname, value in zip(layer, temp_barS)}
    barS = dic_of_list_to_weights(barS)
    print(f"barS: {barS}")

    return barS


# reconstruct missing values of dropped users.
# and then update pre_tildeX
def reconstruct(alpha_list, beta_list, pre_tildeS_dic, pre_barS_dic):
    # pre_tildeS_dic = [dic] { surviving users'(group l-1) index: surviving users' tildeS }
    # pre_barS_dic = [dic] { surviving users'(group l-1) index: surviving users' barS }
    # g_i = lagrange polynomial of group l-1 for reconstruct
    # print(f"pre_tildeS_dic= {pre_tildeS_dic}")
    # print(f"pre_barS_dic= {pre_barS_dic}")

    x_list = []
    for i in pre_tildeS_dic.keys():
        x_list.append(alpha_list[int(i)])
    for i in pre_barS_dic.keys():
        x_list.append(beta_list[int(i)])

    y_list = list(pre_tildeS_dic.values()) + list(pre_barS_dic.values())
    g_i = generateLagrangePolynomial(x_list, y_list)

    drop_out = []
    for index, alpha in enumerate(alpha_list):
        if alpha not in x_list:
            recon_tildeS = np.polyval(g_i, alpha)
            pre_tildeS_dic[index] = recon_tildeS
            # print(f'alpha: {alpha_list[index]}, recon_tildeS: {recon_tildeS}')
            drop_out.append(index)
    
    return pre_tildeS_dic, drop_out


def computeFinalOutput(final_tildeS, mask_u_dic):
    # final_tildeS = users' masked model dic in final stage
    # mask_u_dic = all surviving u_l_i (random mask from server)

    surviving_mask_u = 0
    for group, item in mask_u_dic.items():
        surviving_mask_u = surviving_mask_u + sum(item.values())
    
    sum_x = sum(final_tildeS.values()) / len(final_tildeS) - surviving_mask_u
    return sum_x


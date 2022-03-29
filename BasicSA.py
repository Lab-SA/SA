# Lab-SA Basic SA for Federated Learning
import random, math
import numpy as np
import SecureProtocol as sp
from ast import literal_eval
from learning.utils import sum_weights, add_to_weights

g = 3 #temp
p = 7 #temp #BREA -> p = 2 ** 32 - 5

# Get common values for server set-up: n, t, ...
def getCommonValues():
    global g, p

    # R: domain
    # g: generator, p: prime
    R = 100 #temp
    # _g, _p = sp.generator()
    # g = _g
    # p = _p
    commonValues = {"g": 3, "p": 7, "R": R}
    return commonValues

# Generate two key pairs
def generateKeyPairs():
    global g, p
    c_pk, c_sk = sp.generateKeyPair(g, p)
    s_pk, s_sk = sp.generateKeyPair(g, p)
    return (c_pk, c_sk), (s_pk, s_sk)

# Generate secret-shares of s_sk and bu and encrypt those data
# users [dictionary]: all users of the current round
def generateSharesOfMask(t, u, s_sk, c_sk, users, R):
    global p

    bu = random.randrange(1, R) # 1~R
    s_sk_shares_list = sp.make_shares(s_sk, t, len(users))
    bu_shares_list = sp.make_shares(bu, t, len(users))
    euv_list = []

    for i, user_dic in users.items():
        v = int(i)
        c_pk = user_dic["c_pk"]
        s_uv = sp.agree(c_sk, c_pk, p)
        plainText = str([u, v, s_sk_shares_list[v], bu_shares_list[v]])
        euv = sp.encrypt(s_uv, plainText)
        euv_list.append((u, v, euv))

    return euv_list, bu

def generateMaskedInput(u, bu, xu, s_sk, euv_list, s_pk_dic, R):
    global p

    # compute p_uv
    p_uv_list = []
    for u, v, euv in euv_list: # euv_list = [ (u, v, euv), (u, v, euv) ... ]
        if u == v:
            continue
        s_uv = sp.agree(s_sk, s_pk_dic[v], p)
        random.seed(s_uv)
        p_uv = random.randrange(1, R) # 1~R
        if u < v:
            p_uv = -p_uv
        p_uv_list.append(p_uv)

    #compute bu
    random.seed(bu)
    pu = random.randrange(1, R) # 1~R

    # make masked xu(: dic of weights)
    mask = pu + sum(p_uv_list)
    yu = add_to_weights(xu, mask)
    return yu

# users_previous [list]: users who were alive in the previous round
# users_last [list]: users who were alive in the recent round
def unmasking(u, c_sk, euv_dic, c_pk_dic, users_previous, users_last, R):
    global p

    s_sk_shares_dic = {}
    bu_shares_dic = {}
    for v in users_previous:
        if v == u:
            continue
        try:
            idx = euv = -1
            for _v, _euv in euv_dic.items():
                if _v == v:
                    idx = _v
                    euv = _euv
                    break
            euv_dic.pop(idx)

            # decrypt
            s_uv = sp.agree(c_sk, c_pk_dic[v], p)
            plainText = sp.decrypt(s_uv, euv)
            _v, _u, s_sk_shares, bu_shares = literal_eval(plainText) # list

            if not(u == int(_u) and v == int(_v)):
                raise Exception('Something went wrong during reconstruction.')
            try:
                users_last.remove(v) # v is in U3
                bu_shares_dic[v] = bu_shares
            except ValueError: # v is in U2\U3
                s_sk_shares_dic[v] = s_sk_shares
        except:
            raise Exception('Decryption failed.')
    return s_sk_shares_dic, bu_shares_dic

def reconstruct(shares_list):
    return sp.combine_shares(shares_list)

def reconstructPvu(v, u, s_sk_v, s_pk_u, R):
    global p

    s_uv = sp.agree(s_sk_v, s_pk_u, p)
    random.seed(s_uv)
    p_vu = random.randrange(1, R)
    if v < u:
        p_vu = -p_vu
    return p_vu

def reconstructPu(bu_shares_list, R): # list of user u
    bu = sp.combine_shares(bu_shares_list)
    random.seed(bu)
    pu = random.randrange(1, R)
    return pu

def generatingOutput(yu_list, mask):
    sum_yu = sum_weights(yu_list)
    sum_xu = add_to_weights(sum_yu, mask)
    return sum_xu

def stochasticQuantization(x, q, p):
    # x = local model of user i
    # q = quantization level
    # p = modulo p

    # var_x = quantized x
    
    var_x = []
    ret_x = stochasticRounding(x, q)
    print("ret_x", len(ret_x[0]))
    for each_x in ret_x:
        # print("each_x: ", each_x)
        ko = np.array(each_x)
        # print("ndim: ", ko.shape)
        # print("=============!!==============", q * ko.reshape(-1))
        var_x.append(mappingX(q * np.array(each_x).reshape(-1), p))
        # print("=============^^==============", mappingX(q * np.array(each_x).reshape(-1), p))
        # print("||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||")
        # print("=============!!==============", ko.reshape(-1))
        # print("ndim: ", ko.shape)
    
    return var_x

def stochasticRounding(x, q):
    # x = local model of user i
    # q = quantization level

    # ret_list = return value list after rounding x
    # prob_list = probability list (weight for random.choices)
    # ret_x = rounded x
    ret_x = []
    for k in range(len(x)):
        print("x[k][0]: ", x[k][0])
        
        # ret_list = [(q ** x[k]) / q, (-(q ** x[k]) + 1) / q]
        ret_list = []
        prob_list = []
        for i in range(len(x[k])):
            ret_list.append([math.floor(q * x[k][i]) / q, (math.floor(q * x[k][i]) + 1) / q])
            prob_list.append([1 - (q * x[k][i] - math.floor(q * x[k][i])), q * x[k][i] - math.floor(q * x[k][i])])
        # print("prob_list: ", ret_list[0])
        # print("len(x[k]): ", len(x[k]))
        tx = []
        for weight in range(len(x[k])):
            r_choice = random.choices(ret_list[weight], prob_list[weight])
            tx.append(r_choice)
            # print("r_choice: ",r_choice)
            # tx.append(random.choices(ret_list[weight], prob_list[weight]))
        ret_x.append(tx)
    return ret_x

def mappingX(x, p):
    """mappingX(x, p) is to represent a negative integer in the finite field
    by using two’s complement representation"""
    # % mod 연산으로 대체가 가능한 부분인가...?
    
    y = np.where(x < 0, x + p, x)
    
    return y

def SS_Matrix(G):
    # G = the number of groups
    B = [['*' for x in range(G)] for y in range(G)]
    for g in range(G - 1):
        for r in range(G - g - 1):
            l = 2 * g + r
            B[l % G][g] = g
            B[l % G][g + r + 1] = g
    for i in range(G):
        for j in range(G):
            if B[i][j] == '*':
                B[i][j] = j
    return B

# generate G quantizers randomly
def generateQuantizers_heteroQ(G):
    Q = []
    for i in range(G):
        Q.append(random.randint(1, 100))
    return Q

# return quantization level q
def returnQuantizer(mode, l, g, B, Q):
    # mode = homo quantization(0) or hetero quantization(1)
    # l = segment index
    # g = group index
    # B = SS_Matrix
    # Q = a set of quantization level

    # q = quantization level
    if mode == 0:  # homo quantization
        q = Q[0]
        return q
    elif mode == 1:  # hetero quantization
        q = Q[B[l][g]]
        return q
    else:
        print("wrong input")
        return 0

def Quantization(x, G, q, r1, r2):
    # x = local model value of user i
    # G = the number of groups
    # q = quantization level
    # [r1, r2] = quantization range
    """ q = returnQuantizer(mode, l, g, B, Q)
    => Quantization(x, G, q) can do both homo quantization and hetero quantization. """

    # delK = quantization interval
    # T = discrete value from quantization range point list
    delK = (r2 - r1) / (q - 1)
    T = []
    for l in range(0, G):
        T.append(r1 + l * delK)

    for l in range(0, G - 1):
        if T[l] <= x < T[l + 1]:
            ret_list = [T[l], T[l+1]]
            prob_list = [(x - T[l]) / (T[l + 1] - T[l]), 1-((x - T[l]) / (T[l + 1] - T[l]))]
            ret_x = random.choices(ret_list, prob_list)
            break
    return ret_x


# just for testing
if __name__ == "__main__":
    print(3 ** 2205)

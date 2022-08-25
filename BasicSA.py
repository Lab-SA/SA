# Lab-SA Basic SA for Federated Learning
import random, math
import numpy as np
import SecureProtocol as sp
from ast import literal_eval
from learning.utils import sum_weights, add_to_weights

g = 31
p = 131

# Get common values for server set-up: n, t, ...
def getCommonValues():
    global g, p

    # R: domain
    # g: generator, p: prime
    R = 100 #temp
    # _g, _p = sp.generator()
    # g = _g
    # p = _p
    commonValues = {"g": g, "p": p, "R": R}
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
        if u == v: continue
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
def unmasking(u, c_sk, euv_dic, c_pk_dic, users_previous, users_last):
    global p

    s_sk_shares_dic = {}
    bu_shares_dic = {}
    for v in users_previous:
        if v == u:
            continue
        try:
            # decrypt
            s_uv = sp.agree(c_sk, c_pk_dic[v], p)
            plainText = sp.decrypt(s_uv, euv_dic[v])
            _v, _u, s_sk_shares, bu_shares = literal_eval(plainText) # list

            if not(u == int(_u) and v == int(_v)):
                raise Exception('Something went wrong during reconstruction.')
            
            # s_sk_shares for drop-out users / bu_shars for surviving users
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

def stochasticQuantization(weights, q, p):
    # weights = local model of user
    # q = quantization level
    # p = large prime

    quantized = []
    for x in weights:
        floor_qx = math.floor(q * x)
        selected = int(random.choices(
            population = [floor_qx / q, (floor_qx + 1) / q],
            weights = [1 - (q * x - floor_qx), q * x - floor_qx],
            k = 1 # select one
        )[0] * q)
        if selected < 0:
            selected = selected + p
        quantized.append(selected)

    return quantized

def convertToRealDomain(weights, q, p):
    # weights = local model of user
    # q = quantization level
    # p = large prime

    real_numbers = []
    m = (p - 1) / 2
    for x in weights:
        if 0 <= x and x < m:
            real_numbers.append(x / q)
        else: # (p-1)/2 <= x < p
            real_numbers.append((x - p) / q)
    return real_numbers


# just for testing
# if __name__ == "__main__":

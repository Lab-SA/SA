# Lab-SA HeteroSAg for Federated Learning
import random
import SecureProtocol as sp
from BasicSA import reconstruct, reconstructPu, reconstructPvu, generatingOutput
from learning.utils import add_to_weights
import learning.federated_main as fl
import learning.models_helper as mhelper

default_r1 = -1
default_r2 = 1
default_quantization_levels = [20, 30, 60, 80, 100]

def quantization(x, _Kg, r1, r2):
    # x = local model value of user i
    # Kg = number of quantization levels
    # [r1, r2] = quantization range

    # delK = quantization interval
    Kg = default_quantization_levels[_Kg]
    delK = (r2 - r1) / (Kg - 1)

    # T = discrete value from quantization range point list
    T = [r1 + l * delK for l in range(0, Kg)]

    for l in range(0, len(T)-1):
        if T[l] <= x < T[l + 1]:
            p = (x - T[l]) / (T[l + 1] - T[l])
            prob_list = [p, 1-p]
            return random.choices([l+1, l], prob_list, k=1)[0]
    if T[Kg-1] == x:
        return Kg-1 # r2 choose Kg-1 with 100% probability
    
    return -1 # fail (only when x < r1 or x > r2)

def quantization_weights(weights, _Kg, r1, r2):
    # x = local weigths in 1-dim
    # Kg = number of quantization levels
    # [r1, r2] = quantization range

    # delK = quantization interval
    Kg = default_quantization_levels[_Kg]
    delK = (r2 - r1) / (Kg - 1)

    # T = discrete value from quantization range point list
    T = [r1 + l * delK for l in range(0, Kg)]

    quantized_weights = []
    for x in weights:
        if x < r1: x = r1
        elif x > r2: x = r2
        quantized_x = 0

        for l in range(0, len(T)-1):
            if T[l] <= x < T[l + 1]:
                p = (x - T[l]) / (T[l + 1] - T[l])
                prob_list = [p, 1-p]
                quantized_x = random.choices([l+1, l], prob_list, k=1)[0]
        if T[Kg-1] == x:
            quantized_x = Kg-1 # r2 choose Kg-1 with 100% probability
        quantized_weights.append(quantized_x)

    return quantized_weights

def dequantization_weights(weights, _Kg, r1, r2, u):
    # x = local weigths in 1-dim
    # Kg = number of quantization levels
    # [r1, r2] = quantization range
    # u = number of surviving users of same segment (= |U|)

    # delK = quantization interval
    Kg = default_quantization_levels[_Kg]
    delK = (r2 - r1) / (Kg - 1)

    # mapping to the corresponding values in discrete set of real numbers: |U|r1 ~ |U|r2
    real_numbers = [(u * r1) + (l * delK) for l in range(0, u * (Kg-1) + 1)]
    # print(f'real_numbers: {real_numbers}')
    return list(map(lambda x: real_numbers[x], weights))

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

def getSegmentInfoFromB(B, G, perGroup):
    """ get segment information from SS Matrix B
    Args:        
        B (GxG matrix): SS matirx
        G (int): # of group
        perGroup (int): users num of one group
    Returns:
        dict: segment info (key: segment index, value: dict (key: quantization level, value: index list))
    """
    segment_info = {i: {j: [] for j in range(G)} for i in range(G)} # i: segment level, j: quantization level
    for l, segment in enumerate(B): # for each segment
        for i, value in enumerate(segment): # for each group            
            for idx in range(perGroup): # for each user
                segment_info[l][value].append(i * perGroup + idx)
    return segment_info

def generateMaskedInputOfSegments(index, bu, xu, s_sk, B, G, group, perGroup, weights_interval, euv_list, s_pk_dic, p, R):
    """ generate masked input of segments and do quantization
    Args:
        index (int): user's index
        bu (int): user's private mask
        xu: user's weight (private value)
        s_sk: user's public key of s
        B (GxG matrix): SS matirx
        G (int): # of group
        group (int): user's group
        perGroup (int): users num of one group
        weights_interval (list): interval index of weights (for each segment)
        euv_list (list): user's evu_list
        s_pk_dic (dict): other's public key s dictionary (key: index, value: s_pk)
        p (int): prime
        R (int): field
    Returns:
        dict: yu of segments (key: segment index, value: dict (key: quantization level, value: yu))
    """

    euv_dic = {}
    for u, v, euv in euv_list: # euv_list = [ (u, v, euv), (u, v, euv) ... ]
        if u == v:
            continue
        euv_dic[v] = euv

    # compute pu first
    random.seed(bu)
    pu = random.randrange(1, R) # 1~R
    print(f'pu: {pu}')

    # compute p_uv
    weights_info, flatten_xu = mhelper.flatten_tensor(xu)
    segment_xu = list(map(lambda i: flatten_xu[weights_interval[i]:weights_interval[i+1]], range(0, G)))
    segment_yu = {i: {} for i in range(G)}
    for l, segment in enumerate(B): # for each segment

        # find group of same level
        q = segment[group]
        p_uv_list = []
        for i, value in enumerate(segment):
            if q == value: # in same quantization level
                for idx in range(perGroup):
                    group_idx = i * perGroup + idx
                    if group_idx == index: continue

                    # compute p_uv
                    s_uv = sp.agree(s_sk, s_pk_dic[group_idx], p)
                    random.seed(s_uv)

                    p_uv = random.randrange(1, R) # 1~R
                    if index < group_idx:
                        p_uv = -p_uv
                    p_uv_list.append(p_uv)

        print(f'puv list[{l}]: {p_uv_list}')

        # quantization weights
        quantized_xu = quantization_weights(segment_xu[l], q, default_r1, default_r2)

        # generate yu (masked xu) of segment l
        mask = pu + sum(p_uv_list)
        segment_yu[l][q] = list(map(lambda x : x + mask, quantized_xu))
    
    return segment_yu


def reconstructSSKofSegments(B, G, perGroup, s_sk_shares_dic):
    """ reconstruct s_sk per segment with same group
    Args:
        B (GxG matrix): SS matirx
        G (int): # of group
        perGroup (int): users num of one group
        s_sk_shares_dic (dict): shares of s_sk for drop-out users (key: index, value: list of shares)
    Returns:
        dict: s_sk of drop-out users (key: segment index, value: dict (key: quantization level, value: reconstructed_s_sk))
    """
    # reconstruct s_sk using shares
    s_sk_dic = {i: {j: {} for j in range(G)} for i in range(G)} # i: segment level, j: quantizatoin level

    for index, ssk_shares in s_sk_shares_dic.items(): # first, reconstruct ssk_u <- ssk_u,v
        reconstructed_sk = reconstruct(ssk_shares)
        group = int(index / perGroup)
        for l, segment in enumerate(B):
            q = segment[group]
            s_sk_dic[l][q][index] = reconstructed_sk

    return s_sk_dic

def unmasking(segment_info, G, segment_yu, surviving_users, users_keys, s_sk_dic, bu_shares_dic, R):
    """ generate masked input of segments and do dequantization
    Args:
        segment_info (dict): segment info (key: segment index, value: dict (key: quantization level, value: index list))
        G (int): # of group
        segment_yu (dict): yu of segments (key: segment level, value: dict(key: quantization level, value: segment list of yu))
        surviving_users (list): surviving users index list
        users_keys (dict): public keys of users
        s_sk_dic (dict): s_sk of drop-out users (key: segment index, value: dict (key: quantization level, value: reconstructed_s_sk))
        bu_shares_dic (dict): shares for bu (key: index, value: list of shares)
        R (int): field
    Returns:
        dict: xu(real-value) of segments (key: segment index, value: dict (key: quantization level, value: encoded xu))
    """

    # segment_xu = {i: {j: [] for j in range(G)} for i in range(G)} # i: segment level, j: quantization level
    segment_xu = {i: [] for i in range(G)} # i: segment level
    for l, value in segment_info.items(): 
        for q, index_list in value.items(): # q: quantization level
            if len(segment_yu[l][q]) == 0: continue
            
            surviving_num = 0 # number of surviving users of this segment

            # reconstruct per segment with same quantizer
            sum_pu = 0
            sum_pvu = 0
            for index in index_list:
                if index in surviving_users: # surviving user
                    # reconpute p_u
                    sum_pu = sum_pu + reconstructPu(bu_shares_dic[index], R)
                    # recompute p_vu
                    for v, s_sk in s_sk_dic[l][q].items():
                        sum_pvu = sum_pvu + reconstructPvu(v, index, s_sk, users_keys[index]["s_pk"], R)
                    
                    surviving_num = surviving_num + 1
            print(f'sum pu / (recontructed) sum_pvu : {sum_pu} / {sum_pvu}')
            mask = sum_pvu - sum_pu

            #segment_xu[l][q] = sum(segment_yu[l][q]) + mask
            sum_segment_yu = list(sum(x) for x in zip(*segment_yu[l][q])) # sum

            # segment_xu[l][q] = list(map(lambda x : x + mask, sum_segment_yu))  # remove mask
            raw_segment_xu = list(map(lambda x : x + mask, sum_segment_yu)) # remove mask
            # print(f'q level: {q} / surviving_num: {surviving_num} / min: {min(raw_segment_xu)} / max: {max(raw_segment_xu)}')

            # dequantization: to real numbers
            segment_xu[l].append(dequantization_weights(raw_segment_xu, q, default_r1, default_r2, surviving_num))

    return segment_xu

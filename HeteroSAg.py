# Lab-SA HeteroSAg for Federated Learning
import random
import SecureProtocol as sp
from learning.utils import add_to_weights
import learning.federated_main as fl

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

def generateMaskedInputOfSegments(index, bu, xu, s_sk, B, G, group, perGroup, euv_list, s_pk_dic, p, R):
    """ generate masked input of segments
    Args:
        index (int): user's index
        bu (int): user's private mask
        xu: user's weight (private value)
        s_sk: user's public key of s
        B (GxG matrix): SS matirx
        G (int): # of group
        group (int): user's group
        perGroup (int): users num of one group
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
    segment_yu = {i: {} for i in range(G)}
    for l, segment in enumerate(B): # for each segment

        # find group of same segment
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
        # generate yu (masked xu) of segment l
        mask = pu + sum(p_uv_list)
        # yu = add_to_weights(xu, mask)
        # segment_yu[l] = fl.weights_to_dic_of_list(yu)
        segment_yu[l][q] = xu + mask
    
    return segment_yu

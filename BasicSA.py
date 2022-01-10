# Lab-SA Basic SA for Federated Learning
import random
import SecureProtocol as sp

# Generate two key pairs
def generateKeyPairs():
    (c_pk, c_sk) = sp.generate() #temp
    (s_pk, s_sk) = sp.generate() #temp
    return ((c_pk, c_sk), (s_pk, s_sk))

# Generate secret-shares of s_sk and bu and encrypt those data
def generateSharesOfMask(t, u, s_sk, c_sk, u1_list):
    bu = random.randrange(1, 100) # 1~99 #temp
    s_sk_shares_list = sp.share(s_sk, t, len(u1_list)) #temp
    bu_shares_list = sp.share(bu, t, len(u1_list)) #temp
    u1_s_pk_dic = {}
    euv_dic = {}
    for i, list in enumerate(u1_list): # list = (v, c_pk, s_pk)
        v = list[0]
        c_pk = list[1]
        s_pk = list[2]
        u1_s_pk_dic[v] = s_pk
        euv = sp.encrypt((c_sk, c_pk), (u, v, s_sk_shares_list[i], bu_shares_list[i])) #temp
        euv_dic[v] = euv
    return (u1_s_pk_dic, euv_dic)

def generateMaskedInput(u, bu, xu, s_sk, s_pk_dic, euv_dic):
    # compute p_uv
    p_uv_list = []
    for v, euv in euv_dic.items(): # euv_dic = { v: euv }
        if u == v:
            continue
        s_uv = sp.agree(s_sk, s_pk_dic[v])
        random.seed(s_uv)
        p_uv = random.randrange(1, 100) # 1~99 #temp
        if u < v:
            p_uv = -p_uv
        p_uv_list.append(p_uv)

    #compute bu
    random.seed(bu)
    pu = random.randrange(1, 100) # 1~99 #temp

    # make masked xu
    yu = xu + pu + sum(p_uv_list)
    return yu

# just for testing
# if __name__ == "__main__":

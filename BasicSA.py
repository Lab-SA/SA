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
    s_pk_dic = {}
    c_pk_dic = {}
    euv_dic = {}
    for i, list in enumerate(u1_list): # list = (v, c_pk, s_pk)
        v = list[0]
        c_pk = list[1]
        s_pk = list[2]
        c_pk_dic[v] = c_pk
        s_pk_dic[v] = s_pk
        euv = sp.encrypt((c_sk, c_pk), (u, v, s_sk_shares_list[i], bu_shares_list[i])) #temp
        euv_dic[v] = euv
    return (euv_dic, c_pk_dic, s_pk_dic)

def generateMaskedInput(u, bu, xu, s_sk, euv_dic, s_pk_dic):
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

def unmasking(c_sk, evu_dic, c_pk_dic, users_u2, users_u3):
    s_sk_shares_dic = {}
    bu_shares_dic = {}
    for _v in users_u2:
        try:
            [v, u, s_sk_shares, bu_shares] = sp.decrypt((c_sk, c_pk_dic[_v]), evu_dic[_v])
            try:
                users_u3.remove(v) # v is in U3
                bu_shares_dic[_v] = bu_shares
            except ValueError: # v is in U2\U3
                s_sk_shares_dic[_v] = s_sk_shares
        except:
            raise Exception('Decryption failed.')
    return (s_sk_shares_dic, bu_shares_dic)

def reconstructPuv(u, v, s_sk_shares_list): # shares list of user (u, v): s^SK_(u,v)
    s_sk = sp.reconstruct(s_sk_shares_list)
    random.seed(s_sk)
    p_uv = random.randrange(1, 100) #temp
    if u < v:
        p_uv = -p_uv
    return p_uv

def reconstructPu(bu_shares_list): # list of user u
    bu = sp.reconstruct(bu_shares_list)
    random.seed(bu)
    pu = random.randrange(1, 100) #temp
    return pu

def generatingOutput(yu_list, pu_list, puv_list):
    # yu, pu: user u in U3
    # puv: user u in U3, user v in U2\U3
    sum_xu = sum(yu_list) - sum(pu_list) + sum(puv_list)
    return sum_xu

# just for testing
# if __name__ == "__main__":

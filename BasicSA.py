# Lab-SA Basic SA for Federated Learning
import random
import SecureProtocol as sp

# Generate two key pairs
def generateKeyPairs():
    (c_pk, c_sk) = sp.generate() #temp
    (s_pk, s_sk) = sp.generate() #temp
    return ((c_pk, c_sk), (s_pk, s_sk))

# Generate secret-shares of s_sk and bu and encrypt those data
# users [list]: all users of the current round
def generateSharesOfMask(t, u, s_sk, c_sk, users):
    bu = random.randrange(1, 100) # 1~99 #temp
    s_sk_shares_list = sp.share(s_sk, t, len(users)) #temp
    bu_shares_list = sp.share(bu, t, len(users)) #temp
    s_pk_dic = {}
    c_pk_dic = {}
    euv_list = []
    for i, list in enumerate(users): # list = (v, c_pk, s_pk)
        v = list[0]
        c_pk = list[1]
        s_pk = list[2]
        c_pk_dic[v] = c_pk
        s_pk_dic[v] = s_pk
        euv = sp.encrypt((c_sk, c_pk), (u, v, s_sk_shares_list[i], bu_shares_list[i])) #temp
        euv_list.append((u, v, euv))
    return (euv_list, c_pk_dic, s_pk_dic)

def generateMaskedInput(u, bu, xu, s_sk, euv_list, s_pk_dic):
    # compute p_uv
    p_uv_list = []
    for u, v, euv in euv_list: # euv_list = [ (u, v, euv), (u, v, euv) ... ]
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

# users_previous [list]: users who were alive in the previous round
# users_last [list]: users who were alive in the recent round
def unmasking(u, c_sk, euv_list, c_pk_dic, users_previous, users_last):
    s_sk_shares_dic = {}
    bu_shares_dic = {}
    for v in users_previous:
        try:
            idx = euv = 0
            for i, (u, _v, euv) in enumerate(euv_list):
                if _v == v:
                    idx = i
                    euv = euv
                    break
            euv_list.pop(idx)
            [_v, _u, s_sk_shares, bu_shares] = sp.decrypt((c_sk, c_pk_dic[v]), euv)
            if not(u == _u and u == _v):
                raise Exception('Something went wrong during reconstruction.')
            try:
                users_last.remove(v) # v is in U3
                bu_shares_dic[v] = bu_shares
            except ValueError: # v is in U2\U3
                s_sk_shares_dic[v] = s_sk_shares
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

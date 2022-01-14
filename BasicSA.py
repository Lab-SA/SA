# Lab-SA Basic SA for Federated Learning
import random
import math
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

def stochastic_q(w_i): # w_i = local model of user i
    vx_i = []
    q = random.randint(1, 100)  # quantization level
    p = random.randint(1, 100)  # modulo p
    for x in w_i:
        vx_i.append(pi_x(q * qq_x(x, q), p))
    return vx_i

def qq_x(x, q):
    prob = q * x - math.floor(q * x)
    if prob < 0.5:
        return math.floor(q * x) / q
    else:
        return (math.floor(q * x) + 1) / q

def pi_x(x, p):
    """pi_x(x) is to represent a negative integer in the finite field
    by using two’s complement representation"""
    # % mod 연산으로 대체가 가능한 부분인가...?
    if x < 0:
        return p + x
    else:
        return x

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

def generateQuantizers_heteroQ(G):
    Q = []  # generate G quantizers randomly
    for i in range(G):
        Q.append(random.randint(1, 100))
    return Q

# set quantization level q
def setQuantizer(G, mode, l, g, B):
    # G = the number of groups
    # mode = homo quantization(0) or hetero quantization(1)
    # l = segment index
    # g = group index

    if mode == 0:  # homo quantization
        q = random.randint(1, 100)  # quantization level
        return q
    elif mode == 1:  # hetero quantization
        Q = generateQuantizers_heteroQ(G) # a set of quantization level
        q = Q[B[l][g]]
        return q
    else:
        print("wrong input")
        return 0

def homoQ(x, q, G):
    """x = local model value of user i
    q = setQuantizer(G, mode, l, g, B) = quantization level
    => can do both homo quantization and hetero quantization
    G = the number of groups"""

    r1, r2 = 0, 100  # quantization range
    delK = (r2 - r1) / (q - 1)  # quantization interval
    T = []  # discrete value from quantization range
    for l in range(0, G):
        T.append(r1 + l * delK)

    for l in range(0, G - 1):
        if T[l] <= x < T[l + 1]:
            prob = (x - T[l]) / (T[l + 1] - T[l])
            if prob < 0.5:
                return T[l]
            else:
                return T[l+1]

# just for testing
# if __name__ == "__main__":

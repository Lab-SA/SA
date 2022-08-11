import random
from ecies.utils import generate_key
from ecies import encrypt, decrypt
from sympy import Q

def generateECCKey():
    """ generate ECC key pair (secp256k1)
    Args:
    Returns:
        bytes: secret key
        bytes: public key
    """
    secp_k = generate_key()
    sk_bytes = secp_k.secret
    pk_bytes = secp_k.public_key.format(True)
    # encrypt(pk_bytes, plain)
    # decrypt(sk_bytes, cipher)
    return sk_bytes, pk_bytes

def generateRandomNonce(c, g, p):
    """ generate random nonce for clusters
    Args:
        c (int): number of clusters
        g (int): secure parameter
        p (int): big prime number
    Returns:
        list: list of random nonces
        list: list of Ri
    """
    list_ri = [random.randrange(1, p) for i in range(c)] # for modular p
    list_Ri = [(g ** ri) % p for ri in list_ri]
    return list_ri, list_Ri

def generateMasks(idx, n, ri, pub_keys, g, p):
    """ generate masks
    Args:
        idx (int): user's index (idx < n)
        n (int): number of nodes in a cluster
        ri (int): random nonce ri
        pub_keys (dict): public keys
        g (int): secure parameter
        p (int): big prime number
    Returns:
        dict: random masks (mjk)
        dict: encrypted masks (of mjk)
        dict: public masks (Mjk)
    """

    while True: # repeat until all masks are valid
        mask = {}
        encrypted_mask = {}
        public_mask = {}
        sum_mask = 0
        flag = False

        for k in range(n):
            if k == idx: continue
            if (idx == n - 1 and k == n - 2) or k == n - 1:
                # last mask (ri - sum_mask)
                m = mask[k] = ri - sum_mask # allow negative value
                if m != 0: # mask is not allowed to be 0
                    flag = True
            else:
                m = mask[k] = random.randrange(1, p) # positive integer # for modular p
                sum_mask = (sum_mask + m) % p

            encrypted_mask[k] = encrypt(pub_keys[k], bytes(str(m), 'ascii')).hex()
            if m > 0:
                public_mask[k] = (g ** m) % p
            else:
                public_mask[k] = (g ** (p - 1 + m)) % p
        
        if flag: break # repeat cause last mask is 0

    return mask, encrypted_mask, public_mask


def verifyMasks(idx, ri, n, encrypted_mask, public_mask, sk, g, p):
    """ verify masks
    Args:
        idx (int): user's index (idx < n)
        ri (int): random nonce ri
        n (int): number of nodes in a cluster
        encrypted_mask (dict): encrypted masks (of mkj)
        public_mask (2-dict): public masks in a cluster (Mnn)
        sk (bytes): secret key
        g (int): secure parameter
        p (int): big prime number
    Returns:
        dict: decrypted masks
    """

    if n-1 != len(encrypted_mask) or n != len(public_mask):
        raise Exception('Mask is Dropped during the Communication.')

    # verify Mkj = g^mkj mod p
    mask = {}
    for k, mkj in encrypted_mask.items():
        mask[k] = m = int(bytes.decode(decrypt(sk, bytes.fromhex(mkj)), 'ascii'))
        if m < 0:
            m = p - 1 + m
        if public_mask[k][str(idx)] != (g ** m) % p:
            print('Mask is Invalid. 1')
            return {}
            #raise Exception('Mask is Invalid. 1')
    
    Ri = (g ** ri) % p
    # verify g^ri = **Mnn mod p
    for k, l in public_mask.items():
        if k == idx: continue
        mul_Mkn = 1
        for Mkn in l.values():
            mul_Mkn = (mul_Mkn * Mkn) % p
        if Ri != mul_Mkn:
            print('Mask is Invalid. 2')
            return mask # temp
            return {}
            #raise Exception('Mask is Invalid. 2')
    
    return mask


def generateSecureWeight(weight, ri, masks, p):
    """ generate secure weight Sj
    Args:
        weight (list): 1-d weight list
        ri (int): random nonce ri
        mask (dict): random masks (mkj)
        p (int): big prime number
    Returns:
        dict: secure weight Sj
    """
    sum_mask = ri - (sum(masks.values()) % p)
    return [w + sum_mask for w in weight]


def computeReconstructionValue(drop_out, my_masks, masks):
    """ compute reconstruction value RSj
    Args:
        drop_out (list): index list of drop-out users
        my_masks (dict): random masks by this user (mjk)
        mask (dict): random masks by other users (mkj)
    Returns:
        int: reconstruction value RSj
    """
    RS = 0
    for k in drop_out:
        RS = RS + masks[k] - my_masks[k]
    return RS


def computeIntermediateSum(S_dic, n, p, RS_dic = {}):
    """ compute intermediate sum ISi
    Args:
        S_dic (dict): dict of Sj
        n (int): number of nodes in a cluster
        p (int): big prime number
        RS_dic (dict): for drop-out users
    Returns:
        dict: random masks (mkj)
    """
    # check drop-out users
    drop_out = []
    for j in range(n):
        if j not in S_dic:
            drop_out.append(j)
    
    if drop_out == []:  # no drop-out user
        return False, list(sum(x) % p for x in zip(*list(S_dic.values())))
    elif RS_dic != {}:  # remove masks of drop-out users
        removed_masks = sum(RS_dic.values())
        return False, list((sum(x)+removed_masks) % p for x in zip(*list(S_dic.values())))
    else:               # need RS
        return True, drop_out


def clustering(G, a, b, k, rf, cf, U, t):
    # node clustering
    C = {i: [] for i in range(1, k+1)} # clusters
    Uij = {i: {j: [] for j in range(1, b+1)} for i in range(1, a+1)}
    for user, value in U.items():
        i, j, PS = value
        Uij[i][j].append((user, PS))

    D = 0
    while rf + D <= a or cf + D <= b:
        r0 = max(rf-D, 1)
        c0 = max(cf-D, 1)
        r1 = min(rf+D, a)
        c1 = min(cf+D, b)
        for r in range(r0, r1+1):
            for c in range(c0, c1+1):
                if abs(r-rf) == D or abs(c-cf) == D:
                    for user, PS in Uij[r][c]:
                        C[PS].append(user) # PS is divided into k levels
        D += 1

    # merge clusters for satisfying constraint t
    while k > 1:
        if len(C[k]) < t:
            l = t - len(C[k])
            if len(C[k-1])-l >= t:
                move = []
                for _ in range(l):
                    move.append(C[k-1].pop())
                move.reverse()
                C[k] = C[k] + move
            else:
                C[k-1] = C[k-1] + C[k]
                del C[k]
        k -= 1
    if len(C[k]) < t: # k = 0
        C[k+1] = C[k+1] + C[k]
        del C[k]

    return C


if __name__ == "__main__":
    # example
    p = 7
    g = 3
    c = 3
    n = 3
    a = generateRandomNonce(c, g, p)
    ri = a[0][0]
    
    sk0, pk0 = generateECCKey()
    sk1, pk1 = generateECCKey()
    sk2, pk2 = generateECCKey()
    pub_keys = {0: pk0, 1: pk1, 2: pk2}

    a0, b0, c0 = generateMasks(0, n, ri, pub_keys, g, p)
    a1, b1, c1 = generateMasks(1, n, ri, pub_keys, g, p)
    a2, b2, c2 = generateMasks(2, n, ri, pub_keys, g, p)
    
    e1 = {0: b0[1], 2: b2[1]}
    p1 = {0: c0, 1: c1, 2: c2}
    verifyMasks(1, ri, n, e1, p1, sk1, g, p)


    # IntermediateSum example
    w0 = [1,2,3] # weights
    w1 = [2,3,4]
    w2 = [3,4,5]
    m0 = {1: a1[0], 2: a2[0]} # masks for user 0
    m1 = {0: a0[1], 2: a2[1]}
    m2 = {0: a0[2], 1: a1[2]} # drop-out

    s0 = generateSecureWeight(w0, ri, m0, p)
    s1 = generateSecureWeight(w1, ri, m1, p)
    s2 = generateSecureWeight(w2, ri, m2, p) # drop-out

    # case 1: no drop-out
    print(computeIntermediateSum({0: s0, 1: s1, 2: s2}, n, p))

    # case 2: 1 drop-out user
    isDropout, result = computeIntermediateSum({0: s0, 1: s1}, n, p)
    if isDropout:
        # request Reconstruction Value RSj - R0, R1
        RS_dic = {}
        RS_dic[0] = computeReconstructionValue(result, a0, m0)
        RS_dic[1] = computeReconstructionValue(result, a1, m1)

        # after request RSj
        print(computeIntermediateSum({0: s0, 1: s1}, n, p, RS_dic))


    # example: node clustring
    n = 12
    a = 1
    b = 3
    k = 3
    t = 4
    U = {}
    for i in range(n):
        U[i] = [random.randrange(1, a+1), random.randrange(1, b+1), random.randrange(1, k+1)]
    print(clustering({}, a, b, k, 1, 2, U, t))

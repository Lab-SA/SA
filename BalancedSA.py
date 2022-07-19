import random

def generateRandomNonce(c, g, p, R):
    """ generate random nonce for clusters
    Args:
        c (int): number of clusters
        g (int): secure parameter
        p (int): big prime number
        R (int): random range
    Returns:
        list: list of random nonces
        list: list of Ri
    """
    list_ri = [random.randrange(1, R) for i in range(c)]
    list_Ri = [(g ** ri) % p for ri in list_ri]
    return list_ri, list_Ri

def generateMasks(idx, n, ri, pub_keys, g, p, R):
    """ generate masks
    Args:
        idx (int): user's index (idx < n)
        n (int): number of nodes in a cluster
        ri (int): random nonce ri
        pub_keys (dict): public keys
        g (int): secure parameter
        p (int): big prime number
        R (int): random range
    Returns:
        dict: random masks (mjk)
        dict: encrypted masks (of mjk)
        dict: public masks (Mjk)
    """
    mask = {}
    encrypted_mask = {}
    public_mask = {}
    sum_mask = 0

    for k in range(n):
        if k == idx: continue
        if (idx == n - 1 and k == n - 2) or k == n - 1:
            # last mask (ri - sum_mask)
            m = mask[k] = (ri - sum_mask) % p
        else:
            m = mask[k] = random.randrange(1, R) % p
            sum_mask = sum_mask + m
        
        # encrypted_mask[k] = encrypt(pub_keys[k], m)
        encrypted_mask[k] = m
        public_mask[k] = (g ** m) % p
    
    return mask, encrypted_mask, public_mask


def verifyMasks(idx, ri, n, encrypted_mask, public_mask, pub_keys, g, p):
    """ verify masks
    Args:
        idx (int): user's index (idx < n)
        ri (int): random nonce ri
        n (int): number of nodes in a cluster
        encrypted_mask (dict): encrypted masks (of mkj)
        public_mask (2-dict): public masks in a cluster (Mnn)
        pub_keys (dict): public keys
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
        # m = decrypt(pub_keys[k], mkj)
        m = mask[k] = mkj
        if public_mask[k][idx] != (g ** mkj) % p:
            print('Mask is Invalid. 1')
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
            #raise Exception('Mask is Invalid. 2')
    
    return mask


def generateSecureWeight(weight, ri, masks):
    """ generate secure weight Sj
    Args:
        weight (list): 1-d weight list
        ri (int): random nonce ri
        mask (dict): random masks (mkj)
    Returns:
        dict: secure weight Sj
    """
    sum_mask = ri - sum(masks.values())
    return [w + sum_mask for w in weight]


def computeReconstructionValue(drop_out, my_masks, masks):
    """ compute reconstruction value RSj
    Args:
        drop_out (list): index list of drop-out users
        my_masks (dict): random masks by this user (mjk)
        mask (dict): random masks (mkj)
    Returns:
        int: reconstruction value RSj
    """
    RS = 0
    for k in drop_out:
        RS = RS + masks[k] - my_masks[k]
    return RS


def computeIntermediateSum(S_dic, n, RS_dic = {}):
    """ compute intermediate sum ISi
    Args:
        S_dic (dict): dict of Sj
        n (int): number of nodes in a cluster
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
        return False, list(sum(x) for x in zip(*list(S_dic.values())))
    elif RS_dic != {}:  # remove masks of drop-out users
        removed_masks = sum(RS_dic.values())
        return False, list(sum(x)+removed_masks for x in zip(*list(S_dic.values())))
    else:               # need RS
        return True, drop_out


if __name__ == "__main__":
    # example
    p = 7
    g = 3
    c = 3
    R = 10
    n = 3
    a = generateRandomNonce(c, g, p, R)
    ri = a[0][0]
    
    a0, b0, c0 = generateMasks(0, n, ri, {}, g, p, R)
    a1, b1, c1 = generateMasks(1, n, ri, {}, g, p, R)
    a2, b2, c2 = generateMasks(2, n, ri, {}, g, p, R)
    
    e1 = {0: b0[1], 2: b2[1]}
    p1 = {0: c0, 1: c1, 2: c2}
    verifyMasks(1, ri, n, e1, p1, {}, g, p)


    # IntermediateSum example
    w0 = [1,2,3] # weights
    w1 = [2,3,4]
    w2 = [3,4,5]
    m0 = {1: a1[0], 2: a2[0]} # masks for user 0
    m1 = {0: a0[1], 2: a2[1]}
    m2 = {0: a0[2], 1: a1[2]} # drop-out

    s0 = generateSecureWeight(w0, ri, m0)
    s1 = generateSecureWeight(w1, ri, m1)
    s2 = generateSecureWeight(w2, ri, m2) # drop-out

    # case 1: no drop-out
    print(computeIntermediateSum({0: s0, 1: s1, 2: s2}, n))

    # case 2: 1 drop-out user
    isDropout, result = computeIntermediateSum({0: s0, 1: s1}, n)
    if isDropout:
        # request Reconstruction Value RSj - R0, R1
        RS_dic = {}
        RS_dic[0] = computeReconstructionValue(result, a0, m0)
        RS_dic[1] = computeReconstructionValue(result, a1, m1)

        # after request RSj
        print(computeIntermediateSum({0: s0, 1: s1}, n, RS_dic))
        
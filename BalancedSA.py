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

def generateMasks(idx, n, Ri, pub_keys, g, p, R):
    """ generate masks
    Args:
        idx (int): user's index (idx < n)
        n (int): number of nodes in a cluster
        Ri (int): (g ^ random nonce ri) mod p
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
            # last mask (Ri - sum_mask)
            m = mask[k] = Ri - sum_mask
        else:
            m = mask[k] = random.randrange(1, R)
            sum_mask = sum_mask + m
        
        # encrypted_mask[k] = encrypt(pub_keys[k], m)
        encrypted_mask[k] = m
        public_mask[k] = (g ** m) % p
    
    return mask, encrypted_mask, public_mask

def verifyMasks(idx, Ri, n, encrypted_mask, public_mask, pub_keys, g, p):
    """ verify masks
    Args:
        idx (int): user's index (idx < n)
        Ri (int): (g ^ random nonce ri) mod p
        n (int): number of nodes in a cluster
        encrypted_mask (dict): encrypted masks (of mkj)
        public_mask (2-dict): public masks in a cluster (Mnn)
        pub_keys (dict): public keys
        g (int): secure parameter
        p (int): big prime number
    Returns:
        dict: dcrypted masks
    """

    if n-1 != len(encrypted_mask) or n != len(public_mask):
        raise Exception('Mask is Dropped during the Communication.')

    # verify Mkj = g^mkj mod p
    mask = {}
    for k, mkj in encrypted_mask.items():
        # m = decrypt(pub_keys[k], mkj)
        m = mask[k] = mkj
        if public_mask[k][idx] != (g ** mkj) % p:
            raise Exception('Mask is Invalid. 1')
    
    # verify g^ri (Ri) = **Mnn mod p
    for k, l in public_mask.items():
        if k == idx: continue
        mul_Mkn = 1
        for Mkn in l.values():
            mul_Mkn = (mul_Mkn * Mkn) % p
        if (g ** Ri) % p != mul_Mkn:
            raise Exception('Mask is Invalid. 2')
    
    return mask


def generateSecureWeight(weight, Ri, masks):
    """ generate secure weight Sj
    Args:
        weight (list): 1-d weight list
        Ri (int): (g ^ random nonce ri) mod p
        mask (dict): random masks (mkj)
    Returns:
        dict: secure weight Sj
    """
    sum_mask = Ri - sum(masks.values())
    return [w + sum_mask for w in weight]


def computeReconstructionValue(drop_out, my_masks, masks):
    """ compute reconstruction value Rj
    Args:
        drop_out (list): index list of drop-out users
        my_masks (dict): random masks by this user (mjk)
        mask (dict): random masks (mkj)
    Returns:
        int: reconstruction value Rj
    """
    Rj = 0
    for k in drop_out:
        Rj = Rj + masks[k] - my_masks[k]
    return Rj


def computeIntermediateSum(S_dic, n, R_dic = {}):
    """ compute intermediate sum ISi
    Args:
        S_dic (dict): dict of Sj
        n (int): number of nodes in a cluster
        R_dic (dict): for drop-out users
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
    elif R_dic != {}:  # remove masks of drop-out users
        removed_masks = sum(R_dic.values())
        return False, list(sum(x)+removed_masks for x in zip(*list(S_dic.values())))
    else:               # need Rj
        return True, drop_out


if __name__ == "__main__":
    # example
    p = 7
    g = 3
    c = 3
    R = 10
    n = 3
    a = generateRandomNonce(c, g, p, R)
    Ri = a[1][0]
    
    a0, b0, c0 = generateMasks(0, n, Ri, {}, g, p, R)
    a1, b1, c1 = generateMasks(1, n, Ri, {}, g, p, R)
    a2, b2, c2 = generateMasks(2, n, Ri, {}, g, p, R)
    
    e1 = {0: b0[1], 2: b2[1]}
    p1 = {0: c0, 1: c1, 2: c2}
    #print(verifyMasks(1, Ri, n, e1, p1, {}, g, p))


    # IntermediateSum example
    w0 = [1,2,3] # weights
    w1 = [2,3,4]
    w2 = [3,4,5]
    m0 = {1: a1[0], 2: a2[0]} # masks for user 0
    m1 = {0: a0[1], 2: a2[1]}
    m2 = {0: a0[2], 1: a1[2]} # drop-out

    s0 = generateSecureWeight(w0, Ri, m0)
    s1 = generateSecureWeight(w1, Ri, m1)
    s2 = generateSecureWeight(w2, Ri, m2) # drop-out

    # case 1: no drop-out
    print(computeIntermediateSum({0: s0, 1: s1, 2: s2}, n))

    # case 2: 1 drop-out user
    isDropout, result = computeIntermediateSum({0: s0, 1: s1}, n)
    if isDropout:
        # request Reconstruction Value Rj - R0, R1
        R_dic = {}
        R_dic[0] = computeReconstructionValue(result, a0, m0)
        R_dic[1] = computeReconstructionValue(result, a1, m1)

        # after request Rj
        print(computeIntermediateSum({0: s0, 1: s1}, n, R_dic))
        
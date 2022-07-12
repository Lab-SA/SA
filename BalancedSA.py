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
    print(verifyMasks(1, Ri, n, e1, p1, {}, g, p))

import random
from ecies.utils import generate_key
from ecies import encrypt, decrypt

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

def generateRandomNonce(clusters, g, p):
    """ generate random nonce for clusters
    Args:
        clusters (list): index of clusters
        g (int): secure parameter
        p (int): big prime number
    Returns:
        list: list of random nonces
        list: list of Ri
    """
    list_ri = {c: random.randrange(1, p) for c in clusters} # for modular p
    list_Ri = {c: (g ** ri) % p for c, ri in list_ri.items()}
    return list_ri, list_Ri

def generateMasks(idx, cluster_indexes, ri, pub_keys, g, p):
    """ generate masks
    Args:
        idx (int): user's index (idx < n)
        cluster_indexes (list): index of nodes in a cluster (without my index)
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
        flag = False

        n = len(cluster_indexes)
        for i, k in enumerate(cluster_indexes):
            if i == n - 1: # lask mask
                # last mask (ri - sum_mask)
                m = mask[k] = ri - sum(mask.values()) # allow negative value
                if m != 0: # mask is not allowed to be 0
                    flag = True
            else:
                m = mask[k] = random.randrange(1, p) # positive integer # for modular p

            encrypted_mask[k] = encrypt(pub_keys[k], bytes(str(m), 'ascii')).hex()
            if m > 0:
                public_mask[k] = (g ** m) % p
            else:
                public_mask[k] = (g ** (m % (p - 1))) % p

        if flag: break # repeat cause last mask is 0

    return mask, encrypted_mask, public_mask


def verifyMasks(idx, ri, encrypted_mask, public_mask, sk, g, p):
    """ verify masks
    Args:
        idx (int): user's index (idx < n)
        ri (int): random nonce ri
        encrypted_mask (dict): encrypted masks (of mkj)
        public_mask (2-dict): public masks in a cluster (Mnn)
        sk (bytes): secret key
        g (int): secure parameter
        p (int): big prime number
    Returns:
        dict: decrypted masks
    """

    # verify Mkj = g^mkj mod p
    mask = {}
    for k, mkj in encrypted_mask.items():
        mask[k] = m = int(bytes.decode(decrypt(sk, bytes.fromhex(mkj)), 'ascii'))
        if m < 0:
            m = m % (p - 1)
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
            return {}
            #raise Exception('Mask is Invalid. 2')
    
    return mask


def generateSecureWeight(weight, ri, masks, p, a = 0):
    """ generate secure weight Sj
    Args:
        weight (list): 1-d weight list
        ri (int): random nonce ri
        mask (dict): random masks (mkj)
        p (int): big prime number
        a (int): random value [FullCSA]
    Returns:
        dict: secure weight Sj
    """
    sum_mask = ri - (sum(masks.values()) % p) + a
    return [(w + sum_mask) % p for w in weight]


def computeReconstructionValue(survived, my_masks, masks, cluster_indexes):
    """ compute reconstruction value RSj
    Args:
        survived (list): index list of survived(active) users
        my_masks (dict): random masks by this user (mjk)
        mask (dict): random masks by other users (mkj)
        cluster_indexes (list): survived indexes in a cluster
    Returns:
        int: reconstruction value RSj
    """
    RS = 0
    for k in cluster_indexes:
        if k not in survived:
            RS = RS + masks[k] - my_masks[k]
    return RS


def clustering(a, b, k, rf, cf, U, t):
    # node clustering
    C = {i: [] for i in range(k+1)} # clusters
    Uij = {i: {j: [] for j in range(1, b+1)} for i in range(1, a+1)}
    for user, value in U.items():
        i, j, PS, request = value
        Uij[i][j].append((user, PS, request))

    D = 0
    while rf + D <= a or cf + D <= b:
        r0 = max(rf-D, 1)
        c0 = max(cf-D, 1)
        r1 = min(rf+D, a)
        c1 = min(cf+D, b)
        for r in range(r0, r1+1):
            for c in range(c0, c1+1):
                if abs(r-rf) == D or abs(c-cf) == D:
                    for user, PS, request in Uij[r][c]:
                        C[PS].append([user, request]) # PS is divided into k levels
        D += 1

    # merge clusters for satisfying constraint t
    while k > 0:
        if len(C[k]) < t:
            l = t - len(C[k])
            if len(C[k-1])-l >= t:
                move = []
                for _ in range(l):
                    move.append(C[k-1].pop())
                move.reverse()
                C[k] = move + C[k]
            else:
                C[k-1] = C[k-1] + C[k]
                del C[k]
        k -= 1

    while len(C[0]) < t: # k = 0
        k += 1
        if C.get(k) is None: continue
        C[0] = C[0] + C[k]
        del C[k]

    return C


if __name__ == "__main__":
    # example: node clustring
    n = 25
    a = 5
    b = 10
    k = 9
    t = 6
    U = {}
    for i in range(n):
        U[i] = [random.randrange(1, a+1), random.randrange(1, b+1), random.randrange(0, k), i]
    print(clustering(a, b, k, 1, 2, U, t))

# Lab-SA Secure Protocols
from Crypto.Protocol.SecretSharing import Shamir

# Diffie-Hellman Key Exchange
def DH(u1_pk, u1_sk, u2_pk):
    # u1의 공개키와 비밀키 u1_pk, u1_sk
    # u2의 공개키 u2_pk
    A = u1_pk ** u1_sk % u2_pk
    return A

def encryption(u1_sk, u2_pk, k, data):
    # u1의 데이터를 암호화
    key = k ** u1_sk % u2_pk
    encrypted_data = data + key
    return encrypted_data 


# Secret-Sharing
def make_shares(key, t, n):
    return Shamir.split(t, n, key)

def combine_shares(shares):
    key = Shamir.combine(shares)
    return int.from_bytes(key, 'big')

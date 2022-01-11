# Lab-SA Secure Protocols

# Diffie-Hellman Key Exchange
def DH(c_pk, s_pk, c_sk, s_sk):
    # u1과 u2의 공개키 c_pk, s_pk
    # u1과 u2의 비밀키 c_sk, s_sk

    A = c_pk ** c_sk % s_pk
    B = c_pk ** s_sk % s_pk
    return (A, B)

def encryption(c_pk, s_pk, k, data):
    # u1의 데이터를 암호화
    key = k ** c_pk % s_pk
    encrypted_data = data + key
    return encrypted_data

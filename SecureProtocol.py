# Lab-SA Secure Protocols
from Crypto.Protocol.SecretSharing import Shamir
import random

# find prime number
def primesInRange(x, y):
    prime_list = []
    for n in range(x, y):
        isPrime = True

        for num in range(2, n):
            if n % num == 0:
                isPrime = False

        if isPrime:
            prime_list.append(n)
    return prime_list

prime_list = primesInRange(100, 200) #temp
g = random.choice(prime_list)
p = random.choice(prime_list)

# key generate
def generate():
    pri_key = random.randrange(50000, 90000) #temp
    pub_key = g ** pri_key % p
    return (pub_key, pri_key)

def agree(sk, pk):
    key = pk ** sk % p
    return key

def gcd(a, b):
    while b != 0:
        a, b = b, a % b
    return a

def encrypt(s_uv, u, v, sk_s, bu_s):
    key, n = s_uv
    plaintext = str(u) + ":" + str(v) + ":" + str(sk_s) + ":" + str(bu_s)
    cipher = [(ord(char) ** key) % n for char in plaintext]
    return cipher

def decrypt(s_uv, evu):
    key, n = s_uv
    plain = [chr((char ** key) % n) for char in evu]
    return ''.join(plain)

def get_c_sk(e, tot):
    # k = 1
    k = random.randrange(1, e - 50) #temp
    while (e * k) % tot != 1 or k == e:
        k += 1
    return k

def get_c_pk(tot):
    # e = 2
    e = random.randrange(100, 1000) #temp
    while e < tot and gcd(e, tot) != 1:
        e += 1
    return e

def generate_c():
    totient = (p - 1) * (g - 1)
    c_pk = get_c_pk(totient)
    c_sk = get_c_sk(c_pk, totient)
    return (c_pk, c_sk)


# Secret-Sharing
def make_shares(key, t, n):
    return Shamir.split(t, n, key)

def combine_shares(shares):
    key = Shamir.combine(shares)
    return int.from_bytes(key, 'big')





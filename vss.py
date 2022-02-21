import random
import math


# make N theta_i
# [호출] : 서버
# [인자] : n(사용자수), q
# [리턴] : th(각 client들에 대한 theta list)
def make_theta(n, q):
    th = []
    for i in range(n):
        th.append(random.randint(1, q))
    return th


# Secret polynomium coefficients r_ij
# [호출] : 클라이언트
# [인자] : n(사용자수), q
# [리턴] : rij(사용자 i가 랜덤 생성한 계수)
def get_rij(n, q):
    rij = []
    for j in range(n):
        rij.append(random.randint(1, q))
    return rij


# share를 생성하기 위한 다항식 f
# [인자] : t(자신의 theta), w(quantization한 값), cld(collude한 사용자 list), rij(get_rij()의 리턴값), q
# [리턴] : y
def f(t, w, cld, rij, q):
    y = w
    for i in range(len(cld)):
        y = y + (rij[cld[i]] * (t ** (i+1)))
    # y = y % q
    print("theta: ", t)
    print("final y: ", y)
    return y


# make shares
# [호출] : 클라이언트
# [인자] : list(자신을 제외한 다른 사용자 list), w, t(서버가 알려준 theta list), cld, rij, q
# [리턴] : s(다른 사용자들에게 보낼 share list)
def make_shares(list, w, t, cld, rij, q):
    s = []
    for j in list:
        print("j: ", j)
        s.append(f(t[j], w, cld, rij, q))

    return s


# make commitment
# [호출] : 클라이언트
# [인자] : w, cld, rij, g
# [리턴] : c(verify를 위한 commitment list)
def commitment(w, cld, rij, g, q):
    c = []
    c.append(g**w)

    for i in range(len(cld)):
        c.append(g**rij[cld[i]]) # g**rij[cld[i]] % p
    return c


# 사용자 k에게 받은 S_ki를 verify하려면 k가 생성한 c[]를 인자로
# [호출] : 클라이언트
# [인자] : g, cld, s(다른 사용자 k에게 받은 share), c(k가 생성한 commitment list), t(자신의 theta), q
# [리턴] : c(verify를 위한 commitment list)
def verify(g, cld, s, c, t, q): 
    x = g ** s % q # g ** s % q
    y = c[0]
    for i in range(len(cld)):
        y = y * (c[i+1]**(t**(i+1)))
    y = y % q
    print("x = ", x)
    print("y = ", y)
    if x == y:
        return True
    else:
        return False
  
  

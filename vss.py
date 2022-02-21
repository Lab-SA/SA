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


if __name__ == "__main__":
    n = 4   # 사용자수
    g = 127 # temp
    q = 67 # temp

    # rij = []    # 각 사용자들이 랜덤 생성하는 벡터
    # t = []      # theta를 저장
    cld = [0, 2, 3]     # collude 사용자 인덱스 리스트 (0,2,3이라 가정)
    t = make_theta(n, q)
    print("t : ", t)

    # 0번 user인 경우
    list0 = [1, 2, 3]
    r0j = get_rij(n, q)
    w0 = 67
    s0 = make_shares(list0, w0, t, cld, r0j, q)
    c0 = commitment(w0, cld, r0j, g, q)
    print("r0j = ", r0j)
    print("s0 = ", s0)
    print("c0 = ", c0)

    # 1번 user인 경우
    list1 = [0, 2, 3]
    r1j = get_rij(n, q)
    w1 = 150
    s1 = make_shares(list1, w1, t, cld, r1j, q)
    c1 = commitment(w1, cld, r1j, g, q)
    print("r1j = ", r1j)
    print("s1 = ", s1)
    print("c1 = ", c1)

    # 0번 user가 1번 user에게 받은 s_10 verify
    print(verify(g, cld, s1[0], c1, t[0], q))

  
  

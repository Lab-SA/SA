import random


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
# [인자] : T(threshold), q
# [리턴] : rij(사용자 i가 랜덤 생성한 계수)(j: 1~T)
def generate_rij(T, q):
    rij = [0, ] # not using first index (0)
    for j in range(T):
        rij.append(random.randint(1, q))
    return rij


# share를 생성하기 위한 다항식 f
# [인자] : theta(자신의 theta), w(weights. quantization한 값), T(collude한 사용자 수), rij(get_rij()의 리턴값), q
# [리턴] : y
def f(theta, w, T, rij, q):
    y = w
    for j in range(1, T+1):
        y = y + (rij[j] * (theta ** j))
        y = y % q
    return y


# make shares
# [호출] : 클라이언트
# [인자] : w, theta_list(서버가 알려준 theta list), T, rij_list, q
# [리턴] : shares (다른 사용자들에게 보낼 share list)
def make_shares(w, theta_list, T, rij_list, q):
    shares = []
    for theta in theta_list:
        shares.append(f(theta, w, T, rij_list, q))
    return shares


# make commitment
# [호출] : 클라이언트
# [인자] : w, rij_list, g, q
# [리턴] : commitments (verify를 위한 commitment list)
def generate_commitments(w, rij_list, g, q):
    commitments = []
    for i, rij in enumerate(rij_list):
        if i == 0:
            commitments.append((g**w) % q) # index 0
            continue
        commitments.append((g**rij) % q)
    return commitments


# verify commitments
# [호출] : 클라이언트
# [인자] : g, share(i 에게서 받은 share), commitments(i 가 생성한 commitment list), theta(자신의 theta), q
# [리턴] : boolean
def verify(g, share, commitments, theta, q): 
    x = g ** share % q # g ** s % q
    y = 1
    for i, c in enumerate(commitments):
        y = y * (c**(theta**i))
        y = y % q
    print("x = ", x)
    print("y = ", y)
    if x == y:
        return True
    else:
        return False
  
  
if __name__ == "__main__":
    w = 100
    q = 7
    g = 3
    n = 10
    T = 3
    
    theta_list = make_theta(n, q)
    rij_list = generate_rij(T, q)
    shares = make_shares(w, theta_list, T, rij_list, q)
    commitments = generate_commitments(w, rij_list, g, q)
    result = verify(g, shares[0], commitments, theta_list[0], q)

    print(theta_list)
    print(rij_list)
    print(shares)
    print(commitments)
    print(result)


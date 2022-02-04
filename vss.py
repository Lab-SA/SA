import random
import math

n = 4   # 사용자수
q = 127 # temp

rij = []    # 각 사용자들이 랜덤 생성하는 벡터
t = []      # theta를 저장
cld = [0, 2, 3]     # collude 사용자 인덱스 리스트
list = [1, 2, 3]    # 0번 user인 경우

# make N theta_i
def make_theta(n, q):   # Server
    th = []
    for i in range(n):
        th.append(random.randint(1, q))
    return th

# Secret polynomium coefficients r_ij
def get_rij(n, q):
    rij = []
    for j in range(n):
        rij.append(random.randint(1, q))
    return rij

def f(x, w, cld, rij, q):
    y = w
    for i in range(len(cld)):
        y = y + rij[cld[i]] * (x ** (i+1))
        print(y)
    y = y % q
    return y

# make shares
def vss(list, w, x):
    t = make_theta(n, q)
    rij = get_rij(n, q)
    s = []
    for j in list:
        s.append(f(t[j], w, cld, rij, q))
    return s
  
  

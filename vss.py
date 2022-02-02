import random
import math

n = 4
q = 127

rij = []
t = []
cld = [0, 2, 3]     # collude 사용자 인덱스 리스트
list = [1, 2, 3]    # 0번 user인 경우

# make N theta_i
def make_theta():   # Server
    th = []
    for i in range(n):
        th.append(random.randint(1, q))
    return th

# Secret polynomium coefficients r_ij
def get_rij():
    for j in range(n):
        rij.append(random.randint(1,q))
    return rij

def f(x, w):
    y = w
    for i in range(len(cld)):
        y = y + rij[cld[i]] * (x ** (i+1))
        print(y)
    y = y % q
    return y

# make shares
def vss(list, w, x):
    t = make_theta()
    rij = get_rij()
    s = []
    for j in list:
        s.append(f(t[j], w))
    return s
  
  

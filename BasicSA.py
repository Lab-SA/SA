# Lab-SA Basic SA for Federated Learning
import random
import SecureProtocol as sp

# Generate two key pairs
def generateKeyPairs():
    (c_pk, c_sk) = sp.generate() #temp
    (s_pk, s_sk) = sp.generate() #temp
    return ((c_pk, c_sk), (s_pk, s_sk))

# Generate secret-shares of s_sk and bu and encrypt those data
def generateSharesOfMask(t, users, u, s_sk, c_sk, c_pk):
    bu = random.randrange(1, 100) # 1~99 #temp
    s_sk_shares_list = sp.share(s_sk, t, users) #temp
    bu_shares_list = sp.share(bu, t, users) #temp
    euv_list = []
    for i, v in enumerate(users):
        euv = sp.encrypt((c_sk, c_pk), (u, v, s_sk_shares_list[i], bu_shares_list[i])) #temp
        euv_list.append(euv)
    return euv_list

# just for testing
# if __name__ == "__main__":

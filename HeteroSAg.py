# Lab-SA HeteroSAg for Federated Learning

def SS_Matrix(G):
    # G = the number of groups
    B = [['*' for x in range(G)] for y in range(G)]
    for g in range(G - 1):
        for r in range(G - g - 1):
            l = 2 * g + r
            B[l % G][g] = g
            B[l % G][g + r + 1] = g
    for i in range(G):
        for j in range(G):
            if B[i][j] == '*':
                B[i][j] = j
    return B

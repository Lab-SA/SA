from poly_calc import gf_div, gf_inverse, gf_mul, gf_mult_noLUT, gf_poly_add, gf_poly_div, gf_poly_eval, gf_poly_mul, gf_poly_scale, gf_pow, gf_sub 

gf_exp = [0] * 512 # Create list of 512 elements. In Python 2.6+, consider using bytearray
gf_log = [0] * 256

class ReedSolomonError(Exception):
    pass

try:
    raise ReedSolomonError("Some error message")
except ReedSolomonError as e:
    pass # do something here
 
def init_tables(prim=0x11d):
    '''Precompute the logarithm and anti-log tables for faster computation later, using the provided primitive polynomial.'''

    gf_exp = [0] * 512 # anti-log (exponential) table
    gf_log = [0] * 256 # log table
    # For each possible value in the galois field 2^8, we will pre-compute the logarithm and anti-logarithm (exponential) of this value
    x = 1
    for i in range(0, 255):
        gf_exp[i] = x 
        gf_log[x] = i 
        x = gf_mult_noLUT(x, 2, prim)

    # Optimization: double the size of the anti-log table so that we don't need to mod 255 to
    # stay inside the bounds (because we will mainly use this table for the multiplication of two GF numbers, no more).
    for i in range(255, 512):
        gf_exp[i] = gf_exp[i - 255]
    return [gf_log, gf_exp]


def rs_encode_msg(msg_in, nsym):

    '''Reed-Solomon main encoding function, using polynomial division (algorithm Extended Synthetic Division)'''
    if (len(msg_in) + nsym) > 255: raise ValueError("Message is too long (%i when max is 255)" % (len(msg_in)+nsym))
    
    gen = rs_generator_poly(nsym)
    # Init msg_out with the values inside msg_in and pad with len(gen)-1 bytes (which is the number of ecc symbols).
    msg_out = [0] * (len(msg_in) + len(gen)-1)
    
    # Initializing the Synthetic Division with the dividend (= input message polynomial)
    msg_out[:len(msg_in)] = msg_in

    

    # Synthetic division main loop
    for i in range(len(msg_in)):

        coef = msg_out[i]
        if coef != 0:
            # in synthetic division, we always skip the first coefficient of the divisior, because it's only used to normalize the dividend coefficient (which is here useless since the divisor, the generator polynomial, is always monic)
            for j in range(1, len(gen)):
                msg_out[i+j] ^= gf_mul(gen[j], coef) 

    # our complete codeword composed of the message + code.
    msg_out[:len(msg_in)] = msg_in

    return msg_out

def rs_generator_poly(nsym):
    '''Generate an irreducible generator polynomial (necessary to encode a message into Reed-Solomon)'''
    g = [1]
    for i in range(0, nsym):
        g = gf_poly_mul(g, [1, gf_pow(2, i)])
    return g


def rs_calc_syndromes(msg, nsym):
    '''Given the received codeword msg and the number of error correcting symbols (nsym), computes the syndromes polynomial.
    Mathematically, it's essentially equivalent to a Fourrier Transform (Chien search being the inverse).
    '''
    synd = [0] * nsym
    for i in range(0, nsym):
        synd[i] = gf_poly_eval(msg, gf_pow(2,i))
    return [0] + synd # pad with one 0 for mathematical precision (else we can end up with weird calculations sometimes)


def rs_check(msg, nsym):
    '''Returns true if the message + ecc has no error or false otherwise (may not always catch a wrong decoding or a wrong message, particularly if there are too many errors -- above the Singleton bound --, but it usually does)'''
    return ( max(rs_calc_syndromes(msg, nsym)) == 0 )

def rs_find_errata_locator(e_pos):
    '''Compute the erasures/errors/errata locator polynomial from the erasures/errors/errata positions
       (the positions must be relative to the x coefficient, eg: "hello worldxxxxxxxxx" is tampered to "h_ll_ worldxxxxxxxxx"
       with xxxxxxxxx being the ecc of length n-k=9, here the string positions are [1, 4], but the coefficients are reversed
       since the ecc characters are placed as the first coefficients of the polynomial, thus the coefficients of the
       erased characters are n-1 - [1, 4] = [18, 15] = erasures_loc to be specified as an argument.'''
    e_loc = [1] # just to init because we will multiply, so it must be 1 so that the multiplication starts correctly without nulling any term
    # erasures_loc = product(1 - x*alpha**i) for i in erasures_pos and where alpha is the alpha chosen to evaluate polynomials.
    for i in e_pos:
        e_loc = gf_poly_mul( e_loc, gf_poly_add([1], [gf_pow(2, i), 0]) )
    return e_loc

def rs_find_error_evaluator(synd, err_loc, nsym):
    '''Compute the error (or erasures if you supply sigma=erasures locator polynomial, or errata) evaluator polynomial Omega
       from the syndrome and the error/erasures/errata locator Sigma.'''
    _, remainder = gf_poly_div( gf_poly_mul(synd, err_loc), ([1] + [0]*(nsym+1)) )
    return remainder

def rs_correct_errata(msg_in, synd, err_pos): # err_pos is a list of the positions of the errors/erasures/errata
    '''Forney algorithm, computes the values (error magnitude) to correct the input message.'''
    coef_pos = [len(msg_in) - 1 - p for p in err_pos] 
    err_loc = rs_find_errata_locator(coef_pos)
    err_eval = rs_find_error_evaluator(synd[::-1], err_loc, len(err_loc)-1)[::-1]

    # Second part of Chien search to get the error location polynomial X from the error positions in err_pos (the roots of the error locator polynomial, ie, where it evaluates to 0)
    X = [] # will store the position of the errors
    for i in range(0, len(coef_pos)):
        l = 255 - coef_pos[i]
        X.append( gf_pow(2, -l) )

    # Forney algorithm: compute the magnitudes
    E = [0] * (len(msg_in)) # will store the values that need to be corrected (substracted) to the message containing errors. This is sometimes called the error magnitude polynomial.
    Xlength = len(X)
    for i, Xi in enumerate(X):
        Xi_inv = gf_inverse(Xi)
        err_loc_prime_tmp = []
        for j in range(0, Xlength):
            if j != i:
                err_loc_prime_tmp.append( gf_sub(1, gf_mul( Xi_inv, X[j])) )
        err_loc_prime = 1
        for coef in err_loc_prime_tmp:
            err_loc_prime = gf_mul(err_loc_prime, coef)
        y = gf_poly_eval(err_eval[::-1], Xi_inv)
        y = gf_mul(gf_exp, gf_log, gf_pow(Xi, 1), y)
        
        if err_loc_prime == 0:
            raise ReedSolomonError("Could not find error magnitude")    # Could not find error magnitude

        # Compute the magnitude
        magnitude = gf_div( y, err_loc_prime) 
        E[err_pos[i]] = magnitude 

    msg_in = gf_poly_add(msg_in, E) 
    return msg_in

def rs_find_error_locator(synd, nsym, erase_loc=None, erase_count=0):
    '''Find error/errata locator and evaluator polynomials with Berlekamp-Massey algorithm'''

    # Init the polynomials
    if erase_loc:
        err_loc = list(erase_loc)
        old_loc = list(erase_loc)
    else:
        err_loc = [1] 
        old_loc = [1] 
    synd_shift = len(synd) - nsym

    for i in range(0, nsym-erase_count): 
        if erase_loc: 
            K = erase_count+i+synd_shift
        else: 
            K = i+synd_shift

        delta = synd[K]
        for j in range(1, len(err_loc)):
            delta ^= gf_mul( err_loc[-(j+1)], synd[K - j]) 

        old_loc = old_loc + [0]

        if delta != 0: 
            if len(old_loc) > len(err_loc): 
                new_loc = gf_poly_scale(old_loc, delta)
                old_loc = gf_poly_scale(err_loc, gf_inverse( delta)) 
                err_loc = new_loc

            err_loc = gf_poly_add(err_loc, gf_poly_scale(old_loc, delta))

    while len(err_loc) and err_loc[0] == 0: del err_loc[0] 
    errs = len(err_loc) - 1
    if (errs-erase_count) * 2 + erase_count > nsym:
        raise ReedSolomonError("Too many errors to correct") 

    return err_loc

def rs_find_errors(err_loc, nmess): # nmess is len(msg_in)
    '''Find the roots (ie, where evaluation = zero) of error polynomial by brute-force trial, this is a sort of Chien's search
    (but less efficient, Chien's search is a way to evaluate the polynomial such that each evaluation only takes constant time).'''
    global gf_exp, gf_log
    errs = len(err_loc) - 1
    err_pos = []
    for i in range(nmess): 
        if gf_poly_eval(err_loc, gf_pow( 2, i)) == 0: 
            err_pos.append(nmess - 1 - i)
    # Sanity check: the number of errors/errata positions found should be exactly the same as the length of the errata locator polynomial
    if len(err_pos) != errs:
        # couldn't find error locations
        raise ReedSolomonError("Too many (or few) errors found by Chien Search for the errata locator polynomial!")
    return err_pos

def rs_forney_syndromes(synd, pos, nmess):
    # Compute Forney syndromes, which computes a modified syndromes to compute only errors (erasures are trimmed out). Do not confuse this with Forney algorithm, which allows to correct the message based on the location of errors.
    erase_pos_reversed = [nmess-1-p for p in pos] # prepare the coefficient degree positions (instead of the erasures positions)

    # Optimized method, all operations are inlined
    global gf_exp, gf_log
    fsynd = list(synd[1:])      # make a copy and trim the first coefficient which is always 0 by definition
    for i in range(0, len(pos)):
        x = gf_pow(gf_exp, gf_log, 2, erase_pos_reversed[i])
        for j in range(0, len(fsynd) - 1):
            fsynd[j] = gf_mul(fsynd[j], x) ^ fsynd[j + 1]
    return fsynd

def rs_correct_msg(msg_in, nsym, erase_pos=None):
    '''Reed-Solomon main decoding function'''
    
    if len(msg_in) > 255:
        raise ValueError("Message is too long (%i when max is 255)" % len(msg_in))

    msg_out = list(msg_in)
   
    if erase_pos is None:
        erase_pos = []
    else:
        for e_pos in erase_pos:
            msg_out[e_pos] = 0
    # check if there are too many erasures to correct (beyond the Singleton bound)
    if len(erase_pos) > nsym: raise ReedSolomonError("Too many erasures to correct")

    synd = rs_calc_syndromes(msg_out, nsym)
    if max(synd) == 0:
        return msg_out[:-nsym], msg_out[-nsym:]  # no errors

    
    fsynd = rs_forney_syndromes(synd, erase_pos, len(msg_out))
    
    err_loc = rs_find_error_locator(fsynd, nsym, erase_count=len(erase_pos))
    
    err_pos = rs_find_errors(err_loc[::-1] , len(msg_out))
    if err_pos is None:
        raise ReedSolomonError("Could not locate error")    # error location failed

    # Find errors values and apply them to correct the message
    msg_out = rs_correct_errata(msg_out, synd, (erase_pos + err_pos))

    # check if the final message is fully repaired
    synd = rs_calc_syndromes(msg_out, nsym)
    if max(synd) > 0:
        raise ReedSolomonError("Could not correct message")  
    # return the successfully decoded message
    return msg_out[:-nsym], msg_out[-nsym:] 


# Poly cacluation function

def gf_poly_mul(p,q):
    '''Multiply two polynomials, inside Galois Field'''
    r = [0] * (len(p)+len(q)-1)
    for j in range(0, len(q)):
        for i in range(0, len(p)):
            r[i+j] ^= gf_mul(p[i], q[j])                                                         
    return r

def gf_pow(x, power):
    return gf_exp[(gf_log[x] * power) % 255]

def gf_inverse(x):
    return gf_exp[255 - gf_log[x]] 

def gf_mul(x,y):
    if x==0 or y==0:
        return 0
    return gf_exp[gf_log[x] + gf_log[y]] 

def gf_add(x, y):
    return x ^ y

def gf_sub(x, y):
    return x ^ y

def gf_poly_add(p,q):
    r = [0] * max(len(p),len(q))
    for i in range(0,len(p)):
        r[i+len(r)-len(p)] = p[i]
    for i in range(0,len(q)):
        r[i+len(r)-len(q)] ^= q[i]
    return r

def gf_poly_scale(p,x):
    r = [0] * len(p)
    for i in range(0, len(p)):
        r[i] = gf_mul(p[i], x)
    return r

def gf_div(gf_exp, gf_log, x,y):
    if y==0:
        raise ZeroDivisionError()
    if x==0:
        return 0
    return gf_exp[(gf_log[x] + 255 - gf_log[y]) % 255]

def gf_poly_eval(poly, x):
    '''Evaluates a polynomial in GF(2^p) given the value for x. This is based on Horner's scheme for maximum efficiency.'''
    y = poly[0]
    for i in range(1, len(poly)):
        y = gf_mul(y, x) ^ poly[i]
    return y

def gf_poly_div(dividend, divisor):
    '''Fast polynomial division by using Extended Synthetic Division and optimized for GF(2^p) computations
    (doesn't work with standard polynomials outside of this galois field, see the Wikipedia article for generic algorithm).'''
    msg_out = list(dividend) 
    for i in range(0, len(dividend) - (len(divisor)-1)):

        coef = msg_out[i] 
        if coef != 0: 
            for j in range(1, len(divisor)):
                if divisor[j] != 0: 
                    msg_out[i + j] ^= gf_mul(divisor[j], coef) 

    separator = -(len(divisor)-1)
    return msg_out[:separator], msg_out[separator:] 

def gf_mult_noLUT(x, y, prim=0):
    '''Multiplication in Galois Fields without using a precomputed look-up table
    by using the standard carry-less multiplication + modular reduction using an irreducible prime polynomial'''

    def cl_mult(x,y):
        '''Bitwise carry-less multiplication on integers'''
        z = 0
        i = 0
        while (y>>i) > 0:
            if y & (1<<i):
                z ^= x<<i
            i += 1
        return z

    def bit_length(n):
        '''Compute the position of the most significant bit (1) of an integer.'''
        bits = 0
        while n >> bits: bits += 1
        return bits

    def cl_div(dividend, divisor=None):
        '''Bitwise carry-less long division on integers and returns the remainder'''
        dl1 = bit_length(dividend)
        dl2 = bit_length(divisor)

        if dl1 < dl2:
            return dividend
        for i in range(dl1-dl2,-1,-1):
            if dividend & (1 << i+dl2-1):
                dividend ^= divisor << i
        return dividend

    result = cl_mult(x,y)
    if prim > 0:
        result = cl_div(result, prim)

    return result

def gf_poly_eval(poly, x):
    '''Evaluates a polynomial in GF(2^p) given the value for x. This is based on Horner's scheme for maximum efficiency.'''
    y = poly[0]
    for i in range(1, len(poly)):
        y = gf_mul(y, x) ^ poly[i]
    return y


if __name__ == "__main__": 

    msg_in = [ 0x40, 0xd2, 0x75, 0x47, 0x76, 0x17, 0x32, 0x06, 0x27, 0x26, 0x96, 0xc6, 0xc6, 0x96, 0x70, 0xec ] 

    prim = 0x11d
    n = 20 # set the size 
    k = 11 # k = len(message)
    message = "hello world" # input message

    # Initializing the log/antilog tables
    init_tables(prim)

    # Encoding the input message
    mesecc = rs_encode_msg(msg_in, n-k)
    print("Original: %s" % mesecc)

    # change 6 characters of the message 
    mesecc[0] = 0
    mesecc[1] = 2
    mesecc[2] = 2
    mesecc[3] = 2
    mesecc[4] = 2
    mesecc[5] = 2
    print("Corrupted: %s" % mesecc)

    # Decoding/repairing the corrupted message
    corrected_message, corrected_ecc = rs_correct_msg(mesecc, n-k)
    print("Repaired: %s" % (corrected_message+corrected_ecc))
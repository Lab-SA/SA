gf_exp = [0] * 512 # Create list of 512 elements. In Python 2.6+, consider using bytearray
gf_log = [0] * 256
 
def init_tables(prim=0x11d):
    '''Precompute the logarithm and anti-log tables for faster computation later, using the provided primitive polynomial.'''

    global gf_exp, gf_log
    gf_exp = [0] * 512 # anti-log (exponential) table
    gf_log = [0] * 256 # log table
    # For each possible value in the galois field 2^8, we will pre-compute the logarithm and anti-logarithm (exponential) of this value
    x = 1
    for i in range(0, 255):
        gf_exp[i] = x # compute anti-log for this value and store it in a table
        gf_log[x] = i # compute log at the same time
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

def gf_poly_mul(p,q):
    '''Multiply two polynomials, inside Galois Field'''
    r = [0] * (len(p)+len(q)-1)
    for j in range(0, len(q)):
        for i in range(0, len(p)):
            r[i+j] ^= gf_mul(p[i], q[j])                                                         
    return r

def gf_pow(x, power):
    return gf_exp[(gf_log[x] * power) % 255]

def gf_mul(x,y):
    if x==0 or y==0:
        return 0
    return gf_exp[gf_log[x] + gf_log[y]] 

def gf_mult_noLUT(x, y, prim=0):
    '''Multiplication in Galois Fields without using a precomputed look-up table (and thus it's slower)
    by using the standard carry-less multiplication + modular reduction using an irreducible prime polynomial'''

    ### Define bitwise carry-less operations as inner functions ###
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
        '''Compute the position of the most significant bit (1) of an integer. Equivalent to int.bit_length()'''
        bits = 0
        while n >> bits: bits += 1
        return bits

    def cl_div(dividend, divisor=None):
        '''Bitwise carry-less long division on integers and returns the remainder'''
        # Compute the position of the most significant bit for each integers
        dl1 = bit_length(dividend)
        dl2 = bit_length(divisor)
        # If the dividend is smaller than the divisor, just exit
        if dl1 < dl2:
            return dividend
        # Else, align the most significant 1 of the divisor to the most significant 1 of the dividend (by shifting the divisor)
        for i in range(dl1-dl2,-1,-1):
            # Check that the dividend is divisible (useless for the first iteration but important for the next ones)
            if dividend & (1 << i+dl2-1):
                # If divisible, then shift the divisor to align the most significant bits and XOR (carry-less subtraction)
                dividend ^= divisor << i
        return dividend
    
    ### Main GF multiplication routine ###

    # Multiply the gf numbers
    result = cl_mult(x,y)
    if prim > 0:
        result = cl_div(result, prim)

    return result


if __name__ == "__main__": #temp parameters 


    msg_in = [ 0x40, 0xd2, 0x75, 0x47, 0x76, 0x17, 0x32, 0x06, 0x27, 0x26, 0x96, 0xc6, 0xc6, 0x96, 0x70, 0xec ] 

    init_tables(0x11d)
    msg = rs_encode_msg(msg_in, 10)

    for i in range(0, len(msg)):
        print(hex(msg[i]), end=' ')

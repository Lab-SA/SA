import itertools
import math


################### INIT and stuff ###################

try:  
    bytearray
    _bytearray = bytearray
except NameError:  
    from array import array
    def _bytearray(obj = 0, encoding = "latin-1"):  
        '''Simple bytearray replacement'''
        if isinstance(obj, str):
            obj = [ord(ch) for ch in obj.encode(encoding)]
        elif isinstance(obj, int):
            obj = [0] * obj
        return array("B", obj)

try:  
    xrange
except NameError:  
    xrange = range

class ReedSolomonError(Exception):
    pass

gf_exp = _bytearray([1] * 512) 
gf_log = _bytearray(256)
field_charac = int(2**8 - 1)

################### GALOIS FIELD ELEMENTS MATHS ###################

def rwh_primes1(n):
    ''' Returns  a list of primes < n '''
    sieve = [True] * int(n/2)
    for i in xrange(3,int(n**0.5)+1,2):
        if sieve[int(i/2)]:
            sieve[int((i*i)/2)::i] = [False] * int((n-i*i-1)/(2*i)+1)
    return [2] + [2*i+1 for i in xrange(1,int(n/2)) if sieve[i]]

def find_prime_polys(generator=2, c_exp=8, fast_primes=False, single=False):
    '''Compute the list of prime polynomials for the given generator and galois field characteristic exponent.'''
    root_charac = 2 # we're in GF(2)
    field_charac = int(root_charac**c_exp - 1)
    field_charac_next = int(root_charac**(c_exp+1) - 1)

    prim_candidates = []
    if fast_primes:
        prim_candidates = rwh_primes1(field_charac_next) 
        prim_candidates = [x for x in prim_candidates if x > field_charac] 
    else:
        prim_candidates = xrange(field_charac+2, field_charac_next, root_charac) 

    correct_primes = []
    for prim in prim_candidates: 
        seen = _bytearray(field_charac+1) 
        conflict = False 

        x = 1
        for i in xrange(field_charac):
            x = gf_mult_noLUT(x, generator, prim, field_charac+1)
            if x > field_charac or seen[x] == 1:
                conflict = True
                break
            else:
                seen[x] = 1

        if not conflict: 
            correct_primes.append(prim)
            if single: return prim

    return correct_primes 

def init_tables(prim=0x11d, generator=2, c_exp=8):

    global _bytearray
    if c_exp <= 8:
        _bytearray = bytearray
    else:
        from array import array
        def _bytearray(obj = 0, encoding = "latin-1"):
            '''Fake bytearray replacement, supporting int values above 255'''
            if isinstance(obj, str):  
                obj = obj.encode(encoding)
                if isinstance(obj, str):  
                    obj = [ord(chr) for chr in obj]
                elif isinstance(obj, bytes):  
                    obj = [int(chr) for chr in obj]
                else:
                    raise(ValueError, "Type of object not recognized!")
            elif isinstance(obj, int):
                obj = [0] * obj
            return array("i", obj)

    # Init global tables
    global gf_exp, gf_log, field_charac
    field_charac = int(2**c_exp - 1)
    gf_exp = _bytearray(field_charac * 2)
    gf_log = _bytearray(field_charac+1)

    x = 1
    for i in xrange(field_charac):
        gf_exp[i] = x
        gf_log[x] = i 
        x = gf_mult_noLUT(x, generator, prim, field_charac+1)

    for i in xrange(field_charac, field_charac * 2):
        gf_exp[i] = gf_exp[i - field_charac]

    return [gf_log, gf_exp, field_charac]

def gf_add(x, y):
    return x ^ y

def gf_sub(x, y):
    return x ^ y 
def gf_neg(x):
    return x

def gf_inverse(x):
    return gf_exp[field_charac - gf_log[x]] 

def gf_mul(x, y):
    if x == 0 or y == 0:
        return 0
    return gf_exp[(gf_log[x] + gf_log[y]) % field_charac]

def gf_div(x, y):
    if y == 0:
        raise ZeroDivisionError()
    if x == 0:
        return 0
    return gf_exp[(gf_log[x] + field_charac - gf_log[y]) % field_charac]

def gf_pow(x, power):
    return gf_exp[(gf_log[x] * power) % field_charac]

def gf_mult_noLUT_slow(x, y, prim=0):
    '''Multiplication in Galois Fields without using a precomputed look-up table (and thus it's slower) by using the standard carry-less multiplication + modular reduction using an irreducible prime polynomial.'''

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
        dl1 = bit_length(dividend)
        dl2 = bit_length(divisor)
        if dl1 < dl2:
            return dividend
        for i in xrange(dl1-dl2,-1,-1):
            if dividend & (1 << i+dl2-1):
                dividend ^= divisor << i
        return dividend
 
    ### Main GF multiplication routine ###
 
    result = cl_mult(x,y)
    if prim > 0:
        result = cl_div(result, prim)
 
    return result

def gf_mult_noLUT(x, y, prim=0, field_charac_full=256, carryless=True):
    r = 0
    while y:
        if y & 1: r = r ^ x if carryless else r + x 
        y = y >> 1 # equivalent to y // 2
        x = x << 1 # equivalent to x*2
        if prim > 0 and x & field_charac_full: x = x ^ prim 

    return r


################### GALOIS FIELD POLYNOMIALS MATHS ###################

def gf_poly_scale(p, x):
    return _bytearray([gf_mul(p[i], x) for i in xrange(len(p))])

def gf_poly_add(p, q):
    r = _bytearray( max(len(p), len(q)) )
    r[len(r)-len(p):len(r)] = p
    for i in xrange(len(q)):
        r[i + len(r) - len(q)] ^= q[i]
    return r

def gf_poly_mul(p, q):
    r = _bytearray(len(p) + len(q) - 1)
    lp = [gf_log[p[i]] for i in xrange(len(p))]
    for j in xrange(len(q)):
        qj = q[j] 
        if qj != 0: 
            lq = gf_log[qj]
            for i in xrange(len(p)):
                if p[i] != 0:
                    r[i + j] ^= gf_exp[lp[i] + lq] 
    return r

def gf_poly_mul_simple(p, q):
    r = _bytearray(len(p) + len(q) - 1)
    for j in xrange(len(q)):
        for i in xrange(len(p)):
            r[i + j] ^= gf_mul(p[i], q[j])
    return r

def gf_poly_neg(poly):
    return poly

def gf_poly_div(dividend, divisor):
    msg_out = _bytearray(dividend) 
    for i in xrange(len(dividend) - (len(divisor)-1)):
        coef = msg_out[i] 
        if coef != 0: 
            for j in xrange(1, len(divisor)):
                if divisor[j] != 0: 
                    msg_out[i + j] ^= gf_mul(divisor[j], coef) 
    separator = -(len(divisor)-1)
    return msg_out[:separator], msg_out[separator:] 

def gf_poly_square(poly):  
  
    length = len(poly)
    out = _bytearray(2*length - 1)
    for i in xrange(length-1):
        p = poly[i]
        k = 2*i
        if p != 0:
            out[k] = gf_exp[2*gf_log[p]]
    out[2*length-2] = gf_exp[2*gf_log[poly[length-1]]]
    if out[0] == 0: out[0] = 2*poly[1] - 1
    return out

def gf_poly_eval(poly, x):
    y = poly[0]
    for i in xrange(1, len(poly)):
        y = gf_mul(y, x) ^ poly[i]
    return y


################### REED-SOLOMON ENCODING ###################

def rs_generator_poly(nsym, fcr=0, generator=2):

    g = _bytearray([1])
    for i in xrange(nsym):
        g = gf_poly_mul(g, [1, gf_pow(generator, i+fcr)])
    return g

def rs_generator_poly_all(max_nsym, fcr=0, generator=2):
    g_all = {}
    g_all[0] = g_all[1] = _bytearray([1])
    for nsym in xrange(max_nsym):
        g_all[nsym] = rs_generator_poly(nsym, fcr, generator)
    return g_all

def rs_simple_encode_msg(msg_in, nsym, fcr=0, generator=2, gen=None):
    global field_charac
    if (len(msg_in) + nsym) > field_charac: raise ValueError("Message is too long (%i when max is %i)" % (len(msg_in)+nsym, field_charac))
    if gen is None: gen = rs_generator_poly(nsym, fcr, generator)

    _, remainder = gf_poly_div(msg_in + _bytearray(len(gen)-1), gen)
    msg_out = msg_in + remainder
    return msg_out

def rs_encode_msg(msg_in, nsym, fcr=0, generator=2, gen=None):
    global field_charac
    if (len(msg_in) + nsym) > field_charac: raise ValueError("Message is too long (%i when max is %i)" % (len(msg_in)+nsym, field_charac))
    if gen is None: gen = rs_generator_poly(nsym, fcr, generator)

    msg_in = _bytearray(msg_in)
    msg_out = _bytearray(msg_in) + _bytearray(len(gen)-1)

    lgen = _bytearray([gf_log[gen[j]] for j in xrange(len(gen))])

    for i in xrange(len(msg_in)):
        coef = msg_out[i] 
        if coef != 0: 
            lcoef = gf_log[coef] 

            for j in xrange(1, len(gen)): 
                msg_out[i + j] ^= gf_exp[lcoef + lgen[j]]

    msg_out[:len(msg_in)] = msg_in 
    return msg_out


################### REED-SOLOMON DECODING ###################

def rs_calc_syndromes(msg, nsym, fcr=0, generator=2):
    return [0] + [gf_poly_eval(msg, gf_pow(generator, i+fcr)) for i in xrange(nsym)]

def rs_correct_errata(msg_in, synd, err_pos, fcr=0, generator=2): 
    global field_charac
    msg = _bytearray(msg_in)
   
    coef_pos = [len(msg) - 1 - p for p in err_pos] # need to convert the positions to coefficients degrees for the errata locator algo to work (eg: instead of [0, 1, 2] it will become [len(msg)-1, len(msg)-2, len(msg) -3])
    err_loc = rs_find_errata_locator(coef_pos, generator)
   
    err_eval = rs_find_error_evaluator(synd[::-1], err_loc, len(err_loc)-1)[::-1]

   
    X = [] # will store the position of the errors
    for i in xrange(len(coef_pos)):
        l = field_charac - coef_pos[i]
        X.append( gf_pow(generator, -l) )

    E = _bytearray(len(msg)) # will store the values that need to be corrected (substracted) to the message containing errors. This is sometimes called the error magnitude polynomial.
    Xlength = len(X)
    for i, Xi in enumerate(X):

        Xi_inv = gf_inverse(Xi)

        err_loc_prime_tmp = []
        for j in xrange(Xlength):
            if j != i:
                err_loc_prime_tmp.append( gf_sub(1, gf_mul(Xi_inv, X[j])) )
    
        err_loc_prime = 1
        for coef in err_loc_prime_tmp:
            err_loc_prime = gf_mul(err_loc_prime, coef)
    

        if err_loc_prime == 0:
            raise ReedSolomonError("Decoding failed: Forney algorithm could not properly detect where the errors are located (errata locator prime is 0).")

        y = gf_poly_eval(err_eval[::-1], Xi_inv) 
        y = gf_mul(gf_pow(Xi, 1-fcr), y) 
        
        magnitude = gf_div(y, err_loc_prime) 
        E[err_pos[i]] = magnitude 

    msg = gf_poly_add(msg, E) 
    return msg

def rs_find_error_locator(synd, nsym, erase_loc=None, erase_count=0):

    # Init the polynomials
    if erase_loc: 
        err_loc = _bytearray(erase_loc)
        old_loc = _bytearray(erase_loc)
    else:
        err_loc = _bytearray([1]) 
        old_loc = _bytearray([1]) 

    synd_shift = 0
    if len(synd) > nsym: synd_shift = len(synd) - nsym

    for i in xrange(nsym-erase_count):
        if erase_loc: 
            K = erase_count+i+synd_shift
        else: 
            K = i+synd_shift

        delta = synd[K]
        for j in xrange(1, len(err_loc)):
            delta ^= gf_mul(err_loc[-(j+1)], synd[K - j]) 
     
        old_loc = old_loc + _bytearray([0])

        if delta != 0: 
            if len(old_loc) > len(err_loc): 
                new_loc = gf_poly_scale(old_loc, delta)
                old_loc = gf_poly_scale(err_loc, gf_inverse(delta)) 
                err_loc = new_loc

            err_loc = gf_poly_add(err_loc, gf_poly_scale(old_loc, delta))

    err_loc = list(itertools.dropwhile(lambda x: x == 0, err_loc)) 
    errs = len(err_loc) - 1
    if (errs-erase_count) * 2 + erase_count > nsym:
        raise ReedSolomonError("Too many errors to correct")

    return err_loc

def rs_find_errata_locator(e_pos, generator=2):
    e_loc = [1] 
    for i in e_pos:
        e_loc = gf_poly_mul( e_loc, gf_poly_add(_bytearray([1]), [gf_pow(generator, i), 0]) )
    return e_loc

def rs_find_error_evaluator(synd, err_loc, nsym):
    _, remainder = gf_poly_div( gf_poly_mul(synd, err_loc), ([1] + [0]*(nsym+1)) ) 
    return remainder

def rs_find_errors(err_loc, nmess, generator=2):

    errs = len(err_loc) - 1
    err_pos = []
    for i in xrange(nmess): 
        if gf_poly_eval(err_loc, gf_pow(generator, i)) == 0: 
            err_pos.append(nmess - 1 - i)
    if len(err_pos) != errs:
        raise ReedSolomonError("Too many (or few) errors found by Chien Search for the errata locator polynomial!")
    return err_pos

def rs_forney_syndromes(synd, pos, nmess, generator=2):
 
    erase_pos_reversed = [nmess-1-p for p in pos] 

    fsynd = list(synd[1:])      
    for i in xrange(len(pos)):
        x = gf_pow(generator, erase_pos_reversed[i])
        for j in xrange(len(fsynd) - 1):
            fsynd[j] = gf_mul(fsynd[j], x) ^ fsynd[j + 1]

    return fsynd

def rs_correct_msg(msg_in, nsym, fcr=0, generator=2, erase_pos=None, only_erasures=False):
    '''Reed-Solomon main decoding function'''
    global field_charac
    if len(msg_in) > field_charac:
        raise ValueError("Message is too long (%i when max is %i)" % (len(msg_in), field_charac))

    msg_out = _bytearray(msg_in)    
    if erase_pos is None:
        erase_pos = []
    else:
        for e_pos in erase_pos:
            msg_out[e_pos] = 0
    if len(erase_pos) > nsym: raise ReedSolomonError("Too many erasures to correct")
    synd = rs_calc_syndromes(msg_out, nsym, fcr, generator)
    if max(synd) == 0:
        return msg_out[:-nsym], msg_out[-nsym:], []  # no errors

    if only_erasures:
        err_pos = []
    else:
        fsynd = rs_forney_syndromes(synd, erase_pos, len(msg_out), generator)
        err_loc = rs_find_error_locator(fsynd, nsym, erase_count=len(erase_pos))
        err_pos = rs_find_errors(err_loc[::-1], len(msg_out), generator)
        if err_pos is None:
            raise ReedSolomonError("Could not locate error")

    msg_out = rs_correct_errata(msg_out, synd, erase_pos + err_pos, fcr, generator) 
    synd = rs_calc_syndromes(msg_out, nsym, fcr, generator)
    if max(synd) > 0:
        raise ReedSolomonError("Could not correct message")
    return msg_out[:-nsym], msg_out[-nsym:], erase_pos + err_pos 

def rs_correct_msg_nofsynd(msg_in, nsym, fcr=0, generator=2, erase_pos=None, only_erasures=False):
    '''Reed-Solomon main decoding function, without using the modified Forney syndromes'''
    global field_charac
    if len(msg_in) > field_charac:
        raise ValueError("Message is too long (%i when max is %i)" % (len(msg_in), field_charac))

    msg_out = _bytearray(msg_in)     
    if erase_pos is None:
        erase_pos = []
    else:
        for e_pos in erase_pos:
            msg_out[e_pos] = 0

    if len(erase_pos) > nsym: raise ReedSolomonError("Too many erasures to correct")
 
    synd = rs_calc_syndromes(msg_out, nsym, fcr, generator)
    if max(synd) == 0:
        return msg_out[:-nsym], msg_out[-nsym:], []  # no errors

    erase_loc = None
    erase_count = 0
    if erase_pos:
        erase_count = len(erase_pos)
        erase_pos_reversed = [len(msg_out)-1-eras for eras in erase_pos]
        erase_loc = rs_find_errata_locator(erase_pos_reversed, generator=generator)

    if only_erasures:
        err_loc = erase_loc[::-1]
    else:
        err_loc = rs_find_error_locator(synd, nsym, erase_loc=erase_loc, erase_count=erase_count)
        err_loc = err_loc[::-1]

    err_pos = rs_find_errors(err_loc, len(msg_out), generator) 
    if err_pos is None:
        raise ReedSolomonError("Could not locate error")

    msg_out = rs_correct_errata(msg_out, synd, err_pos, fcr=fcr, generator=generator)
    synd = rs_calc_syndromes(msg_out, nsym, fcr, generator)
    if max(synd) > 0:
        raise ReedSolomonError("Could not correct message")
    return msg_out[:-nsym], msg_out[-nsym:], erase_pos + err_pos 

def rs_check(msg, nsym, fcr=0, generator=2):
    '''Returns true if the message + ecc has no error of false otherwise (may not always catch a wrong decoding or a wrong message, particularly if there are too many errors -- above the Singleton bound --, but it usually does)'''
    return ( max(rs_calc_syndromes(msg, nsym, fcr, generator)) == 0 )



class RSCodec(object):


    def __init__(self, nsym=10, nsize=255, fcr=0, prim=0x11d, generator=2, c_exp=8, single_gen=True):
 
        if nsize > 255 and c_exp <= 8:  
            c_exp = int(math.log(2 ** (math.floor(math.log(nsize) / math.log(2)) + 1), 2))
        if c_exp != 8 and prim == 0x11d:  
            prim = find_prime_polys(generator=generator, c_exp=c_exp, fast_primes=True, single=True)
            if nsize == 255: 
                nsize = int(2**c_exp - 1)

        self.nsym = nsym 
        self.nsize = nsize 
        self.fcr = fcr 
        self.prim = prim 
        self.generator = generator 
        self.c_exp = c_exp 

        self.gf_log, self.gf_exp, self.field_charac = init_tables(prim, generator, c_exp)
        if single_gen:
            self.gen = {}
            self.gen[nsym] = rs_generator_poly(nsym, fcr=fcr, generator=generator)
        else:
            self.gen = rs_generator_poly_all(nsize, fcr=fcr, generator=generator)

    def chunk(self, data, chunksize):
        '''Split a long message into chunks'''
        for i in xrange(0, len(data), chunksize):
            # Split the long message in a chunk
            chunk = data[i:i+chunksize]
            yield chunk

    def encode(self, data, nsym=None):
        global gf_log, gf_exp, field_charac
        gf_log, gf_exp, field_charac = self.gf_log, self.gf_exp, self.field_charac

        if not nsym:
            nsym = self.nsym

        if isinstance(data, str):
            data = _bytearray(data)
        enc = _bytearray()
        for chunk in self.chunk(data, self.nsize - self.nsym):
            enc.extend(rs_encode_msg(chunk, self.nsym, fcr=self.fcr, generator=self.generator, gen=self.gen[nsym]))
        return enc

    def decode(self, data, nsym=None, erase_pos=None, only_erasures=False):

        global gf_log, gf_exp, field_charac
        gf_log, gf_exp, field_charac = self.gf_log, self.gf_exp, self.field_charac

        if not nsym:
            nsym = self.nsym

        if isinstance(data, str):
            data = _bytearray(data)
        dec = _bytearray()
        dec_full = _bytearray()
        errata_pos_all = _bytearray()
        for chunk in self.chunk(data, self.nsize):
            # Extract the erasures for this chunk
            e_pos = []
            if erase_pos:
                e_pos = [x for x in erase_pos if x <= self.nsize]
                erase_pos = [x - (self.nsize+1) for x in erase_pos if x > self.nsize]
            rmes, recc, errata_pos = rs_correct_msg(chunk, nsym, fcr=self.fcr, generator=self.generator, erase_pos=e_pos, only_erasures=only_erasures)
            dec.extend(rmes)
            dec_full.extend(rmes+recc)
            errata_pos_all.extend(errata_pos)
        return dec, dec_full, errata_pos_all

def start_encode(x):
    rsc = RSCodec(10)
    encode = rsc.encode([x])
    print(encode)
    return encode

def start_decode(x):
    rsc = RSCodec(10)
    decode = rsc.decode(x)
    print(decode)
    return decode
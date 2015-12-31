'''
pymmh3 was written by Fredrik Kihlander, and is placed in the public
domain. The author hereby disclaims copyright to this source code.

pure python implementation of the murmur3 hash algorithm

https://code.google.com/p/smhasher/wiki/MurmurHash3

This was written for the times when you do not want to compile c-code and install modules,
and you only want a drop-in murmur3 implementation.

As this is purely python it is FAR from performant and if performance is anything that is needed
a proper c-module is suggested!

This module is written to have the same format as mmh3 python package found here for simple conversions:

https://pypi.python.org/pypi/mmh3/2.0 
'''

import sys

if (sys.version_info > (3, 0)):
    def xrange( a, b, c ):
        return range( a, b, c )


def hash( key, seed = 0x0 ):
    ''' implements 32bit murmur3 hash. '''

    key = bytearray( key )

    def fmix( h ):
        h ^= h >> 16
        h  = ( h * 0x85ebca6b ) & 0xFFFFFFFF
        h ^= h >> 13
        h  = ( h * 0xc2b2ae35 ) & 0xFFFFFFFF
        h ^= h >> 16
        return h;

    length = len( key )
    nblocks = int( length / 4 )

    h1 = seed;

    c1 = 0xcc9e2d51
    c2 = 0x1b873593

    # body
    for block_start in xrange( 0, nblocks * 4, 4 ):
        # ??? big endian?
        k1 = key[ block_start + 3 ] << 24 | \
             key[ block_start + 2 ] << 16 | \
             key[ block_start + 1 ] <<  8 | \
             key[ block_start + 0 ]
             
        k1 = c1 * k1 & 0xFFFFFFFF
        k1 = ( k1 << 15 | k1 >> 17 ) & 0xFFFFFFFF # inlined ROTL32
        k1 = ( c2 * k1 ) & 0xFFFFFFFF;
        
        h1 ^= k1
        h1  = ( h1 << 13 | h1 >> 19 ) & 0xFFFFFFFF # inlined _ROTL32 
        h1  = ( h1 * 5 + 0xe6546b64 ) & 0xFFFFFFFF

    # tail
    tail_index = nblocks * 4
    k1 = 0
    tail_size = length & 3

    if tail_size >= 3:
        k1 ^= key[ tail_index + 2 ] << 16
    if tail_size >= 2:
        k1 ^= key[ tail_index + 1 ] << 8
    if tail_size >= 1:
        k1 ^= key[ tail_index + 0 ]
    
    if tail_size != 0:
        k1  = ( k1 * c1 ) & 0xFFFFFFFF
        k1  = ( k1 << 15 | k1 >> 17 ) & 0xFFFFFFFF # _ROTL32
        k1  = ( k1 * c2 ) & 0xFFFFFFFF
        h1 ^= k1

    return fmix( h1 ^ length )


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser( 'pymurmur3', 'pymurmur [options] "string to hash"' )
    parser.add_argument( '--seed', type = int, default = 0 )
    parser.add_argument( 'strings', default = [], nargs='+')
    
    opts = parser.parse_args()
    
    for str_to_hash in opts.strings:
        sys.stdout.write( '"%s" = 0x%08X\n' % ( str_to_hash, hash( str_to_hash ) ) )

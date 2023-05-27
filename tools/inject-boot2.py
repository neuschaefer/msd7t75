#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
import argparse, lzma, struct
from construct import *

KiB = 1 << 10
MiB = 1 << 20

def compress_lzma(data):
    # Compress data in LZMA "alone" format, and manually patch the uncompressed-length field
    filters = [dict(id=lzma.FILTER_LZMA1, dict_size=1*MiB)]
    l = lzma.LZMACompressor(format=lzma.FORMAT_ALONE, filters=filters)
    out = l.compress(data)
    out += l.flush()
    out = bytearray(out)
    assert out[5:5+8] == 8*b'\xff'
    out[5:5+8] = struct.pack('<Q', len(data))
    return bytes(out)

Header = Struct(
    'unk0' / Hex(Int32ul),
    'unk4' / Hex(Int32ul),
    'comp_size' / Hex(Int32ul),
    'uncomp_size' / Hex(Int32ul),
)

def patch(args):
    with open(args.program, 'rb') as f:
        uncompressed = f.read()
        compressed = compress_lzma(uncompressed)
    print(f'Uncompressed size: {len(uncompressed):#x}')
    print(f'Compressed size:   {len(compressed):#x}')

    with open(args.image, 'rb+') as f:
        f.seek(0x20000)
        header = Header.build(dict(
            unk0 = 0x82000080,
            unk4 = 0x1a4,
            comp_size = len(compressed) + 0x100,
            uncomp_size = len(uncompressed) + 0x100,
        ))
        f.write(header)
        f.seek(0x20100)
        f.write(compressed + 0x100 * b'\xda')
        f.flush()

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Inject boot2 stage into a flash image')
    parser.add_argument('image', help='flash image')
    parser.add_argument('program', help='program to inject')
    args = parser.parse_args()
    patch(args)

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

def human_size(size):
    scale = 0
    while size > 1200:
        size /= 1024
        scale += 1
    b = ['B', 'KiB', 'MiB', 'GiB'][scale]
    return f'{round(size, 1)} {b}'

def inject(f, offset, program):
    with open(program, 'rb') as p:
        uncompressed = p.read()
        compressed = compress_lzma(uncompressed)
    print(f'Injecting {program} into {f.name} @ {offset:#x}: {human_size(len(uncompressed))} -> {human_size(len(compressed))}')

    f.seek(offset)
    header = Header.build(dict(
        unk0 = 0x82000080,
        unk4 = 0x1a4,
        comp_size = len(compressed) + 0x100,
        uncomp_size = len(uncompressed) + 0x100,
    ))
    f.write(header)
    f.seek(offset + 0x100)
    f.write(compressed + 0x100 * b'\xda')
    f.flush()

def patch(args):
    with open(args.image, 'rb+') as f:
        inject(f, 0x20000, args.main)
        if args.recovery:
            inject(f, 0x720000, args.recovery)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Inject boot2 stage into a flash image')
    parser.add_argument('image', help='flash image')
    parser.add_argument('main', help='program to inject (main @ 0x20100)')
    parser.add_argument('recovery', help='program to inject (recovery @ 0x720100)', nargs='?') # TODO
    args = parser.parse_args()
    patch(args)

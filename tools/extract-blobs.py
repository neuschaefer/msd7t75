#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
import argparse, hashlib, sys, os

class Blob:
    def __init__(self, offset, size, name):
        self.offset = offset
        self.size = size
        self.name = name

BASE = 0x80000180
BLOBS = {
    'f424ac2d2d4633f24f06c972500a9e5872831f511f70d597268c5f097ee9ddd9': [
        Blob(0x80d29620-BASE, 450400, 'vpu.bin'),
        Blob(0x8112fe88-BASE,   3072, 'msb124x-100.bin'),
        Blob(0x81138a88-BASE,  29696, 'msb124x-108.bin'),
        Blob(0x81130a88-BASE,  32768, 'msb124x-110.bin'),
        Blob(0x8113fe88-BASE,  32768, 'msb124x-118.bin'),
        Blob(0x81147e88-BASE,  32768, 'msb124x-120.bin'),
        Blob(0x81157e88-BASE,   4096, 'msb124x-128.bin'),
        Blob(0x8114fe88-BASE,  32768, 'msb124x-130.bin'),
        Blob(0x81127ec4-BASE,  32708, 'msb124x-80000.bin'),
        Blob(0x810ab828-BASE, 222576, 'audsp-base.bin'),
        Blob(0x80fcf3ac-BASE,  37073, 'audsp-algo3.bin'),
        Blob(0x8102d724-BASE, 497153, 'audsp-algo4.bin'),
        Blob(0x80fd8480-BASE, 195901, 'audsp-algo5.bin'),
        Blob(0x80f35300-BASE,  13714, 'audsp-algo7.bin'),
        Blob(0x80f29234-BASE,  49356, 'audsp-algo8.bin'),
        Blob(0x80f38894-BASE,  29033, 'audsp-algo9.bin'),
        Blob(0x80f49bb8-BASE, 367160, 'audsp-algo10.bin'),
        Blob(0x80f3fa00-BASE,  41400, 'audsp-algo12.bin'),
        Blob(0x80fb1bf0-BASE, 120762, 'audsp-algo13.bin'),
        Blob(0x810081c0-BASE, 152932, 'audsp-algo14.bin'),
        Blob(0x80fa35f0-BASE,  58878, 'audsp-algo16.bin'),
        Blob(0x81161544-BASE,  16488, 'pm51-1.bin'),
        Blob(0x8115d120-BASE,  17442, 'pm51-2.bin'),
    ]
}

def extract(args):
    os.makedirs(args.output, exist_ok=True)

    with open(args.file, 'rb') as f:
        data = f.read()
        sha256 = hashlib.sha256(data).digest().hex()

    if sha256 not in BLOBS:
        print(f'Unknown input file (SHA256 hash {sha256})')
        sys.exit(1)

    blobs = BLOBS[sha256]
    print(f'Found {len(blobs)} blobs.')

    for b in blobs:
        print(f'Extracting {b.offset:08x}:{b.size:08x} {b.name}.')
        with open(f'{args.output}/{b.name}', 'wb') as f:
            f.write(data[b.offset:b.offset+b.size])
            f.close()

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Extract blobs (peripheral firmware) from the Irdeto application image')
    parser.add_argument('file', help='application image file')
    parser.add_argument('--output', '-o', help='output directory', required=True)
    args = parser.parse_args()
    extract(args)

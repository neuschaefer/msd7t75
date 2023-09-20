#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
import argparse, lzma

def extract(args):
    with open(args.image, 'rb') as f:
        data = f.read()
    a = lzma.decompress(data[0x20100:])
    b = lzma.decompress(data[0x720100:])

    if not args.recovery and a != b:
        print('Warning: main and recovery copies of boot2 are different! Extracting main only.')

    with open(args.main, 'wb') as f:
        f.write(a)
        f.close()

    if args.recovery:
        with open(args.recovery, 'wb') as f:
            f.write(b)
            f.close()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Extract boot2')
    parser.add_argument('image', help='flash image')
    parser.add_argument('main', help='filename of resulting program (main @ 0x20100)')
    parser.add_argument('recovery', help='filename of resulting program (recovery @ 0x720100)', nargs='?')
    args = parser.parse_args()
    extract(args)

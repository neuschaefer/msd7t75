#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
import sys, argparse

def decode(args):
    if args.file:   i = open(args.file, 'rb')
    else:           i = sys.stdin.buffer.raw
    if args.output: o = open(args.output, 'wb')
    else:           o = sys.stdout.buffer.raw

    base = 0x80000180
    seen_command = False

    program = bytearray()
    for line in i:
        line = line.decode('ascii', errors='replace').strip()
        if seen_command:
            try:
                addr, data = line.split(':')
                addr = int(addr, 16)
            except:
                continue
            if addr < base:
                continue

            for i, x in enumerate(data.strip().split(' ')):
                a = addr + 4*i
                x = int(x, 16)
                program[a-base:a-base+4] = x.to_bytes(4, 'little')

        elif 'unOrgLen:' in line:
            length = int(line.split(':')[3].split('<')[0])
            program = bytearray(length)

        elif line.startswith('> rw'):
            seen_command = True

    o.write(program[:length])
    o.flush()

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Decode hexdump output from lolmon')
    parser.add_argument('file', help='hexdump file')
    parser.add_argument('--output', '-o', help='hexdump file')
    args = parser.parse_args()
    decode(args)

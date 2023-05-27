#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
import argparse

KiB = 1 << 10
MiB = 1 << 20

class MIPSASM:
    def __init__(self, buf, addr, offset = 0):
        self.addr = addr
        self.buf = buf
        self.offset = offset

    def advance(self, diff):
        self.addr += diff
        self.offset += diff

    def goto(self, addr):
        self.advance(addr - self.addr)

    def write32(self, value):
        self.buf[self.offset:self.offset+4] = value.to_bytes(4, 'little')
        self.advance(4)

    def j(self, target):
        index = (target & 0x0ffffffc) >> 2
        self.write32(0b000010 << 26 | index)

    def write(self, data):
        self.buf[self.offset:self.offset+len(data)] = data
        self.advance(len(data))


BASE = 0x82000180

def patch(args):
    with open(args.program, 'rb') as f: prog = f.read()
    with open(args.ecos, 'rb')    as f: ecos = bytearray(f.read())

    if hashlib.sha256(ecos).digest().hex() != 'd8320d6b8d4f209b20bd217f19c5c0efde5a0488c243adb6dee531ed37764d99':
        print('WARNING! eCos doesn\'t have the expected hash! You might run into problems.')

    #ecos += (16*MiB - len(ecos)) * b'\0'

    asm = MIPSASM(ecos, BASE)

    hideout = 0x822ba000
    asm.goto(hideout)
    asm.write(prog)

    asm.goto(0x82007280)
    asm.j(hideout)

    with open(args.ecos, 'wb') as f:
        f.write(ecos)
        f.flush()
        f.close()

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Patch eCos boot2 image to run custom code instead of jumping into the application')
    parser.add_argument('ecos', help='eCos program image')
    parser.add_argument('program', help='program to inject')
    args = parser.parse_args()
    patch(args)

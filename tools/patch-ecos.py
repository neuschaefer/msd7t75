#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
import argparse, hashlib
from enum import Enum

KiB = 1 << 10
MiB = 1 << 20

class MIPSASM:
    class Reg(Enum):  # from linux/arch/mips/include/asm/regdef.h
        zero=0; AT=1; v0=2; v1=3; a0=4; a1=5; a2=6; a3=7;
        t0=8; t1=9; t2=10; t3=11; t4=12; t5=13; t6=14; t7=15;
        s0=16; s1=17; s2=18; s3=19; s4=20; s5=21; s6=22; s7=23;
        t8=24; t9=25; jp=25; k0=26; k1=27; gp=28; sp=29; fp=30; ra=31;

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

    def addi(self, rt, rs, imm):
        assert imm == imm & 0xffff
        self.write32(0b001000 << 26 | rs.value << 21 | rt.value << 16 | imm)

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

    asm.goto(0x82263090) # otaTunerCallback
    asm.write(b'[%s] jn was here\n\0')
    asm.goto(0x8205e7b4) # don't return, jump to monitor
    asm.j(hideout)

    asm.goto(0x82052330) # after "Error: Signature verification failed!"
    asm.addi(asm.Reg.v0, asm.Reg.zero, 0) # ignore the error

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

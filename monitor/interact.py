#!/usr/share/python3
# SPDX-License-Identifier: MIT
# Usage: python3 -i ./interact.py

import serial, time, re, struct, sys, random, socket, os

KiB = 1 << 10
MiB = 1 << 20
GiB = 1 << 30

def BIT(x):
    return 1 << x

def MASK(x):
    return BIT(x) - 1

def bswap16(x):
    x = (x & 0xff00ff00) >>  8 | (x & 0x00ff00ff) <<  8
    return x

def bswap32(x):
    x = (x & 0xffff0000) >> 16 | (x & 0x0000ffff) << 16
    x = (x & 0xff00ff00) >>  8 | (x & 0x00ff00ff) <<  8
    return x

def get_be16(data, offset):
    return data[offset] << 8 | data[offset+1]

def get_be32(data, offset):
    return get_be16(data, offset) << 16 | get_be16(data, offset+2)

def to_be24(n):
    return [n >> 16 & 0xff, n >> 8 & 0xff, n & 0xff]

def to_be32(n):
    return [n >> 24 & 0xff, n >> 16 & 0xff, n >> 8 & 0xff, n & 0xff]

def from_be32(data):
    word = 0
    for i, b in enumerate(data[:4]):
        word |= b << (3 - i) * 8
    return word

def to_le32(n):
    return [n & 0xff, n >> 8 & 0xff, n >> 16 & 0xff, n >> 24 & 0xff]

def from_le32(data):
    word = 0
    for i, b in enumerate(data[:4]):
        word |= b << i * 8
    return word

def hexdump(data):
    if data:
        for offset in range(0, len(data), 16):
            d = data[offset:offset+16]
            line = f'{offset:08x}:  '
            line += ' '.join([f'{x:02x}' for x in d]).ljust(49)
            line += ''.join([chr(x) if (x >= 0x20 and x <= 0x7f) else '.' for x in d])
            print(line)


def error(s):
    sys.stderr.write(s)
    sys.stderr.write('\n')
    sys.stderr.flush()

class Lolmon:
    def __init__(self, device):
        self.device = device
        self.s = serial.Serial(device, baudrate=115200, timeout=0.2)
        self.prompt = b'> '
        self.debug = 0
        self.echo_attempts = 3
        self.chunksize = 0x38

    def connection_test(self):
        self.s.write(b'\n')
        time.sleep(0.2)
        answer = self.s.read_all()
        if (b'\r\n' + self.prompt) in answer:
            print("lolmon detected!")

    def debug_log(self, prefix, s):
        if self.debug >= 2:
            error(f'{prefix}: {s}')
        return s

    def read_until_prompt(self):
        answer = bytearray()
        timeout = 1
        while True:
            if self.s.readable():
                answer += self.debug_log('until prompt', self.s.read_all())
                if self.prompt in answer:
                    return bytes(answer)[:-len(self.prompt)], True
            else:
                time.sleep(0.05)
                timeout -= 0.05

            if timeout < 0:
                return bytes(answer), False

    def flush(self):
        while self.debug_log('flush', self.s.read_all()) != b'':
            time.sleep(0.05)
        self.run_command('')

    def enter_with_echo(self, cmd, chunksize):
        if isinstance(cmd, str):
            cmd = cmd.encode('UTF-8')
        assert not b'\n' in cmd

        pos = 0
        while pos < len(cmd):
            chunk = cmd[pos:pos+chunksize]
            assert len(chunk) >= 1
            self.s.write(chunk)
            echo = self.s.read(len(chunk))
            if self.debug >= 2:
                error(f'input {chunk} -> {echo}')
            if echo != chunk:
                error(f'Echo error! {chunk} -> {echo}')
                error((echo + self.s.read_all()).decode('ascii'))
                return False
            pos += len(chunk)
        return True

    def run_command(self, cmd):
        try:
            chunksize = self.chunksize
            for _ in range(self.echo_attempts):
                if self.debug:
                    error(':> %s' % cmd)
                good = self.enter_with_echo(cmd, chunksize)
                if not good:
                    # Clear the prompt (send Ctrl-U)
                    self.s.write(b'\025')
                    time.sleep(0.01)
                    while self.s.read_all() != b'':
                        time.sleep(0.01)
                    # ... and retry
                    chunksize = 1
                    continue

                self.s.write(b'\n')
                assert self.s.read(2) == b'\r\n'

                answer, good = self.read_until_prompt()
                if not good:
                    error('Command \'%s\' timed out:\n%s' % (cmd, answer.decode('UTF-8')))
                    return b''
                return answer
            return b''
        except KeyboardInterrupt as e:
            time.sleep(0.10)
            self.flush()
            raise e

    def run_command_noreturn(self, cmd):
        if self.debug:
            error(':> %s' % cmd)
        self.enter_with_echo(cmd, self.chunksize)
        self.s.write(b'\n')
        #assert self.s.read(2) == b'\r\n'
        self.s.read(2)

    def writeX(self, cmd, size, addr, value):
        #print('poke %s %08x %s' % (cmd, addr, value))
        if isinstance(value, bytes):
            value = [x for x in value]
        if hasattr(value, '__iter__'):
            value = list(value)
        if isinstance(value, list):
            v = value
            while len(v) > 0:
                line = f'{cmd} {addr:x}'; i = 0
                while i < 14 and i < len(v) and len(line + f' {v[i]}') <= 128:
                    line += f' {v[i]}'
                    i += 1
                self.run_command(line)
                v = v[i:]
                addr += i * size
        else:
            self.run_command("%s %08x %#x" % (cmd, addr, value))

    def write8(self, addr, value):  return self.writeX('wb', 1, addr, value)
    def write16(self, addr, value): return self.writeX('wh', 2, addr, value)
    def write32(self, addr, value): return self.writeX('ww', 4, addr, value)

    def write_file(self, addr, filename):
        with open(filename, 'rb') as f:
            data = f.read()
            f.close()
            self.write8(addr, data)

    def flash(self, memaddr, flashaddr, size):
        self.run_command("fl %08x %08x %#x" % (memaddr, flashaddr, size))

    def memset(self, addr, value, size):
        value16 = value << 8 | value
        value32 = value16 << 16 | value16
        while size > 0:
            if addr & 3 != 0 or size < 4:
                n = size & 3 or 1
                self.write8(addr, [value] * n)
                addr += n
                size -= n
            else:
                n = size // 4
                self.write32(addr, [value32] * n)
                addr += n * 4
                size -= n * 4

    def parse_r_output(self, s):
        array = []
        s = s.decode('UTF-8')
        for line in s.splitlines():
            if re.match('[0-9a-f]{8}: [0-9a-f]+', line):
                for n in line[10:].split(' '):
                    array.append(int(n, base=16))
        return array


    def readX(self, cmd, size, addr, num):
        output = self.run_command("%s %08x %d" % (cmd, addr, num))
        a = self.parse_r_output(output)
        if num == 1:  return a[0]
        elif size==1: return bytes(a)
        else:         return a

    def read8(self, addr, num=1):  return self.readX('rb', 1, addr, num)
    def read16(self, addr, num=1): return self.readX('rh', 2, addr, num)
    def read32(self, addr, num=1): return self.readX('rw', 4, addr, num)

    def copyX(self, cmd, dest, src, num):
        self.run_command("%s %08x %08x %d" % (cmd, src, dest, num))

    def copy8(self, dest, src, num):  self.copyX('cb', dest, src, num)
    def copy16(self, dest, src, num): self.copyX('ch', dest, src, num)
    def copy32(self, dest, src, num): self.copyX('cw', dest, src, num)

    def make_setclr(rd, wr):
        def fn(self, addr, bit, value):
            x = rd(self, addr)
            if value: wr(self, addr, x |  (1 << bit))
            else:     wr(self, addr, x & ~(1 << bit))
        return fn

    setclr8 = make_setclr(read8, write8)
    setclr16 = make_setclr(read16, write16)
    setclr32 = make_setclr(read32, write32)

    def make_dump(cmd):
        def fn(self, addr, length):
            res = self.run_command('%s %08x %d' % (cmd, addr, length))
            print(res.decode('ascii').strip())
        return fn

    dump8 = make_dump('rb')
    dump16 = make_dump('rh')
    dump32 = make_dump('rw')

    # Special read/write methods are provided to deal with RIU's weirdness:
    # - Offset 2*n   -> 4*n
    # - Offset 2*n+1 -> 4*n+1

    @staticmethod
    def riu_addr(offset):
        assert offset < 0x200000
        one = offset & 1
        return 0xbf000000 + (offset // 2) * 4 + one

    def riu_read8(self, offset):  return self.read8 (self.riu_addr(offset))
    def riu_read16(self, offset): return self.read16(self.riu_addr(offset))
    def riu_read32(self, offset):
        lo = self.read16(self.riu_addr(offset))
        hi = self.read16(self.riu_addr(offset + 2))
        return lo | (hi << 16)

    def riu_write8(self, offset, value):  return self.write8 (self.riu_addr(offset), value)
    def riu_write16(self, offset, value): return self.write16(self.riu_addr(offset), value)
    def riu_write32(self, offset, value):
        self.write16(self.riu_addr(offset + 0), (value >>  0) & 0xffff)
        self.write16(self.riu_addr(offset + 2), (value >> 16) & 0xffff)


    def call(self, addr, a=0, b=0, c=0, d=0):
        self.run_command_noreturn('call %x %d %d %d %d' % (addr, a, b, c, d))

    def call_linux_and_run_microcom(self, addr):
        self.call(addr, 0, 0xffffffff, 0)
        os.system(f'busybox microcom -s {self.s.baudrate} /dev/ttyUSB0')

class Block:
    def __init__(self, lolmon, base=None):
        self.l = lolmon
        if base:
            self.base = base
            if base in range(0xbf000000, 0xc0000000):
                self.riu_base = (base - 0xbf000000) // 2

    def read8(self, offset): return self.l.read8(self.base + offset)
    def read16(self, offset): return self.l.read16(self.base + offset)
    def read32(self, offset): return self.l.read32(self.base + offset)

    def write8(self, offset, value): return self.l.write8(self.base + offset, value)
    def write16(self, offset, value): return self.l.write16(self.base + offset, value)
    def write32(self, offset, value): return self.l.write32(self.base + offset, value)

    def setclr8(self, offset, bit, value): return self.l.setclr8(self.base + offset, bit, value)
    def setclr16(self, offset, bit, value): return self.l.setclr16(self.base + offset, bit, value)
    def setclr32(self, offset, bit, value): return self.l.setclr32(self.base + offset, bit, value)

    def dump(self):
        self.l.dump32(self.base, 0x40)

    def riu_read8(self, offset): return self.l.riu_read8(self.riu_base + offset)
    def riu_read16(self, offset): return self.l.riu_read16(self.riu_base + offset)
    def riu_read32(self, offset): return self.l.riu_read32(self.riu_base + offset)

    def riu_write8(self, offset, value): return self.l.riu_write8(self.riu_base + offset, value)
    def riu_write16(self, offset, value): return self.l.riu_write16(self.riu_base + offset, value)
    def riu_write32(self, offset, value): return self.l.riu_write32(self.riu_base + offset, value)


class EMAC(Block):
    CTL = 0x00  # offsets are in RIU notation
    CFG = 0x04
    SR  = 0x08
    TAR = 0x0c
    TCR = 0x10
    TSR = 0x14
    RBQP= 0x18
    TBQP= 0x1c
    RSR = 0x20
    ISR = 0x24
    IER = 0x28
    IDR = 0x2c
    IMR = 0x30

    CTL_LB  = BIT(0)
    CTL_LBL = BIT(1)
    CTL_RE  = BIT(2)
    CTL_TE  = BIT(3)
    CTL_MPE = BIT(4)
    CTL_CSR = BIT(5)
    CTL_ISR = BIT(6)
    CTL_WES = BIT(7)
    CTL_BP  = BIT(8)

    def read_macaddr(self, offset):
        lo = self.riu_read32(offset)
        hi = self.riu_read32(offset + 4)
        return f'{lo:x}{hi:x}'

    def init(self):
        self.mystery_init_sequence()
        self.riu_write32(0x100, 0xf051)
        self.riu_read32(self.CTL)
        self.riu_write32(self.CTL, 0)

        self.riu_write32(self.RBQP, 1 * MiB)
        self.riu_write32(self.TBQP, 2 * MiB)

        self.riu_write32(0x108, 0)
        self.riu_write32(0x104, 0x04020081)
        self.riu_write32(self.IER, 0x437)
        self.riu_write32(0x104, 1)
        print(f'int mask: {self.riu_read32(self.IMR):x}')
        print(f'mac1: {self.read_macaddr(0x98)}')

        self.riu_write32(self.CFG, 0x803)

        self.riu_write32(self.CTL, 0x1c)  # MDIO on

        self.enable()
        ephy.check()


    def enable(self):
        ctl = self.riu_read32(self.CTL)
        self.riu_write32(self.CTL, ctl | self.CTL_TE | self.CTL_MPE)
        self.riu_write32(self.CFG, self.riu_read32(self.CFG) | 3)

    def tx_one_frame(self, addr, size):
        self.riu_write32(self.TAR, addr & 0x03ffffff)
        self.riu_write32(self.TCR, size)

    @staticmethod
    def mystery_init_sequence():
        """
        A series of magic writes that successfully brings the Ethernet link up.
        Ripped from vendor firmware, but it's a series of uncopyrightable facts. ;)
        """
        uVar1 = l.riu_read8(0x121f60);
        l.riu_write8(0x121f60,uVar1 & 0xfc | 2);
        l.riu_write8(0x103364,0x10);
        l.riu_write8(0x121f23,8);
        l.riu_write8(0x121f24,8);
        l.riu_write8(0x121f25,0);
        uVar1 = l.riu_read8(0xe60);
        l.riu_write8(0xe60,uVar1 & 0xfe);
        l.riu_write8(0x324f,2);
        l.riu_write8(0x3251,1);
        l.riu_write8(0x3277,0x18);
        l.riu_write8(0x3172,0x80);
        l.riu_write8(0x32fc,0);
        l.riu_write8(0x32fd,0);
        l.riu_write8(0x32b7,7);
        l.riu_write8(0x32cb,0x11);
        l.riu_write8(0x32cc,0x80);
        l.riu_write8(0x32cd,0xd1);
        l.riu_write8(0x32d4,0);
        l.riu_write8(0x32b9,0x40);
        l.riu_write8(0x32bb,5);
        l.riu_write8(0x32ea,0x46);
        l.riu_write8(0x33a1,0);
        l.riu_write8(0x333a,3);
        l.riu_write8(0x333b,0);
        l.riu_write8(0x33c5,0);
        l.riu_write8(0x3330,0x43);
        l.riu_write8(0x3339,0x41);
        l.riu_write8(0x33e8,6);
        l.riu_write8(0x312b,0);
        l.riu_write8(0x33e8,0);
        l.riu_write8(0x312b,0);
        l.riu_write8(0x33e8,6);
        l.riu_write8(0x31aa,0x1c);
        l.riu_write8(0x31ac,0x1c);
        l.riu_write8(0x31ad,0x1c);
        l.riu_write8(0x31ae,0x1c);
        l.riu_write8(0x31af,0x1c);
        l.riu_write8(0x33e8,0);
        l.riu_write8(0x33e8,0);
        l.riu_write8(0x31ab,0x28);

class EPHY(Block):
    # MDIO read/write
    def read(self, offset):
        self.write16(4, self.read16(4) | 4)
        return self.read16(4 * offset)

    def write(self, offset, value):
        self.write16(4 * offset, value)

    def dump(self):
        for j in range(0, 32, 8):
            print('  '.join([hex(ephy.read(j+i)).rjust(6, ' ') for i in range(8)]))

    def check(self):
        self.write(0, 0x2100)
        self.write(4, 0x1e1)
        self.write(0, 0x1200)
        time.sleep(2)
        self.link()

    def link(self):
        print(f'link? {ephy.read(1) & 4}')

class Pinmux(Block):
    # RIU offset 2
    #   - set 0x3000 -> breaks uart
    #   - 0xe00 -> can be set, doesn't matter
    # RIU offset 6
    #   - 0x8000 -> breaks uart
    #   - 0x333  -> can be set
    # RIU offset 0xa6
    #   - 0xfff0 -> ok
    #   - 0xf -> writing anything but 0x4 breaks uart
    def dump(self):
        l.dump16(self.base, 0x100)


UART = Block

l = Lolmon('/dev/ttyUSB0')
l.connection_test()
pinmux = Pinmux(l, 0xbf203c00)
uart0 = UART(l, 0xbf201300)
emac = EMAC(l, 0xbf243600)
ephy = EPHY(l, 0xbf006200)

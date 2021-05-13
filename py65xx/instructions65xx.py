# -*- coding: utf-8 -*-
# Copyright (C) 2021  Jyrki Launonen

from __future__ import annotations

import typing
if typing.TYPE_CHECKING:
    from .cpu65xx import CPU

from .statelog import LOG
from .bcd import bcdtoi, itobcd

# Should JMP and B* instructions check for self-jump, which would stuck the CPU (until IQR/NMI)?
CHECK_STUCK = True


def _data_or_read(self: CPU):
    if self.data_val is not None:
        # Immediate, etc.
        return self.data_val
    # Addressed.
    self.clock.wait_cycle()
    return self.bus.read(self.addr_val)


# region General

def fault(self: CPU):
    self.fault_log(f"Faulty code at ${self.pc - 1:04X}: ${self.cmd_val:02X}")
    raise StopIteration


def jam(self: CPU):
    self.bus.read(self.pc)
    print(f"Jam by ${self.cmd_val:02X}")
    if self.cmd_val == 0x02:
        self.fault_log("")
    raise StopIteration


def nop(self: CPU):
    pass

# endregion


# region Load, store and transfer

def lda(self: CPU):
    self.A = _data_or_read(self)
    self.p.update_by_value(self.A)

def ldx(self: CPU):
    self.X = _data_or_read(self)
    self.p.update_by_value(self.X)

def ldy(self: CPU):
    self.Y = _data_or_read(self)
    self.p.update_by_value(self.Y)

def sta(self: CPU):
    self.bus.write(self.addr_val, self.A)
    self.clock.wait_cycle()

def stx(self: CPU):
    self.bus.write(self.addr_val, self.X)
    self.clock.wait_cycle()

def sty(self: CPU):
    self.bus.write(self.addr_val, self.Y)
    self.clock.wait_cycle()

def _set_a(self: CPU, v):
    self.A = v
    self.p.update_by_value(v)

def _set_x(self: CPU, v):
    self.X = v
    self.p.update_by_value(v)

def _set_y(self: CPU, v):
    self.Y = v
    self.p.update_by_value(v)

def tax(self: CPU):
    _set_x(self, self.A)

def txa(self: CPU):
    _set_a(self, self.X)

def tay(self: CPU):
    _set_y(self, self.A)

def tya(self: CPU):
    _set_a(self, self.Y)

def tsx(self: CPU):
    _set_x(self, self.sp)

def txs(self: CPU):
    self.sp = self.X

# endregion


# region Arithmetics

def inx(self: CPU):
    v = self.X + 1
    if v > 0xff:
        v -= 0x100
    self.X = v
    self.clock.wait_cycle()
    self.p.update_by_value(self.X)

def iny(self: CPU):
    v = self.Y + 1
    if v > 0xff:
        v -= 0x100
    self.Y = v
    self.clock.wait_cycle()
    self.p.update_by_value(self.Y)

def inc(self: CPU):
    v = self.bus.read(self.addr_val) + 1
    if v > 0xff:
        v -= 0x100
    self.bus.write(self.addr_val, v)
    self.p.update_by_value(v)

def dex(self: CPU):
    v = self.X - 1
    if v < 0:
        v += 0x100
    self.X = v
    self.clock.wait_cycle()
    self.p.update_by_value(self.X)

def dey(self: CPU):
    v = self.Y - 1
    if v < 0:
        v += 0x100
    self.Y = v
    self.clock.wait_cycle()
    self.p.update_by_value(self.Y)

def dec(self: CPU):
    v = self.bus.read(self.addr_val) - 1
    if v < 0:
        v += 0x100
    self.bus.write(self.addr_val, v)
    self.p.update_by_value(v)

def adc(self: CPU):
    """
    1, 2: Input signs
    m: Output sign
    V: Expected overflow value

    1 2 m V 1^2 !1^2 1^m !(1^2)&(1^m)
    -------
    0 0 0 0 0   1    0    0
    0 0 1 1 0   1    1    1
    0 1 0 0 1   0    -    0
    0 1 1 0 1   0    -    0
    1 0 0 0 1   0    -    0
    1 0 1 0 1   0    -    0
    1 1 0 1 0   1    1    1
    1 1 1 0 0   1    0    0
    """
    a = self.A
    b = _data_or_read(self)
    if self.p.D:
        a = bcdtoi(a)
        b = bcdtoi(b)

    m = a + b
    v = ((a & 0x80) ^ (b & 0x80))
    if self.p.C:
        m += 1

    if self.p.D:
        self.p.C = m > 99
        # Masking in itobcd.
    else:
        self.p.C = m > 0xff
        m &= 0xff

    self.p.V = not v and ((a & 0x80) ^ (m & 0x80))
    if self.p.D:
        m = itobcd(m)
    self.p.update_by_value(m)
    self.A = m

def sbc(self: CPU):
    """
    1, 2: Input signs
    m: Output sign
    V: Expected overflow value

    1 2 m V 1^2 1^m (1^2)&(1^m)
    -------
    0 0 0 0 0   -   0
    0 0 1 0 0   -   0
    0 1 0 0 1   0   0
    0 1 1 1 1   1   1
    1 0 0 1 1   1   1
    1 0 1 0 1   0   0
    1 1 0 0 0   -   0
    1 1 1 0 0   -   0
    """
    a = self.A
    b = _data_or_read(self)
    if self.p.D:
        a = bcdtoi(a)
        b = bcdtoi(b)

    m = a - b
    v = ((a & 0x80) ^ (b & 0x80))
    if not self.p.C:
        m -= 1
        self.p.C = True
    if m < 0:
        if self.p.D:
            # 0xff mask does bad things for negatives in decimal mode.
            m += 100
        self.p.C = False
    m &= 0xff
    self.p.V = v and ((a & 0x80) ^ (m & 0x80))
    if self.p.D:
        m = itobcd(m)
    self.p.update_by_value(m)
    self.A = m

# endregion


# region Subroutines and IRQs

def jsr(self: CPU):
    # XXX: So, we save return address which points to middle of this instruction.
    # This is the way. It is adjusted back in rts.
    ra = self.pc - 1
    self.bus.write(self.stc + self.sp - 1, ra & 0xff)
    self.clock.wait_cycle()
    self.bus.write(self.stc + self.sp, ra >> 8)
    self.clock.wait_cycle()
    self.sp -= 2
    self.pc = self.addr_val
    self.clock.wait_cycle()
    self.print_stack()

def rts(self: CPU):
    self.clock.wait_cycle()
    self.clock.wait_cycle()
    pch = self.bus.read(self.stc + self.sp + 2)
    self.clock.wait_cycle()
    pcl = self.bus.read(self.stc + self.sp + 1)
    self.clock.wait_cycle()
    self.sp += 2
    self.pc = (pch << 8) + pcl + 1
    self.clock.wait_cycle()
    self.print_stack()


def _prepare_irq(self: CPU, isr: int):
    ra = self.pc
    _push(self, ra >> 8)
    _push(self, ra & 0xff)
    _push(self, self.p.val)
    self.pc = isr
    self.p.I = True

def irq(self: CPU, is_brk: bool):
    isr = self.bus.read(0xfffe) | self.bus.read(0xffff) << 8
    self.p.B = is_brk
    _prepare_irq(self, isr)
    self.irq |= 0x80

def nmi(self: CPU):
    isr = self.bus.read(0xfffa) | self.bus.read(0xfffb) << 8
    _prepare_irq(self, isr)
    self.irq |= 0x80

def rti(self: CPU):
    self.p.load(_pop(self))
    pcl = _pop(self)
    pch = _pop(self)
    self.pc = (pch << 8) + pcl
    self.irq = 0


def brk(self: CPU):
    print("<BRK>")
    self.pc += 1  # why tho? and because of that, a nop is needed after this in program.
    self.irq = self.IRQ.BRK

# endregion


# region Processor state

def clc(self: CPU):
    self.p.C = False

def sec(self: CPU):
    self.p.C = True

def cld(self: CPU):
    self.p.D = False

def sed(self: CPU):
    self.p.D = True

def cli(self: CPU):
    self.p.I = False

def sei(self: CPU):
    self.p.I = True

def clv(self: CPU):
    self.p.V = False

# endregion



# region Comparison and 'bit'

def cmp(self: CPU):
    m = _data_or_read(self)
    v = self.A - m
    self.p.update_by_value(v)
    self.p.C = self.A >= m

def bit(self: CPU):
    m = _data_or_read(self)
    v = self.A & m
    self.p.Z = v == 0
    self.p.N = m & 0x80
    self.p.V = m & 0x40


def cpx(self: CPU):
    m = _data_or_read(self)
    v = self.X - m
    self.p.update_by_value(v)
    self.p.C = self.X >= m

def cpy(self: CPU):
    m = _data_or_read(self)
    v = self.Y - m
    self.p.update_by_value(v)
    self.p.C = self.Y >= m

# endregion


# region Branching

def _chk_jump(self: CPU):
    self.pc = self.addr_val

    if CHECK_STUCK and self.addr_val == self.spc:
        if not LOG.dis:
            self.fault_log("<stuck>")
        else:
            LOG.print("<stuck>")
        raise StopIteration

def jmp(self: CPU):
    _chk_jump(self)

def bcs(self: CPU):
    if self.p.C:
        _chk_jump(self)

def bcc(self: CPU):
    if not self.p.C:
        _chk_jump(self)

def beq(self: CPU):
    if self.p.Z:
        _chk_jump(self)

def bne(self: CPU):
    if not self.p.Z:
        _chk_jump(self)

def bpl(self: CPU):
    if not self.p.N:
        _chk_jump(self)

def bmi(self: CPU):
    if self.p.N:
        _chk_jump(self)

def bvc(self: CPU):
    if not self.p.V:
        _chk_jump(self)

def bvs(self: CPU):
    if self.p.V:
        _chk_jump(self)

# endregion


# region Bit operations

def asl(self: CPU):
    # Can access a registers directly.
    v = _data_or_read(self)
    self.p.C = v & 0x80
    v = (v << 1) & 0xff
    self.save(self, v)
    self.p.update_by_value(v)

def lsr(self: CPU):
    # Can access a registers directly.
    v = _data_or_read(self)
    self.p.C = v & 1
    v = v >> 1
    self.save(self, v)
    self.p.update_by_value(v)


def rol(self: CPU):
    # Can access a registers directly.
    v = _data_or_read(self)
    n = int(self.p.C)
    self.p.C = v & 0x80
    v = ((v << 1) + n) & 0xff
    self.save(self, v)
    self.p.update_by_value(v)

def ror(self: CPU):
    # Can access a registers directly.
    v = _data_or_read(self)
    n = int(self.p.C) * 0x80
    self.p.C = v & 1
    v = (v >> 1) + n
    self.save(self, v)
    self.p.update_by_value(v)


def iand(self: CPU):
    self.A = _data_or_read(self) & self.A
    self.p.update_by_value(self.A)
iand.__name__ = "and"

def ora(self: CPU):
    self.A = _data_or_read(self) | self.A
    self.p.update_by_value(self.A)

def eor(self: CPU):
    self.A = _data_or_read(self) ^ self.A
    self.p.update_by_value(self.A)

# endregion


# region Stack operations

def _push(self: CPU, val: int):
    self.bus.write(self.stc + self.sp, val)
    self.sp -= 1
    if self.sp < 0:
        self.sp = 0xff
    self.print_stack()

def _pop(self: CPU) -> int:
    self.sp += 1
    if self.sp > 0xff:
        self.sp = 0
    self.print_stack()
    return self.bus.read(self.stc + self.sp)

def php(self: CPU):
    _push(self, self.p.val)

def plp(self: CPU):
    self.p.load(_pop(self))
    self.p.B = self.irq == 0

def pha(self: CPU):
    _push(self, self.A)

def pla(self: CPU):
    self.A = _pop(self)
    self.p.update_by_value(self.A)

# endregion

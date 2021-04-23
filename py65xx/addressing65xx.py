# -*- coding: utf-8 -*-
# Copyright (C) 2021  Jyrki Launonen

from __future__ import annotations

import typing
if typing.TYPE_CHECKING:
    from .cpu65xx import CPU


def afault(self: CPU):
    pass
afault.dis = lambda x: ""


def _save_on_addr(self: CPU, val):
    self.bus.write(self.addr_val, val)


def aabs(self: CPU):
    addr = self.bus.read(self.pc)
    self.pc += 1
    self.clock.wait_cycle()
    addr |= self.bus.read(self.pc) << 8
    self.pc += 1
    self.clock.wait_cycle()
    self.addr_val = addr
    return _save_on_addr
aabs.dis = lambda x: f"${x}"


def aabsx(self: CPU):
    aabs(self)
    self.addr_val += self.X
    return _save_on_addr
aabsx.dis = lambda x: f"${x},X"


def aabsy(self: CPU):
    aabs(self)
    self.addr_val += self.Y
    return _save_on_addr
aabsy.dis = lambda x: f"${x},Y"


def aimm(self: CPU):
    self.data_val = self.bus.read(self.pc)
    self.addr_val = None
    self.pc += 1
    self.clock.wait_cycle()
aimm.dis = lambda x: f"#${x}"


def aimpl(self: CPU):
    pass
aimpl.dis = lambda x: ""


def _save_a(self: CPU, val):
    self.A = val


def aacc(self: CPU):
    self.data_val = self.A
    self.addr_val = None
    return _save_a
aacc.dis = lambda x: "A"


def aind(self: CPU):
    addr = self.bus.read(self.pc) | self.bus.read(self.pc + 1) << 8
    self.pc += 2
    self.addr_val = self.bus.read(addr) | self.bus.read(addr + 1) << 8
    return _save_on_addr
aind.dis = lambda x: f"${x},IND"


def aindx(self: CPU):
    base = self.bus.read(self.pc) + self.X
    self.pc += 1
    self.clock.wait_cycle()
    if base > 0xff:
        base -= 0x100
    self.addr_val = self.bus.read(base) | self.bus.read(base + 1) << 8
    self.clock.wait_cycle()
    self.clock.wait_cycle()
    return _save_on_addr
aindx.dis = lambda x: f"(${x},X)"


def aindy(self: CPU):
    zoff = self.bus.read(self.pc)
    self.pc += 1
    off = self.bus.read(zoff) + self.Y
    hb = self.bus.read(zoff + 1)
    if off > 0xff:
        hb += 1
        off -= 0x100
    # self.addr_val = self.bus.read(off)
    self.addr_val = off | hb << 8
    self.clock.wait_cycle()
    self.clock.wait_cycle()
    return _save_on_addr
aindy.dis = lambda x: f"(${x}),Y"


def _cpl(v: int) -> int:
    """
    >>> _cpl(1)
    1
    >>> _cpl(0)
    0
    >>> _cpl(0x7f)
    127
    >>> _cpl(0x80)
    -128
    >>> _cpl(0xff)
    -1
    """
    if v >= 0x80:
        return -((~v) & 0xff) - 1
    return v


def arel(self: CPU):
    rel = self.bus.read(self.pc)
    self.pc += 1

    rel = _cpl(rel)
    self.addr_val = self.pc + rel
    return _save_on_addr
arel.dis = lambda x: f"PC{_cpl(int(x, 16)):+}"


def azero(self: CPU):
    offset = self.bus.read(self.pc)
    self.pc += 1
    self.addr_val = offset
    return _save_on_addr
azero.dis = lambda x: f"${x},Z"

def azerox(self: CPU):
    offset = self.bus.read(self.pc)
    self.pc += 1
    self.addr_val = (offset + self.X) & 0xff
    return _save_on_addr
azerox.dis = lambda x: f"${x},ZX"

def azeroy(self: CPU):
    offset = self.bus.read(self.pc)
    self.pc += 1
    self.addr_val = (offset + self.Y) & 0xff
    return _save_on_addr
azeroy.dis = lambda x: f"${x},ZY"

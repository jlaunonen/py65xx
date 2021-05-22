# -*- coding: utf-8 -*-
# Copyright (C) 2021  Jyrki Launonen

from __future__ import annotations

import typing

if typing.TYPE_CHECKING:
    from py65xx.bus import Bus

from py65xx.defs import BusPart, BusRet, TAddr, TData


class PLA(BusPart):
    LORAM = 1  # A000-BFFF / Basic
    HIRAM = 1 << 1  # E000-FFFF / Kernal
    CHAREN = 1 << 2  # D000-DFFF / Chargen
    CAS_D_OUT = 1 << 3
    CAS_SW_SENSE_BIT = 4  # 1=sw closed
    CAS_MOTOR_CTL_BIT = 5  # 0=on, 1=off

    def __init__(self, bus: Bus):
        self.ddr = 0b00101111
        self.val = 0b00110111
        self._bus = bus
        self.i_basic = None
        self.i_chargen = None
        self.i_kernal = None
        self.i_io = None
        self.datassette = None

    def reset(self):
        # 1=output, 0=input
        self.ddr = 0b00101111
        self.val = 0b00110111
        self._update_peripherals()

    def read_address(self, addr: TAddr) -> BusRet:
        if addr == 0:
            return self.ddr
        elif addr == 1:
            d = 0
            if self.datassette is not None:
                d = self.datassette.sw_sense << self.CAS_SW_SENSE_BIT
            return d | self.val

    def write_address(self, addr: TAddr, data: TData):
        if addr == 0:
            self.ddr = data
        elif addr == 1:

            self.val = ((data & self.ddr) | (self.val & ~self.ddr)) & 0xFF
            self._update_peripherals()

    def set_map(self, basic, kernal, charen):
        self.val = (
            (self.val & ~0x7)
            | (int(basic) << self.LORAM)
            | (int(kernal) << self.HIRAM)
            | (int(charen) << self.CHAREN)
        )
        self._update_peripherals()

    def _update_peripherals(self):
        # LORAM enabled only if HIRAM is also enabled.
        self._set(self.i_basic, self.LORAM | self.HIRAM, self.LORAM | self.HIRAM)

        if self.val & self.CHAREN:
            # For I/O charegen is always disabled.
            self._set(self.i_chargen, 0, 1)
            # I/O is disabled if neither LORAM or HIRAM is enabled.
            self._set_if_any(self.i_io, self.LORAM | self.HIRAM)
        else:
            # CHARGEN is enabled if LORAM or HIRAM is enabled.
            # i.e. Disabled if neither is set.
            self._set_if_any(self.i_chargen, self.LORAM | self.HIRAM)
            self._set(self.i_io, 0, 1)

        self._set_if_any(self.i_kernal, self.HIRAM)

    def _set(self, index: typing.Optional[int], mask: int, val: int = 0):
        if index is not None:
            self._bus.set_enabled(index, self.val & mask == val)

    def _set_if_any(self, index: typing.Optional[int], mask: int):
        if index is not None:
            self._bus.set_enabled(index, self.val & mask > 0)

    def __repr__(self):
        def get(i):
            if i is None:
                return "None"
            else:
                return self._bus._enabled[i]

        return f"PLA(LORAM={get(self.i_basic)}, HIRAM={get(self.i_kernal)}, CHARGEN={get(self.i_chargen)}, IO={get(self.i_io)})"

    @classmethod
    def test(cls):
        class BusMock:
            def __init__(self):
                # chargen, kernal, basic, io
                self.p = [False, False, False, False]

            def set_enabled(self, index: int, enable: bool):
                self.p[index] = enable

            def print(self, pla):
                print(
                    f"{pla.val & cls.CHAREN > 0:3d} {pla.val & cls.HIRAM > 0:3d} {pla.val & cls.LORAM > 0:3d} - "
                    f"{self.p[0] and 'CHAR':5} {self.p[1] and 'KERN':5} {self.p[2] and 'BASIC':5} {self.p[3] and 'IO'}"
                )

        b = BusMock()
        t = cls(b)
        t.i_chargen = 0
        t.i_kernal = 1
        t.i_basic = 2
        t.i_io = 3
        print("CHA HIM LOM")
        for i in range(8):
            t.val = i
            t._update_peripherals()
            b.print(t)


class Multiplex(BusPart):
    def __init__(self):
        self.parts: typing.List[BusPart] = []

    def add(self, part: BusPart):
        self.parts.append(part)

    def reset(self):
        for part in self.parts:
            part.reset()

    def read_address(self, addr: TAddr) -> BusRet:
        i = 0
        e = len(self.parts)
        while i < e:
            value = self.parts[i].read_address(addr)
            if value is not None:
                return value
            i += 1

    def write_address(self, addr: TAddr, data: TData):
        i = 0
        e = len(self.parts)
        while i < e:
            self.parts[i].write_address(addr, data)
            i += 1

    def __repr__(self):
        return "Multiplex(" + ", ".join(repr(p) for p in self.parts) + ")"

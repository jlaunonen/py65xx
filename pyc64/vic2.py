# -*- coding: utf-8 -*-
# Copyright (C) 2021  Jyrki Launonen

from __future__ import annotations

import array
import enum
import typing

if typing.TYPE_CHECKING:
    from py65xx.bus import Bus

from py65xx.defs import BusPart, BusRet, TAddr, TData

_CL_STATIC = 0xF0
_MASK_NIBBLE = 0x0F


class DisplayMode(enum.IntEnum):
    TEXT_STANDARD = 0
    TEXT_MULTI_COLOR = 1
    TEXT_EXTENDED = 2

    BM_STANDARD = 3
    BM_MULTI_COLOR = 4


class VIC2(BusPart):
    """
    VIC2 data module.
    This doesn't implement much other than the registers and some basic calculation.
    """

    # 25 rows, 40 cols; 24x38

    def __init__(self, bus: Bus, cpu):
        self.bus = bus
        self.cpu = cpu

        self._mem_base = 0xC000

        # Current raster position. Visible area is 51..251
        self._raster_pos = 0
        self._raster_latch = 0

        self._rsel = 1  # 0=24 rows, 1=25 rows
        self._csel = 1  # 0=38 cols, 1=40 cols

        # All colors are 0..15 / 4bit

        self.bord_cl = 3  # aka EC
        self.bg_cl = [0] * 4  # aka BxC

        self._spr_x = [0] * 8  # aka MxX
        self._spr_y = [0] * 8  # aka MxY
        self._spr_en = [False] * 8  # aka MxE
        self._spr_cl = [0] * 8  # aka MxC
        self._spr_mcl1 = 0  # aka MM0
        self._spr_mcl2 = 0  # aka MM1

        self._lpx = 0  # light pen x; half resolution
        self._lpy = 0  # light pen y

        """
        Current X scroll position.
        """
        self.scroll_x = 0

        """
        Current Y scroll position.
        When 0, first line should be covered.
        When 7, last line should be covered.
        """
        self.scroll_y = 0

        self._irst = 0  # raster count == stored raster count
        self._erst = 0
        self._imbc = 0  # sprite-data collision
        self._embc = 0
        self._immc = 0  # sprite-sprite collision
        self._emmc = 0
        self._ilp = 0  # negative transition of lightpen input
        self._elp = 0
        self._irq = 0

        self.den = 0  # 1 display enable / 0 screen blank
        self._res = 0

        self._mcm = self._bmm = self._ecm = 0
        self._vc1x = 1  # 0..15 Screen memory location. * 0x400
        self._cb1x = 2  # 0..7 Character data bits 11 to 13 (= * 0x800). 3..10 is char, 0..2 is char raster line.

    def reset(self):
        self.__init__(self.bus, self.cpu)

    def set_mem_base_index(self, base: int):
        # These addresses correspond to VIC2 address bits in CIA2A.
        self._mem_base = (0xC000, 0x8000, 0x4000, 0x0000)[base]
        print("Base", hex(self._mem_base))

    def read_address(self, addr: TAddr) -> BusRet:
        if 0xD000 <= addr <= 0xD3FF:
            c_addr = addr & 0x3F

            if 0 <= c_addr <= 0xF:
                # Sprite X and Y positions
                if c_addr % 2 == 0:
                    return self._spr_x[c_addr // 2] & 0xFF
                return self._spr_y[(c_addr - 1) // 2] & 0xFF
            if c_addr == 0x10:
                # MSB of X:s
                return sum(1 << i if x & 256 else 0 for i, x in enumerate(self._spr_x))

            if c_addr == 0x11:
                # Control reg 1
                # RST8, ECM, BMM, DEN, RSEL, YSCROLL:3
                return (
                    (self._raster_pos >> 8 & 1) << 7
                    | self._ecm << 6
                    | self._bmm << 5
                    | self.den << 4
                    | self._rsel << 3
                    | self.scroll_y
                )
            if c_addr == 0x12:
                # RASTER
                return self._raster_pos & 0xFF

            if c_addr == 0x13:
                # Light pen x
                return self._lpx
            if c_addr == 0x14:
                # Light pen y
                return self._lpy

            if c_addr == 0x15:
                # Sprite enabled
                return sum(1 << i if x & 256 else 0 for i, x in enumerate(self._spr_en))

            if c_addr == 0x16:
                # Control reg 2
                # -, -, RES, MCM, CSEL, XSCROLL:3
                return (
                    0xC0
                    | self._res << 5
                    | self._mcm << 4
                    | self._csel << 3
                    | self.scroll_x
                )

            # TODO: 0x17 MOB Y expand

            if c_addr == 0x18:
                # VM13..VM10, CB13..CB11, -
                return self._vc1x << 4 | self._cb1x << 1 | 1

            # TODO: 0x1B..0x1F MOB stuff

            if c_addr == 0x19:
                # IRQ, -, -, -, ILP, IMMC, IMBC, IRST
                return (
                    0x70
                    | self._irq << 7
                    | self._ilp << 3
                    | self._immc << 2
                    | self._imbc << 1
                    | self._irst
                )
            if c_addr == 0x1A:
                # ELP, EMMC, EMBC, ERST
                return (
                    _CL_STATIC
                    | self._elp << 3
                    | self._emmc << 2
                    | self._embc << 1
                    | self._erst
                )

            if c_addr == 0x20:
                # Border color
                return _CL_STATIC | self.bord_cl

            if 0x21 <= c_addr <= 0x24:
                # Background color
                return _CL_STATIC | self.bg_cl[c_addr - 0x21]

            if c_addr == 0x25:
                # Sprite multicolor 1
                return _CL_STATIC | self._spr_mcl1
            if c_addr == 0x26:
                # Sprite multicolor 2
                return _CL_STATIC | self._spr_mcl2

            if 0x27 <= c_addr <= 0x2E:
                # Sprite colors
                return _CL_STATIC | self._spr_cl[c_addr - 0x27]

            if 0x2F <= c_addr <= 0x3F:
                # Static.
                return 0xFF

    def write_address(self, addr: TAddr, data: TData):
        if 0xD000 <= addr <= 0xD3FF:
            c_addr = addr & 0x3F

            if 0 <= c_addr <= 0xF:
                # Sprite X and Y positions
                if c_addr % 2 == 0:
                    self._spr_x[c_addr // 2] = data
                else:
                    self._spr_y[(c_addr - 1) // 2] = data
            elif c_addr == 0x10:
                # MSB of X:s
                for i in range(8):
                    if data & (1 << i):
                        self._spr_x[i] |= 0x100
                    else:
                        self._spr_x[i] &= 0xFF

            elif c_addr == 0x11:
                # Control reg 1
                # RST8, ECM, BMM, DEN, RSEL, YSCROLL:3
                self.scroll_y = data & 7
                self._rsel = data & 8 != 0
                self.den = data & 0x10 != 0
                self._bmm = data & 0x20 != 0
                self._ecm = data & 0x40 != 0
                if data & 0x80:
                    self._raster_latch |= 0x100
                else:
                    self._raster_latch &= 0xFF

            elif c_addr == 0x12:
                # RASTER TODO: Is bit8 actually kept=
                self._raster_latch = self._raster_latch & 0x100 | data

            elif c_addr == 0x16:
                # Control reg 2
                # -, -, RES, MCM, CSEL, XSCROLL:3
                self.scroll_x = data & 7
                self._csel = data & 8 != 0
                self._mcm = data & 0x10 != 0
                self._res = data & 0x20 != 0

            elif c_addr == 0x18:
                # VM13..VM10, CB13..CB11, -
                self._vc1x = (data >> 4) & 0xF
                self._cb1x = (data >> 1) & 0x7
                print("Display", self._vc1x, "font", self._cb1x)

            elif c_addr == 0x19:
                # IRQ, -, -, -, ILP, IMMC, IMBC, IRST
                self._irst = data & 1
                self._imbc = data & 2 != 0
                self._immc = data & 4 != 0
                self._ilp = data & 8 != 0
                self._irq = data & 0x80 != 0
            elif c_addr == 0x1A:
                # ELP, EMMC, EMBC, ERST
                self._erst = data & 1
                self._embc = data & 2 != 0
                self._emmc = data & 4 != 0
                self._elp = data & 8 != 0

            elif c_addr == 0x20:
                # Border color
                self.bord_cl = data & _MASK_NIBBLE

            elif 0x21 <= c_addr <= 0x24:
                # Background color (when ECM=1)
                self.bg_cl[c_addr - 0x21] = data & _MASK_NIBBLE

            elif c_addr == 0x25:
                # Sprite multicolor 1
                self._spr_mcl1 = data & _MASK_NIBBLE
            elif c_addr == 0x26:
                # Sprite multicolor 2
                self._spr_mcl2 = data & _MASK_NIBBLE

            elif 0x27 <= c_addr <= 0x2E:
                # Sprite colors
                self._spr_cl[c_addr - 0x27] = data & _MASK_NIBBLE

    @property
    def display_base(self):
        return self._mem_base + self._vc1x * 0x400

    @property
    def graphics_base(self):
        return self._mem_base + (self._cb1x & 4 > 0) * 0x2000

    @property
    def font_base(self):
        return self._mem_base + self._cb1x * 0x800

    @property
    def columns(self):
        """
        Current column count: 40 or 38 columns.
        Memory contains always 40 columns, but for 38-column mode which
        supports scrolling, only 38 should be shown.
        """
        return 40 if self._csel else 38

    @property
    def can_scroll_x(self):
        return not self._csel

    @property
    def rows(self):
        """
        Current row count: 25 or 24 rows.
        Memory contains always 25 rows, but for 24-row mode which
        supports scrolling, only 24 should be shown.
        """
        return 25 if self._rsel else 24

    @property
    def can_scroll_y(self):
        return not self._rsel

    def mode(self) -> DisplayMode:
        mode = (self._mcm, self._bmm, self._ecm)
        if mode == (0, 0, 0):
            # Standard character mode
            return DisplayMode.TEXT_STANDARD
        if mode == (1, 0, 0):
            # Multi-color character mode
            return DisplayMode.TEXT_MULTI_COLOR
        if mode == (0, 0, 1):
            # Extended color mode
            # Char bit 6..7 index the bg color used from _bg_cl.
            return DisplayMode.TEXT_EXTENDED
        if mode == (0, 1, 0):
            # Standard bitmap mode
            return DisplayMode.BM_STANDARD
        if mode == (1, 1, 0):
            # Multi-color bitmap mode
            return DisplayMode.BM_MULTI_COLOR
        # Modes (1, 1, 1), (0, 1, 1) and (1, 0, 1) are invalid.
        raise RuntimeError("Unexpected graphics mode: " + str(mode))

    def set_lightpen_pos(self, x: int, y: int):
        """
        :param x: X-coordinate in screen, 0..320
        :param y: Y-coordinate in screen, 0..200
        """
        self._lpx = x // 2
        self._lpy = y
        print(self._lpx, self._lpy)


class ColorRAM(BusPart):
    def __init__(self):
        self.mem = [0] * 1024

    def reset(self):
        for i in range(len(self.mem)):
            self.mem[i] = 0

    def read_address(self, addr: TAddr) -> BusRet:
        if 0xD800 <= addr <= 0xDBFF:
            return self.mem[addr - 0xD800]

    def write_address(self, addr: TAddr, data: TData):
        if 0xD800 <= addr <= 0xDBFF:
            self.mem[addr - 0xD800] = data & 0xF

    def __getitem__(self, item):
        return self.mem[item]

    def dump(self, fname: str):
        with open(fname, "wb") as f:
            array.array("B", self.mem).tofile(f)


class Colors(int, enum.Enum):
    def __new__(cls, val):
        index = len(cls.__members__)
        obj = int.__new__(cls, index)
        obj._value_ = index
        obj.color = val
        obj.rgb = (val >> 16) & 0xFF, (val >> 8) & 0xFF, val & 0xFF
        return obj

    BLACK = 0x000000
    WHITE = 0xFFFFFF
    RED = 0x880000
    CYAN = 0x54FCFC
    VIOLET = 0xCC44CC
    GREEN = 0x00CC55
    BLUE = 0x0000A8
    YELLOW = 0xEEEE77
    ORANGE = 0xDD8855
    BROWN = 0x664400
    L_RED = 0xFF7777
    D_GREY = 0x333333
    GREY = 0x777777
    L_GREEN = 0xAAFF66
    L_BLUE = 0x5454FC
    L_GRY = 0xBBBBBB

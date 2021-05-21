# -*- coding: utf-8 -*-
# Copyright (C) 2021  Jyrki Launonen

from __future__ import annotations

from .addressing65xx import *
from .instructions65xx import *

if typing.TYPE_CHECKING:
    from .bus import Bus

OP = typing.Callable[["CPU"], typing.Any]


class SetOnceList(list):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._assigned = set()

    def __setitem__(self, key, value):
        if key in self._assigned:
            raise KeyError(f"Already assigned: 0x{key:02X}")
        self._assigned.add(key)
        super().__setitem__(key, value)


class ISet:
    __slots__ = ("iset", "rts", "brk")

    def __init__(self):

        # instruction, addressing, bytes, cycles
        self.iset: typing.List[typing.Tuple[OP, OP, int, int]] = SetOnceList(
            [(fault, afault, 1, 0)] * 256
        )

        self.iset[0x02] = jam, aimpl, 2, 1
        self.iset[0x12] = jam, aimpl, 2, 1
        self.iset[0x22] = jam, aimpl, 2, 1
        self.iset[0x32] = jam, aimpl, 2, 1
        self.iset[0x42] = jam, aimpl, 2, 1
        self.iset[0x52] = jam, aimpl, 2, 1
        self.iset[0x62] = jam, aimpl, 2, 1
        self.iset[0x72] = jam, aimpl, 2, 1
        self.iset[0x92] = jam, aimpl, 2, 1
        self.iset[0xB2] = jam, aimpl, 2, 1
        self.iset[0xD2] = jam, aimpl, 2, 1
        self.iset[0xF2] = jam, aimpl, 2, 1

        self.iset[0x00] = brk, aimpl, 1, 7
        self.iset[0x01] = ora, aindx, 2, 6
        self.iset[0x05] = ora, azero, 2, 3
        self.iset[0x06] = asl, azero, 2, 5
        self.iset[0x08] = php, aimpl, 1, 3
        self.iset[0x09] = ora, aimm, 2, 2
        self.iset[0x0A] = asl, aacc, 1, 2
        self.iset[0x0D] = ora, aabs, 3, 4
        self.iset[0x0E] = asl, aabs, 3, 6
        #

        self.iset[0x10] = bpl, arel, 2, 2  # pb12
        self.iset[0x11] = ora, aindy, 2, 5  # pb
        self.iset[0x15] = ora, azerox, 2, 4
        self.iset[0x16] = asl, azerox, 2, 6
        self.iset[0x18] = clc, aimpl, 1, 2
        self.iset[0x19] = ora, aabsy, 3, 4  # pb
        self.iset[0x1D] = ora, aabsx, 3, 4  # pb
        self.iset[0x1E] = asl, aabsx, 3, 7
        #

        self.iset[0x20] = jsr, aabs, 3, 6
        self.iset[0x21] = iand, aindx, 2, 6
        self.iset[0x24] = bit, azero, 2, 3
        self.iset[0x25] = iand, azero, 2, 3
        self.iset[0x26] = rol, azero, 2, 5
        #         0x27
        self.iset[0x28] = plp, aimpl, 1, 4
        self.iset[0x29] = iand, aimm, 2, 2
        self.iset[0x2A] = rol, aacc, 1, 2
        self.iset[0x2C] = bit, aabs, 3, 4
        self.iset[0x2D] = iand, aabs, 3, 4
        self.iset[0x2E] = rol, aabs, 3, 6
        #

        self.iset[0x30] = bmi, arel, 2, 2  # pb12
        self.iset[0x31] = iand, aindy, 2, 5  # pb
        #         0x32
        #         0x33
        #         0x34
        self.iset[0x35] = iand, azerox, 2, 4
        self.iset[0x36] = rol, azerox, 2, 6
        #         0x37
        self.iset[0x38] = sec, aimpl, 1, 2
        self.iset[0x39] = iand, aabsy, 3, 4  # pb
        #         0x3A
        #         0x3B
        #         0x3C
        self.iset[0x3D] = iand, aabsx, 3, 4  # pb
        self.iset[0x3E] = rol, aabsx, 3, 7
        #

        self.iset[0x40] = rti, aimpl, 1, 6
        self.iset[0x41] = eor, aindx, 2, 6
        #
        self.iset[0x45] = eor, azero, 2, 3
        self.iset[0x46] = lsr, azero, 2, 5
        self.iset[0x48] = pha, aimpl, 1, 3
        self.iset[0x49] = eor, aimm, 2, 2
        self.iset[0x4A] = lsr, aacc, 1, 2
        self.iset[0x4C] = jmp, aabs, 3, 3
        self.iset[0x4D] = eor, aabs, 3, 4
        self.iset[0x4E] = lsr, aabs, 3, 6
        #

        self.iset[0x50] = bvc, arel, 2, 2  # pb12
        self.iset[0x51] = eor, aindy, 2, 5  # pb
        self.iset[0x55] = eor, azerox, 2, 4
        self.iset[0x56] = lsr, azerox, 2, 6
        self.iset[0x58] = cli, aimpl, 1, 2
        self.iset[0x59] = eor, aabsy, 3, 4  # pb
        self.iset[0x5C] = nop, aabs, 3, 4  # illegal. nmos 3,4; cmos 3,8
        self.iset[0x5D] = eor, aabsx, 3, 4  # pb
        self.iset[0x5E] = lsr, aabsx, 3, 7
        #

        self.iset[0x60] = rts, aimpl, 1, 6
        self.iset[0x61] = adc, aindx, 2, 6
        self.iset[0x65] = adc, azero, 2, 3
        self.iset[0x66] = ror, azero, 2, 5
        self.iset[0x68] = pla, aimpl, 1, 4
        self.iset[0x69] = adc, aimm, 2, 2
        self.iset[0x6A] = ror, aacc, 1, 2
        self.iset[0x6C] = jmp, aind, 3, 5
        self.iset[0x6D] = adc, aabs, 3, 4
        self.iset[0x6E] = ror, aabs, 3, 6
        #

        self.iset[0x70] = bvs, arel, 2, 2  # pb12
        self.iset[0x71] = adc, aindy, 2, 5  # pb
        self.iset[0x75] = adc, azerox, 2, 4
        self.iset[0x76] = ror, azerox, 2, 6
        self.iset[0x78] = sei, aimpl, 1, 2
        self.iset[0x79] = adc, aabsy, 3, 4  # pb
        self.iset[0x7D] = adc, aabsx, 3, 4  # pb
        self.iset[0x7E] = ror, aabsx, 3, 7
        #

        #         0x80
        self.iset[0x81] = sta, aindx, 2, 6
        #         0x82
        #         0x83
        self.iset[0x84] = sty, azero, 2, 3
        self.iset[0x85] = sta, azero, 2, 3
        self.iset[0x86] = stx, azero, 2, 3
        #         0x87
        self.iset[0x88] = dey, aimpl, 1, 2
        #         0x89
        self.iset[0x8A] = txa, aimpl, 1, 2
        #         0x8B
        self.iset[0x8C] = sty, aabs, 3, 4
        self.iset[0x8D] = sta, aabs, 3, 4
        self.iset[0x8E] = stx, aabs, 3, 4
        #

        self.iset[0x90] = bcc, arel, 2, 2  # pb12
        self.iset[0x91] = sta, aindy, 2, 6
        #         0x92
        #         0x93
        self.iset[0x94] = sty, azerox, 2, 4
        self.iset[0x95] = sta, azerox, 2, 4
        self.iset[0x96] = stx, azeroy, 2, 4
        #         0x97
        self.iset[0x98] = tya, aimpl, 1, 2
        self.iset[0x99] = sta, aabsy, 3, 5
        self.iset[0x9A] = txs, aimpl, 1, 2
        #         0x9B
        #         0x9C
        self.iset[0x9D] = sta, aabsx, 3, 5
        #         0x9E

        self.iset[0xA0] = ldy, aimm, 2, 2
        self.iset[0xA1] = lda, aindx, 2, 6
        self.iset[0xA2] = ldx, aimm, 2, 2
        #         0xA3
        self.iset[0xA4] = ldy, azero, 2, 3
        self.iset[0xA5] = lda, azero, 2, 3
        self.iset[0xA6] = ldx, azero, 2, 3
        #         0xA7
        self.iset[0xA8] = tay, aimpl, 1, 2
        self.iset[0xA9] = lda, aimm, 2, 2
        self.iset[0xAA] = tax, aimpl, 1, 2
        #         0xAB
        self.iset[0xAC] = ldy, aabs, 3, 4
        self.iset[0xAD] = lda, aabs, 3, 4
        self.iset[0xAE] = ldx, aabs, 3, 4

        self.iset[0xB0] = bcs, arel, 2, 2  # pb12
        self.iset[0xB1] = lda, aindy, 2, 5  # pb
        #         0xB2
        #         0xB3
        self.iset[0xB4] = ldy, azerox, 2, 4
        self.iset[0xB5] = lda, azerox, 2, 4
        self.iset[0xB6] = ldx, azeroy, 2, 4
        #         0xB7
        self.iset[0xB8] = clv, aimpl, 1, 2
        self.iset[0xB9] = lda, aabsy, 3, 4  # pb
        self.iset[0xBA] = tsx, aimpl, 1, 2
        #         0xBB
        self.iset[0xBC] = ldy, aabsx, 3, 4  # pb
        self.iset[0xBD] = lda, aabsx, 3, 4  # pb
        self.iset[0xBE] = ldx, aabsy, 3, 4  # pb

        self.iset[0xC0] = cpy, aimm, 2, 3
        self.iset[0xC1] = cmp, aindx, 2, 6
        self.iset[0xC4] = cpy, azero, 2, 3
        self.iset[0xC5] = cmp, azero, 2, 3
        self.iset[0xC6] = dec, azero, 2, 3
        self.iset[0xC8] = iny, aimpl, 1, 2
        self.iset[0xC9] = cmp, aimm, 2, 2
        self.iset[0xCA] = dex, aimpl, 1, 2
        self.iset[0xCC] = cpy, aabs, 3, 4
        self.iset[0xCD] = cmp, aabs, 3, 4
        self.iset[0xCE] = dec, aabs, 3, 6

        self.iset[0xD0] = bne, arel, 2, 2  # pb12
        self.iset[0xD1] = cmp, aindy, 2, 5  # pb
        self.iset[0xD5] = cmp, azerox, 2, 4
        self.iset[0xD6] = dec, azerox, 2, 6
        self.iset[0xD8] = cld, aimpl, 1, 2
        self.iset[0xD9] = cmp, aabsy, 3, 4  # pb
        self.iset[0xDD] = cmp, aabsx, 3, 4  # pb
        self.iset[0xDE] = dec, aabsx, 3, 7

        self.iset[0xE0] = cpx, aimm, 2, 2
        self.iset[0xE1] = sbc, aindx, 2, 6
        #         0xE2
        #         0xE3
        self.iset[0xE4] = cpx, azero, 2, 3
        self.iset[0xE5] = sbc, azero, 2, 3
        self.iset[0xE6] = inc, azero, 2, 5
        #         0xE7
        self.iset[0xE8] = inx, aimpl, 1, 2
        self.iset[0xE9] = sbc, aimm, 2, 2
        self.iset[0xEA] = nop, aimpl, 1, 2
        #         0xEB
        self.iset[0xEC] = cpx, aabs, 3, 4
        self.iset[0xED] = sbc, aabs, 3, 4
        self.iset[0xEE] = inc, aabs, 3, 6

        self.iset[0xF0] = beq, arel, 2, 2  # pb12
        self.iset[0xF1] = sbc, aindy, 2, 5  # pb
        self.iset[0xF5] = sbc, azerox, 2, 4
        self.iset[0xF6] = inc, azerox, 2, 6
        self.iset[0xF8] = sed, aimpl, 1, 2
        self.iset[0xF9] = sbc, aabsy, 3, 4  # pb
        self.iset[0xFD] = sbc, aabsx, 3, 4  # pb
        self.iset[0xFE] = inc, aabsx, 3, 7  # pb

        self.brk = brk
        self.rts = rts

    def __getitem__(self, item):
        return self.iset[item]

    def dis(
        self,
        mem: typing.Union[typing.List, Bus],
        start: int,
        end: typing.Optional[int] = None,
    ):
        i = start
        if end is None:
            _end = start
        else:
            _end = end
        ret: typing.List[str] = []
        while i <= _end:
            b = mem[i]
            if b is None:
                ret.append(f"${i:04X} None")
                continue
            instr = self.iset[b]
            arg_len = instr[2] - 1
            arg = mem[i + 1 : i + 1 + arg_len]
            arg_hex = "".join(f"{a:02X}" for a in reversed(arg))

            bs = " ".join(f"{a:02X}" for a in mem[i : i + 1 + arg_len])
            if instr[0] == fault:
                bs += " " + str(mem[i])

            # noinspection PyUnresolvedReferences
            body = f"${i:04X} {instr[0].__name__.upper()} {instr[1].dis(arg_hex)}"
            ret.append(f"{body:20} {bs}")
            i += 1 + arg_len
        if end is None:
            return ret[0]
        return ret

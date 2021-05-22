# -*- coding: utf-8 -*-
# Copyright (C) 2021  Jyrki Launonen

from __future__ import annotations

import dataclasses
import enum
import typing

from py65xx.bcd import bcdtoi, itobcd
from py65xx.clock import Clock, Clocked
from py65xx.defs import BusPart, BusRet, TAddr, TData

if typing.TYPE_CHECKING:
    from pyc64.keyboard import Keyboard
    from pyc64.vic2 import VIC2


class _CIAPart:
    # Bits 0 = Input, 1 = Output
    ddr: int

    def reset(self):
        raise NotImplementedError()

    @property
    def value(self):
        raise NotImplementedError()

    @value.setter
    def value(self, val):
        raise NotImplementedError()


# How many cycles should be counted before 1/10s is increased. 100_000 would be kind of emulation-accurate.
CIA_TOD_DIVIDER = 15_000


class ICR(enum.IntEnum):
    UTA = 1
    UTB = 1 << 1
    UTOD = 1 << 2
    SDR = 1 << 3
    FLAG = 1 << 4


class CRA(enum.IntEnum):
    """
    Control Register A bits.
    """

    ENABLE = 1
    # underflow?
    # ??
    TMR_STOP = 1 << 3  # ...after underflow.
    LATCH_ONCE = 1 << 4
    TOD_RTC_50HZ = 1 << 7


class CRB(enum.IntEnum):
    """
    Control Register B bits.
    """

    ENABLE = 1
    # underflow?
    # ??
    TMR_STOP = 1 << 3  # ...after underflow.
    LATCH_ONCE = 1 << 4

    # Bits and masks for 5..6 timer sources.
    TMR_COUNT_MASK = 1 << 5 | 1 << 6
    TMR_COUNT_SYS = 0
    TMR_COUNT_CNT = 1 << 5
    TMR_COUNT_TMRA = 1 << 6
    TMR_COUNT_TMRA_ON_CNT = TMR_COUNT_MASK

    TOD_W_SET_ALARM = 1 << 7


@dataclasses.dataclass
class RealTime:
    s_per_10: int = 0
    s: int = 0
    m: int = 0
    h: int = 0

    def __str__(self):
        return f"{self.h:02d}:{self.m:02d}:{self.s:02d}.{self.s_per_10:d}"

    def tick_10th(self):
        self.s_per_10 += 1
        if self.s_per_10 >= 10:
            self.s_per_10 = 0

            self.s += 1
            if self.s >= 60:
                self.s = 0

                self.m += 1
                if self.m >= 60:
                    self.m = 0

                    self.h += 1
                    if self.h >= 24:
                        self.h = 0


class CIA(BusPart, Clocked):
    def __init__(self, base_addr: int, clock: Clock, irq: int):
        self._base_addr = base_addr
        self._end_addr = base_addr + 0xFF
        self._clock = clock
        self._irq = irq  # IRQ or NMI, depending on CIA part.

        self._tmr1_val = 0
        self._tmr1_div = 0
        self._tmr1_active = False
        self._tmr1_latch = 0xFFFF

        self._tmr2_val = 0
        self._tmr2_div = 0
        self._tmr2_active = False
        self._tmr2_latch = 0xFFFF

        self._pa1_ddr = 0
        self._pa2_ddr = 0
        self.pio1: typing.Optional[_CIAPart] = None
        self.pio2: typing.Optional[_CIAPart] = None

        self._tod_freeze: typing.Optional[RealTime] = None
        self._tod = RealTime()
        self._tod_alarm = RealTime()
        self._tod_cycles = 0  # on_clock cycle counter

        self._icr_data = 0
        self._icr_mask = 0

        # Control Register for timer A
        self._cra = 0
        # Control Register for timer B
        self._crb = 0

    def reset(self):
        # All DDR as inputs,
        # port registers zero (but return high due pullup),
        # timer ctl zero, timer latches 0xff,
        # other registers zero.
        pio1 = self.pio1
        pio2 = self.pio2
        self.__init__(self._base_addr, self._clock, self._irq)
        self.pio1 = pio1
        self.pio2 = pio2
        if self.pio1 is not None:
            self.pio1.reset()
        if self.pio2 is not None:
            self.pio2.reset()

    def read_address(self, addr: TAddr) -> BusRet:
        if self._base_addr <= addr < self._end_addr:
            c_addr = addr & 0xF

            if c_addr == 0:
                if self.pio1 is not None:
                    return self.pio1.value
                return 0
            if c_addr == 1:
                if self.pio2 is not None:
                    return self.pio2.value
                return 0
            if c_addr == 2:
                return self._pa1_ddr
            if c_addr == 3:
                return self._pa1_ddr
            if c_addr == 4:
                return self._tmr1_val & 0xFF
            if c_addr == 5:
                return self._tmr1_val >> 8
            if c_addr == 6:
                return self._tmr2_val & 0xFF
            if c_addr == 7:
                return self._tmr2_val >> 8

            if c_addr == 8:
                # TOD 10THS
                r = (self._tod_freeze or self._tod).s_per_10
                self._tod_freeze = None
                print("read /10", r)
                return itobcd(r)
            if c_addr == 9:
                # TOD SEC
                r = (self._tod_freeze or self._tod).s
                print("read sec", r)
                return itobcd(r)
            if c_addr == 0xA:
                # TOD MIN
                r = (self._tod_freeze or self._tod).m
                print("read min", r)
                return itobcd(r)
            if c_addr == 0xB:
                # TOD HR
                r = (self._tod_freeze or self._tod).h
                print("read hr", r)
                if r >= 12:
                    pm = 0x80
                    r -= 12
                else:
                    pm = 0
                return pm | itobcd(r)

            if c_addr == 0xC:
                # SDR
                return 0

            if c_addr == 0xD:
                # ICR, Status
                d = self._icr_data
                if d & self._icr_mask:
                    d |= 0x80
                self._icr_data = 0
                return d

            if c_addr == 0xE:
                # CRA
                return self._cra
            if c_addr == 0xF:
                # CRB
                return self._crb

    def write_address(self, addr: TAddr, data: TData):
        if self._base_addr <= addr < self._end_addr:
            c_addr = addr & 0xF
            if c_addr == 0:
                if self.pio1 is not None:
                    self.pio1.value = data
            elif c_addr == 1:
                if self.pio2 is not None:
                    self.pio2.value = data
            elif c_addr == 2:
                if self.pio1 is not None:
                    self.pio1.ddr = data
                self._pa1_ddr = data
            elif c_addr == 3:
                if self.pio2 is not None:
                    self.pio2.ddr = data
                self._pa1_ddr = data

            elif c_addr == 4:
                # TA LO
                self._tmr1_latch = self._tmr1_latch & 0xFF00 | data & 0xFF
            elif c_addr == 5:
                # TA HI
                self._tmr1_latch = self._tmr1_latch & 0xFF | data << 8
            elif c_addr == 6:
                # TB LO
                self._tmr2_latch = self._tmr2_latch & 0xFF00 | data & 0xFF
            elif c_addr == 7:
                # TB HI
                self._tmr2_latch = self._tmr2_latch & 0xFF | data << 8

            elif c_addr == 9:
                # TOD 10THS
                print("write /10", hex(data), self._crb & CRB.TOD_W_SET_ALARM)
                if self._crb & CRB.TOD_W_SET_ALARM == 0:
                    self._tod_freeze = None  # FIXME: Should be in read??
                    self._tod.s_per_10 = bcdtoi(data & 0xF)
                else:
                    self._tod_alarm.s_per_10 = bcdtoi(data & 0xF)

            elif c_addr == 9:
                # TOD SEC
                print("write sec", hex(data), self._crb & CRB.TOD_W_SET_ALARM)
                if self._crb & CRB.TOD_W_SET_ALARM == 0:
                    self._tod.s = bcdtoi(data)
                else:
                    self._tod_alarm.s = bcdtoi(data)

            elif c_addr == 0xA:
                # TOD MIN
                print("write min", hex(data), self._crb & CRB.TOD_W_SET_ALARM)
                if self._crb & CRB.TOD_W_SET_ALARM == 0:
                    self._tod.m = bcdtoi(data)
                else:
                    self._tod_alarm.m = bcdtoi(data)

            elif c_addr == 0xB:
                # TOD HR
                print("write hr", hex(data), self._crb & CRB.TOD_W_SET_ALARM)
                if self._crb & CRB.TOD_W_SET_ALARM == 0:
                    self._tod_freeze = self._tod
                    self._tod.h = bcdtoi(data)
                else:
                    self._tod_alarm.h = bcdtoi(data)

            elif c_addr == 0xD:
                if data & 0x80:
                    # SET 0..4
                    self._icr_mask |= data & 0x1F
                else:
                    # CLEAR 0..4
                    self._icr_mask &= ~(data & 0x1F)

            elif c_addr == 0xE:
                # CRA
                self._cra = data & 0xEF  # bit4 not stored
                self._tmr1_active = data & CRA.ENABLE != 0
                if data & CRA.LATCH_ONCE:
                    self._tmr1_val = self._tmr1_latch
            elif c_addr == 0xF:
                # CRB
                self._crb = data & 0xEF  # bit4 not stored
                self._tmr2_active = data & CRA.ENABLE != 0
                if data & CRB.LATCH_ONCE:
                    self._tmr2_val = self._tmr2_latch

    def flag(self):
        # TODO
        self._icr_data |= 1 << 4

    def on_clock(self):
        r = None
        self._tod_cycles += 1
        if self._tod_cycles >= CIA_TOD_DIVIDER:
            self._tod_cycles = 0
            self._tod.tick_10th()

        t1_underflow = False
        if self._tmr1_active:
            self._tmr1_val -= 1

            if self._tmr1_val < 0:
                t1_underflow = True
                self._icr_data |= ICR.UTA
                if self._cra & CRA.TMR_STOP:
                    self._tmr1_active = False
                    self._cra &= ~CRA.ENABLE
                if self._cra & CRA.LATCH_ONCE == 0:
                    self._tmr1_val = self._tmr1_latch

        if self._tmr2_active:
            count_on = self._crb & CRB.TMR_COUNT_MASK
            if (
                count_on == CRB.TMR_COUNT_SYS
                or count_on == CRB.TMR_COUNT_TMRA
                and t1_underflow
            ):
                self._tmr2_val -= 1

            if self._tmr2_val < 0:
                # TMR2 underflow
                self._icr_data |= ICR.UTB
                if self._crb & CRB.TMR_STOP:
                    self._tmr2_active = False
                    self._crb &= ~CRB.ENABLE
                if self._crb & CRB.LATCH_ONCE == 0:
                    self._tmr2_val = self._tmr2_latch

        if self._icr_data & self._icr_mask & 0x1F:
            r = self._irq

        return r

    def __repr__(self):
        return (
            f"CIA({self._base_addr:04X}, {self._tmr1_val:04X}/{self._tmr1_latch:04X})"
        )


class CIA2A(_CIAPart):
    def __init__(self, vic: typing.Optional[VIC2] = None):
        self.ddr = 0

        self._vic: typing.Optional[VIC2] = None
        # self._bus = bus
        self._vic_mem_index = 0
        if vic is not None:
            self.set_vic(vic)

        self._so_clk_last = False
        self._so_clk_counter = 0
        self._so_data = 0
        self._so_is_atn = False

    def reset(self):
        self.__init__(self._vic)

    def set_vic(self, vic):
        self._vic = vic
        vic.set_mem_base_index(self._vic_mem_index)

    @property
    def value(self):
        return self._vic_mem_index

    @value.setter
    def value(self, val):
        self._vic_mem_index = val & 0x3
        if self._vic is not None:
            self._vic.set_mem_base_index(self._vic_mem_index)


class CIA1AB(_CIAPart):
    def __init__(self, keyboard: Keyboard, is_b: bool):
        self._keyboard = keyboard
        self.ddr = 0
        self.strobe = 0

        # lateinit
        self.other_port: typing.Optional[CIA1AB] = None
        self._is_b = is_b

        # Inverted since reader is one using the mapping function.
        if not is_b:
            self._key_fn = keyboard.by_b
        else:
            self._key_fn = keyboard.by_a

    def reset(self):
        self._keyboard.reset()

    @property
    def value(self):
        return (~self._key_fn(self.strobe)) & 0xFF

    @value.setter
    def value(self, val):
        x = ~val & self.ddr
        self.other_port.strobe = x

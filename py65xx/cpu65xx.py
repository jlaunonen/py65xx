# -*- coding: utf-8 -*-
# Copyright (C) 2021  Jyrki Launonen

from __future__ import annotations
import collections
import enum
import typing

if typing.TYPE_CHECKING:
    from .bus import Bus
    from .clock import Clock

from .instructions65xx import irq, nmi
from .statelog import LOG
from .iset65xx import ISet

OP = typing.Callable[["CPU"], typing.Any]


class BreakOp(typing.NamedTuple):
    action: typing.Union[str, typing.Callable[["CPU"], None]] = "debug"
    cond: typing.Optional[typing.Callable[["CPU"], bool]] = None
    call: typing.Optional[typing.Callable[["CPU"], None]] = None


class StatusMasks:
    C = 1       # Carry
    Z = 1 << 1  # Zero
    I = 1 << 2  # IRQ Disable
    D = 1 << 3  # Decimal mode
    B = 1 << 4  # BRK
    res = 1 << 5 # Reserved
    V = 1 << 6  # Overflow
    N = 1 << 7  # Negative

    @classmethod
    def getter(cls, name):
        mask = getattr(cls, name)
        def inner(self):
            return self.val & mask > 0
        inner.__name__ = name
        return inner

    @classmethod
    def setter(cls, name):
        mask = getattr(cls, name)
        def inner(self, value):
            if value:
                self.val |= mask
            else:
                self.val &= ~mask
        inner.__name__ = name
        return inner

    @classmethod
    def pair(cls, v):
        return cls.getter(v), cls.setter(v)


# noinspection PyPropertyAccess
class Status:
    __slots__ = "val"

    def __init__(self, initial: int = 0x30):
        # 0x30 = BRK/4 + Reserved/5
        self.val = initial

    C = property(*StatusMasks.pair("C"), doc="Carry")
    Z = property(*StatusMasks.pair("Z"), doc="Zero")
    I = property(*StatusMasks.pair("I"), doc="IRQ disable")
    D = property(*StatusMasks.pair("D"), doc="Decimal mode")
    B = property(*StatusMasks.pair("B"), doc="BRK")
    res = property(*StatusMasks.pair("res"), doc="Reserved")
    V = property(*StatusMasks.pair("V"), doc="Overflow")
    N = property(*StatusMasks.pair("N"), doc="Negative")

    def update_by_value(self, val: int):
        self.Z = val == 0
        self.N = val & 0x80 > 0

    def load(self, val: int):
        self.val = val  # FIXME: So, what actually?
        self.res = True

    def __repr__(self):
        is_set =  "NVUBDIZC"
        not_set = "nvubdizc"
        return f"${self.val:02X}/" +\
               "".join(is_set[i] if f else not_set[i]
                       for i, f in enumerate([self.N, self.V, self.res, self.B, self.D, self.I, self.Z, self.C]))


def _sanitize(v: int):
    # assert v < -512 or v > 512, f"{v:X} is probably not 8bit"
    o = v
    if v < 0:
        o += 0x100
    elif v > 0xff:
        o -= 0x100
    assert 0 <= 0 < 256, f"{v:X} is not 8bit (result={o})"
    return o


# noinspection PyPep8Naming
class CPU:
    __slots__ = (
        "bus", "clock", "pc", "stc", "sp", "p", "spc",
    #    "A", "X", "Y",
        "_A", "_X", "_Y",
        "cmd_val", "data_val", "addr_val", "iset", "save", "breaks",
        "history", "irq",
    )
    class IRQ(enum.IntEnum):
        NONE = 0
        BRK = 1
        IRQ = 2
        NMI = 3

    def __init__(self, bus: Bus, clock: Clock, history_length: int = 5):
        self.bus = bus
        self.clock = clock

        self.pc = 0xfffc
        self.spc = 0        # Start of current command
        self.stc = 0x0100   # Bottom of stack.
        self.sp = 0xFF      # Stack pointer, offset from bottom.
        self.p = Status()
        self._A = self._Y = self._X = 0
        #self.A = self.Y = self.X = 0

        self.cmd_val = 0
        self.data_val = None  # Immediate value for operation.
        self.addr_val = 0  # Address for operation.
        self.save = None  # Function used to write back.

        self.iset = ISet()
        self.breaks: typing.Dict[int, BreakOp] = dict()
        self.history = collections.deque(maxlen=history_length)
        self.irq = self.IRQ.NONE

    @property
    def A(self):
        return self._A

    @A.setter
    def A(self, val: int):
        self._A = _sanitize(val)

    @property
    def X(self):
        return self._X

    @X.setter
    def X(self, val: int):
        self._X = _sanitize(val)

    @property
    def Y(self):
        return self._Y

    @Y.setter
    def Y(self, val: int):
        self._Y = _sanitize(val)

    def reset(self):
        self.pc = 0
        self.sp = 0xFF
        self.p = Status()
        self.A = 0
        self.Y = 0
        self.X = 0
        self.clock.reset() # should take 6 cycles.
        self.load_reset()

    def load_reset(self):
        self.pc = self.bus.read(0xfffc) | self.bus.read(0xfffd) << 8

    def print_stack(self):
        if LOG.stack:
            LOG.print("%02X:" % self.sp, ", ".join("%02X" % self.bus.mem[t] for t in range(self.stc + 0xff, self.stc + self.sp, -1)))

    def fault_log(self, msg: str):
        print(msg)
        for hpc in self.history:
            print(self.iset.dis(self.bus, hpc))

    def run(self, cycles: int = -1, step = False):
        self.bus.fault_handler = self.fault_log
        try:
            while cycles < 0 or self.clock.cycles < cycles:

                # Handle interrupt request, if any.
                if self.irq:
                    if self.irq == self.IRQ.BRK:
                        irq(self, is_brk=True)
                    elif self.irq & 0x7f == self.IRQ.NMI:
                        nmi(self)
                    elif self.irq == self.IRQ.IRQ and not self.p.I:
                        irq(self, is_brk=False)
                    # Reset request so next request can occur even during handling.
                    self.irq = 0


                # Continue instruction processing.
                self.spc = spc = self.pc
                sclk = self.clock.cycles
                if LOG.dis:
                    # Disassembly next instruction. Before breakpoint handling so allow debug op to see what's up.
                    LOG.print(self.iset.dis(self.bus, self.pc))
                is_bp = self.pc in self.breaks
                if is_bp:
                    the_break = self.breaks[self.pc]
                    bp_op = the_break.action
                    if the_break.cond is not None and not the_break.cond(self):
                        pass
                    elif bp_op == "log":
                        LOG.enable_all()
                    elif bp_op == "step":
                        step = True
                    elif bp_op == "call":
                        the_break.call(self)
                    elif bp_op == "debug":
                        print(f"Stopped on break point at ${self.pc:04X}")
                        breakpoint()
                    elif callable(bp_op):
                        # noinspection PyCallingNonCallable
                        bp_op(self)
                if step:
                    print(f"Step at ${self.pc:04X}")
                    breakpoint()

                self.history.append(self.pc)
                self.bus.pc = self.pc

                # Read from PC
                self.data_val = None
                self.cmd_val = cmd = self.bus.read(self.pc)
                self.pc += 1
                self.clock.wait_cycle()

                if callable(cmd):
                    # Not for usual operation, but allows e.g. implementing minikernel natively.
                    cmd(self)
                    continue

                # "Decode"
                instruction, addressing, b8s, ncycles = self.iset[cmd]
                # Access
                self.save = addressing(self)
                # Interact
                instruction(self)

                if LOG.status:
                    LOG.print(repr(self))
                if LOG.chk_cmd and self.pc - spc != b8s:
                    # N.B. This lies if the instruction was a jump.
                    LOG.print(f"${spc:04X} Advanced {self.pc - spc} bytes, expected {b8s} bytes.")
                if LOG.chk_clk and self.clock.cycles - sclk != ncycles:
                    LOG.print(f"${spc:04X} Ticked {self.clock.cycles - sclk} cycles, expected {ncycles} cycles.")

        except StopIteration:
            print("<break>")
        except KeyboardInterrupt:
            print("<stop>")
        print(repr(self))

    def __repr__(self):
        return f"pc=${self.pc:04X}, sp=${self.sp:02X}, p={self.p}, A=${self.A:02X}, X=${self.X:02X}, Y=${self.Y:02X}"


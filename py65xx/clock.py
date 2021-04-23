# -*- coding: utf-8 -*-
# Copyright (C) 2021  Jyrki Launonen

import time
import typing

class Clocked:
    def on_clock(self) -> typing.Optional[int]:
        raise NotImplementedError()


class Clock:
    __slots__ = ("_cycle_time_ns", "_last_cycle", "_s_waits", "_s_late", "cycles", "_cycle_listeners", "cpu")

    def __init__(self, two_mhz = False):
        self._cycle_time_ns = 500 if two_mhz else 1000
        self._last_cycle = 0
        self._s_waits = 0
        self._s_late = []
        self.cycles = 0
        self._cycle_listeners: typing.List[Clocked] = []
        self.cpu = None

    def register(self, listener: Clocked):
        self._cycle_listeners.append(listener)

    def reset(self):
        self._last_cycle = time.time_ns()
        self.cycles = 0

    def wait_cycle(self):
        self.cycles += 1
        for listener in self._cycle_listeners:
            r = listener.on_clock()
            if r is not None and r > self.cpu.irq:
                # IRQ from device connected to clock.
                self.cpu.irq = r

    def stats(self):
        print(f"Waits: {self._s_waits}, late: {self._s_late}", sum(self._s_late), self.cycles)

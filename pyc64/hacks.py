# -*- coding: utf-8 -*-
# Copyright (C) 2021  Jyrki Launonen

from __future__ import annotations

import typing

if typing.TYPE_CHECKING:
    from py65xx.bus import Bus, RAM
    from pyc64.support.defs import DEntry

from pyc64.support.prg import load_prg
from pyc64.support.tape import load_tape


class ProgramInject:
    """
    Helper class to inject programs directly into the emulator memory.
    Only supports .PRG and single-file .T64 files, since there is no way
    to load more from inside the emulation.
    """

    def __init__(self, programs: typing.List[str], bus: Bus, ram: RAM):
        self._bus = bus
        self._ram = ram
        self._prog_index = 0
        self._programs = []

        for p in programs:
            e = self.load(p)
            if e is not None:
                self._programs.append(e)

    @staticmethod
    def load(entry: str) -> typing.Optional[DEntry]:
        elow = entry.lower()
        if elow.endswith(".prg"):
            return load_prg(entry)
        elif elow.endswith(".t64"):
            entries = load_tape(entry)
            if len(entries) != 1:
                print("Unsupported count of programs in tape:", len(entries))
            return entries[0]
        else:
            print("Unsupported file format:", entry)

    def inject_next(self):
        if self._prog_index >= len(self._programs):
            print("Nothing to load.")
            return

        prg = self._programs[self._prog_index]
        self._prog_index = (self._prog_index + 1) % len(self._programs)

        prg.write_into(self._ram)
        end = prg.load_addr + len(prg.data)

        for copy in range(3):
            # Vartab, Arytab, stred
            self._bus.write(0x2D + copy * 2, end & 0xFF)
            self._bus.write(0x2E + copy * 2, end >> 8)

        # OLDTXT ptr to basic statment
        self._bus.write(0x3D, prg.load_addr & 0xFF)
        self._bus.write(0x3E, prg.load_addr >> 8)
        # EAL Ending address of load
        self._bus.write(0xAE, end & 0xFF)  # Load end
        self._bus.write(0xAF, end >> 8)

        # Put run to keyboard buffer.
        text = "RUN\r"
        for i, c in enumerate(text):
            self._bus.write(0x277 + i, ord(c))
        self._bus.write(0xC6, len(text))

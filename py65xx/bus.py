# -*- coding: utf-8 -*-
# Copyright (C) 2021  Jyrki Launonen

from __future__ import annotations

import array
import typing

from .defs import BusPart, BusRet, TAddr, TData
from .statelog import LOG


class RAM(BusPart):
    __slots__ = "mem"
    CLEAR_BYTE = 0x00

    def __init__(self):
        self.mem = array.array("B", (self.CLEAR_BYTE for _ in range(65536)))

    def reset(self):
        for i in range(len(self.mem)):
            self.mem[i] = self.CLEAR_BYTE

    def read_address(self, addr: TAddr) -> typing.Optional[TData]:
        if 0x0000 <= addr <= 0xFFFF:
            return self.mem[addr]

    def write_address(self, addr: TAddr, data: TData):
        if 0x0000 <= addr <= 0xFFFF:
            self.mem[addr] = data

    def __getitem__(self, item):
        return self.mem[item]

    def __repr__(self):
        return f"RAM()"

    def dump(self, fname: str):
        with open(fname, "wb") as f:
            self.mem.tofile(f)


class MMap(BusPart):
    __slots__ = ("name", "data", "start_addr", "end_addr", "rom_file")

    def __init__(
        self,
        name: str,
        rom_file: typing.Union[str, typing.List[int], bytes],
        start_addr: int,
        end_addr: int = -1,
        writable: bool = False,
        write_through: bool = True,
    ):
        self.name = name
        self.start_addr = start_addr
        self.writable = writable
        self.write_through = write_through
        self.rom_file = rom_file
        self.data: typing.List[int] = self.reset()

        self.end_addr = end_addr if end_addr >= 0 else start_addr + len(self.data) - 1

        if len(self.data) != (self.end_addr - self.start_addr + 1):
            raise ValueError(
                f"Rom length {hex(len(self.data))} does not match target segment"
                f" {hex(self.start_addr)}-{hex(self.end_addr)},"
                f" {hex(self.end_addr - self.start_addr + 1)} bytes"
            )

    def reset(self):
        rom_file = self.rom_file
        if isinstance(rom_file, str):
            with open(rom_file, "rb") as f:
                data = list(f.read())
        elif isinstance(rom_file, bytes):
            data = list(rom_file)
        else:
            data = rom_file.copy()

        self.data = data
        return data

    def read_address(self, addr: TAddr) -> BusRet:
        if self.start_addr <= addr <= self.end_addr:
            return self.data[addr - self.start_addr]

    def write_address(self, addr: TAddr, data: TData):
        if self.start_addr <= addr <= self.end_addr and not self.write_through:
            if not self.writable:
                return f"Write in {self.name} ROM ${addr:04X} - ${data:02X}"
            else:
                self.data[addr - self.start_addr] = data

    def __getitem__(self, item):
        return self.data[item]

    def __repr__(self):
        return f"MMap({self.name!r}, ${self.start_addr:04X})"

    def dump(self, fname: str):
        with open(fname, "wb") as f:
            array.array("B", self.data).tofile(f)


class Bus:
    __slots__ = (
        "_parts",
        "_enabled",
        "_defaults",
        "mem",
        "pc",
        "fault_handler",
        "write_breakpoints",
        "read_breakpoints",
    )

    def __init__(self):
        self._parts: typing.List[BusPart] = []
        self._enabled: typing.List[bool] = []
        self._defaults: typing.List[bool] = []
        # Reference to memory reference which skips bus multiplexing.
        self.mem = None
        # Copy of CPU program counter.
        self.pc = 0
        self.fault_handler = None
        self.write_breakpoints = set()
        self.read_breakpoints = set()

    def register(
        self,
        receiver: BusPart,
        before: typing.Optional[BusPart] = None,
        enabled: bool = True,
    ):
        if before is not None:
            to = self._parts.index(before)
            self._parts.insert(to, receiver)
        else:
            self._parts.append(receiver)
        self._enabled.append(enabled)
        self._defaults.append(enabled)
        return len(self._parts) - 1

    def set_enabled(self, index: int, enabled: bool):
        self._enabled[index] = enabled

    def reset(self):
        for part in self._parts:
            part.reset()
        for i, e in enumerate(self._defaults):
            self._enabled[i] = e

    def read(self, addr: TAddr, silent=False) -> BusRet:
        ret = 0
        if addr in self.read_breakpoints:
            breakpoint()

        # Check every part if they are enabled and supply given address.
        # Not using iterator / zip, as they are slower.
        i = 0
        e = len(self._parts)
        while i < e:
            if not self._enabled[i]:
                i += 1
                continue
            part = self._parts[i]
            value = part.read_address(addr)
            if value is not None:
                if not silent and LOG.bus_read:
                    LOG.print(f"<- ${addr:04X}: ${value:02X} ({part})")
                return value
            i += 1
        if not silent and LOG.bus_read:
            LOG.print(f"<- ${addr:04X}: ${ret:02X}")
        return ret

    def write(self, addr: TAddr, data: TData):
        if LOG.bus_write and (addr < 0x100 or addr > 0x1FF):
            LOG.print(f"-> ${addr:04X}: ${data:02X}")
        if addr in self.write_breakpoints:
            breakpoint()

        # Try to write each enabled part, which might ignore the write if it is not in their area.
        i = 0
        e = len(self._parts)
        while i < e:
            if not self._enabled[i]:
                i += 1
                continue
            r = self._parts[i].write_address(addr, data)
            if r is not None and self.fault_handler is not None:
                self.fault_handler(f"${self.pc:04X}: {r}")
            i += 1

    def __getitem__(self, item):
        if isinstance(item, slice):
            return [self.read(i, silent=True) for i in range(item.start, item.stop)]
        return self.read(item, silent=True)

    def find(
        self, part: typing.Type[BusPart], match_index: int = 0
    ) -> typing.Optional[BusPart]:
        for p in self._parts:
            if type(p) == part:
                if match_index == 0:
                    return p
                match_index -= 1

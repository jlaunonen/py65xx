# -*- coding: utf-8 -*-
# Copyright (C) 2021  Jyrki Launonen

from __future__ import annotations

import array
import typing

from .statelog import LOG

TData = int
TAddr = int
BusRet = typing.Optional[typing.Union[TData, callable]]


class BusPart:
    def reset(self):
        pass

    def read_address(self, addr: TAddr) -> BusRet:
        raise NotImplementedError()

    def write_address(self, addr: TAddr, data: TData):
        raise NotImplementedError()



class RAM(BusPart):
    __slots__ = "mem"
    CLEAR_BYTE = 0xff

    def __init__(self):
        self.mem = array.array('B', (self.CLEAR_BYTE for _ in range(65536)))

    def reset(self):
        for i in range(len(self.mem)):
            self.mem[i] = self.CLEAR_BYTE

    def read_address(self, addr: TAddr) -> typing.Optional[TData]:
        if 0x0000 <= addr <= 0xffff:
            return self.mem[addr]

    def write_address(self, addr: TAddr, data: TData):
        if 0x0000 <= addr <= 0xffff:
            self.mem[addr] = data

    def __getitem__(self, item):
        return self.mem[item]

    def __repr__(self):
        return f"RAM()"

    def dump(self, fname: str):
        with open(fname, "wb") as f:
            self.mem.tofile(f)


class MMap(BusPart):
    __slots__ = ("name", "data", "start_addr", "end_addr")

    def __init__(self, name: str, rom_file: typing.Union[str, typing.List[int], bytes], start_addr: int,
                 end_addr: int = -1, writable: bool = False, write_through: bool = True):
        self.name = name
        self.start_addr = start_addr
        self.writable = writable
        self.write_through = write_through
        self.data = array.array("B")

        if isinstance(rom_file, str):
            with open(rom_file, "rb") as f:
                self.data.frombytes(f.read())
        elif isinstance(rom_file, bytes):
            self.data.frombytes(rom_file)
        else:
            self.data.fromlist(rom_file)

        self.end_addr = end_addr if end_addr >= 0 else start_addr + len(self.data) - 1

        if len(self.data) != (self.end_addr - self.start_addr + 1):
            raise ValueError(f"Rom length {hex(len(self.data))} does not match target segment"
                             f" {hex(self.start_addr)}-{hex(self.end_addr)},"
                             f" {hex(self.end_addr - self.start_addr + 1)} bytes")

    def reset(self):
        if self.writable:
            raise ValueError("Writable MMap can not be reset :(")

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
            self.data.tofile(f)


class Bus:
    __slots__ = ("_parts", "_enabled", "mem", "pc", "fault_handler", "write_breakpoints", "read_breakpoints")

    def __init__(self):
        self._parts: typing.List[BusPart] = []
        self._enabled: typing.List[bool] = []
        # Reference to memory reference which skips bus multiplexing.
        self.mem = None
        # Copy of CPU program counter.
        self.pc = 0
        self.fault_handler = None
        self.write_breakpoints = set()
        self.read_breakpoints = set()

    def register(self, receiver: BusPart, before: typing.Optional[BusPart] = None):
        if before is not None:
            to = self._parts.index(before)
            self._parts.insert(to, receiver)
        else:
            self._parts.append(receiver)
        self._enabled.append(True)
        return len(self._parts) - 1

    def set_enabled(self, index: int, enabled: bool):
        self._enabled[index] = enabled

    def reset(self):
        for part in self._parts:
            part.reset()

    def read(self, addr: TAddr, silent=False) -> BusRet:
        ret = 0
        if addr in self.read_breakpoints:
            breakpoint()

        # Check every part if they are enabled and supply given address.
        for part, enabled in zip(self._parts, self._enabled):
            if not enabled:
                continue
            value = part.read_address(addr)
            if value is not None:
                if not silent and LOG.bus_read:
                    LOG.print(f"<- ${addr:04X}: ${value:02X} ({part})")
                return value
        if not silent and LOG.bus_read:
            LOG.print(f"<- ${addr:04X}: ${ret:02X}")
        return ret

    def write(self, addr: TAddr, data: TData):
        if LOG.bus_write and (addr < 0x100 or addr > 0x1ff):
            LOG.print(f"-> ${addr:04X}: ${data:02X}")
        if addr in self.write_breakpoints:
            breakpoint()

        # Try to write each enabled part, which might ignore the write if it is not in their area.
        for part, enabled in zip(self._parts, self._enabled):
            if not enabled:
                continue
            r = part.write_address(addr, data)
            if r is not None and self.fault_handler is not None:
                self.fault_handler(f"${self.pc:04X}: {r}")

    def __getitem__(self, item):
        if isinstance(item, slice):
            return [self.read(i, silent=True) for i in range(item.start, item.stop)]
        return self.read(item, silent=True)

    def find(self, part: typing.Type[BusPart], match_index: int = 0) -> typing.Optional[BusPart]:
        for p in self._parts:
            if type(p) == part:
                if match_index == 0:
                    return p
                match_index -= 1

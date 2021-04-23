# Copyright (C) 2021  Jyrki Launonen

import time

from py65xx.bus import Bus, MMap
from py65xx.clock import Clock
from py65xx.cpu65xx import CPU, BreakOp


def main():
    bus = Bus()
    clock = Clock()

    cpu = CPU(bus, clock, history_length=16)
    cpu.reset()

    # ROM from Klaus2m5/6502_65C02_functional_tests
    # Since the binary is full memory, consider the loaded memory directly writable.
    # The test needs to write into memory anyways.
    rom = MMap("FlashRom", "6502_functional_test.bin", 0, writable=True, write_through=False)
    bus.register(rom)
    bus.mem = rom  # not really mem, but...
    cpu.pc = 0x0400

    # cpu.breaks[0x35cd] = BreakOp(action="log")
    # cpu.breaks[0x3470] = BreakOp(action="log", cond=lambda c: clock.cycles > 40_000_000)

    print("Testing... (might take few minutes)")

    start = time.time()
    try:
        cpu.run()
    except:
        print(repr(cpu))
        clock.stats()
        raise
    end = time.time()
    print("took", end - start, "s")
    clock.stats()
    # rom.dump("ftest.dat")


if __name__ == '__main__':
    main()

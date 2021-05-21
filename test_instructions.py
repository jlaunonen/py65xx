# Copyright (C) 2021  Jyrki Launonen

import hashlib
import time

import py65xx.instructions65xx
from py65xx.bus import Bus, MMap
from py65xx.clock import Clock
from py65xx.cpu65xx import CPU, BreakOp

BIN = "6502_functional_test.bin"
LST = "6502_functional_test.lst"
# Commit 7954e2dbb49c469ea286070bf46cdd71aeb29e4b
BIN_HASH = "55c9ab5b137c8ced3c666bfdb55c8285782baad9"
SUCCESS_ADDRESS = 0x3469


def hash_test():
    try:
        with open(BIN, "rb") as f:
            data = f.read()
    except FileNotFoundError:
        print("File {} not found. Please ensure it exists in working directory.".format(BIN))
        exit(1)

    bin_hash = hashlib.sha1(data)
    if bin_hash.hexdigest() != BIN_HASH:
        print("Warning: {} SHA1 hash is not as expected.".format(BIN))
        print("Expected:", BIN_HASH)
        print("Got:     ", bin_hash.hexdigest())
        return False
    return True


def main():
    bus = Bus()
    clock = Clock()

    # Ensure we stop when expected.
    py65xx.instructions65xx.CHECK_STUCK = True

    cpu = CPU(bus, clock, history_length=16)
    cpu.reset()

    # ROM from Klaus2m5/6502_65C02_functional_tests
    # Since the binary is full memory, consider the loaded memory directly writable.
    # The test needs to write into memory anyways.
    rom_hash_valid = hash_test()
    rom = MMap("FlashRom", BIN, 0, writable=True, write_through=False)
    bus.register(rom)
    bus.mem = rom  # not really mem, but...
    cpu.pc = 0x0400

    # cpu.breaks[0x35cd] = BreakOp(action="log")
    # cpu.breaks[0x3470] = BreakOp(action="log", cond=lambda c: clock.cycles > 40_000_000)

    print("Testing... (might take few minutes)")

    start = time.time()
    try:
        r = cpu.run()
        print(repr(cpu))
    except:
        print(repr(cpu))
        clock.stats()
        raise
    end = time.time()
    print("took {:.3f} s".format(end - start))
    clock.stats()

    if r == 2:
        if rom_hash_valid:
            if cpu.pc == SUCCESS_ADDRESS:
                print("Test (probably) succeeded. Check {} to ensure we stopped in right place.".format(LST))
            else:
                print("Test (probably) failed. Check {} to see where CPU stuck.".format(LST))
        else:
            print("Test ended. Check {} to see where CPU stuck.".format(LST))

    # rom.dump("ftest.dat")


if __name__ == '__main__':
    main()

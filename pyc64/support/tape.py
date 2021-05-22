# -*- coding: utf-8 -*-
# Copyright (C) 2021  Jyrki Launonen

import struct
import typing

from pyc64.support.defs import DEntry


def load_tape(name: str) -> typing.Optional[typing.List[DEntry]]:
    """
    Load a .T64 tape file.
    Not all tapes can be loaded with this.
    - The C3C6 bug is not handled.
    - Only .PRG files are returned.
    - Signature check might be too restrictive (there are lot of different signatures).

    :param name: File name to load.
    :return: List of tape entries in DEntry, or None if load failed.
    """
    with open(name, "rb") as f:
        signature = f.read(32)
        if len(signature) != 32 or signature[0:4] != b"C64S":
            print("Not a T64 tape")
            return None

        main_header = f.read(32)
        if len(main_header) != 32:
            print("Unexpectedly short header")
            return None

        version, max_dents, total_dents, _, name = struct.unpack(
            "<HHHH24s", main_header
        )
        if version not in (0x0100, 0x0101):
            print("Unsupported version")
            return None

        dents = []
        for _ in range(max_dents):
            dent = f.read(32)
            if len(dent) != 32:
                print("Unexpectedly short dent")
                return None
            dents.append(dent)

        files = []
        for i, dent in enumerate(dents):
            (
                ftype_c64s,
                ftype_1541,
                load_addr,
                end_addr,
                _,
                offset,
                _,
                name,
            ) = struct.unpack("<BBHHHII16s", dent)
            if ftype_c64s == 0:
                continue
            if ftype_c64s != 1:
                print("Unsupported file type", ftype_c64s, "index", i)
                continue
            if end_addr == 0xC3C6:
                print("Buggy file", i)
                continue

            f.seek(offset)
            data = f.read(end_addr - load_addr)

            files.append(DEntry(load_addr, name, data))

    return files

# -*- coding: utf-8 -*-
# Copyright (C) 2021  Jyrki Launonen

import struct

from pyc64.support.defs import DEntry


def load_prg(name: str) -> DEntry:
    """
    Load a .PRG file.
    Two first bytes are expected to be the load address. After that, a slightly compressed basic program.

    :param name: File name to load.
    :return: DEntry.
    """
    with open(name, "rb") as f:
        (lpos,) = struct.unpack("<H", f.read(2))
        data = f.read()
    return DEntry(lpos, name, data)

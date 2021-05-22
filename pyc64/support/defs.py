# -*- coding: utf-8 -*-
# Copyright (C) 2021  Jyrki Launonen

import typing


class DEntry(typing.NamedTuple):
    load_addr: int
    name: str
    data: bytes

    def write_into(self, ram):
        for i, data in enumerate(self.data):
            ram.mem[self.load_addr + i] = data

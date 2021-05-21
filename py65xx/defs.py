# -*- coding: utf-8 -*-

import typing

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

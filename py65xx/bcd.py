# -*- coding: utf-8 -*-
# Copyright (C) 2021  Jyrki Launonen

def itobcd(i: int) -> int:
    """
    >>> itobcd(0)
    0
    >>> itobcd(9)
    9
    >>> hex(itobcd(99))
    '0x99'
    >>> hex(itobcd(123))
    '0x23'

    :param i:
    :return:
    """
    return (i % 10) | ((i // 10) % 10) << 4


def bcdtoi(bcd: int) -> int:
    """
    >>> bcdtoi(0x99)
    99
    >>> bcdtoi(9)
    9
    >>> bcdtoi(0)
    0

    :param bcd:
    :return:
    """
    return (bcd & 0xf) + ((bcd & 0xf0) >> 4) * 10

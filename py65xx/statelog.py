# -*- coding: utf-8 -*-
# Copyright (C) 2021  Jyrki Launonen


class Log:
    def __init__(self):
        self.dis = False
        self.chk_clk = False
        self.chk_cmd = False
        self.status = False
        self.stack = False
        self.bus_read = False
        self.bus_write = False

    def enable_all(self):
        self.dis = True
        self.chk_clk = True
        self.chk_cmd = True
        self.status = True
        self.stack = True
        self.bus_read = True
        self.bus_write = True

    def disable_all(self):
        self.__init__()

    @staticmethod
    def print(*args, **kwargs):
        print(*args, **kwargs)


LOG = Log()

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2021  Jyrki Launonen

import argparse
import time

import sdl2

import pyc64.keyboard_sdl2 as key_map
from py65xx.bus import RAM, Bus, MMap
from py65xx.clock import Clock
from py65xx.cpu65xx import CPU
from pyc64.cia import CIA, CIA1AB, CIA2A
from pyc64.graphics import Renderer, TextRenderer
from pyc64.hacks import ProgramInject
from pyc64.keyboard import Keyboard
from pyc64.pla import PLA, Multiplex
from pyc64.vic2 import VIC2, ColorRAM


def init(w: int, h: int, title: bytes = b"SDL"):
    if sdl2.SDL_Init(sdl2.SDL_INIT_VIDEO) < 0:
        print("Fail.", sdl2.SDL_GetError())
        exit(1)

    window = sdl2.SDL_CreateWindow(title, sdl2.SDL_WINDOWPOS_UNDEFINED, sdl2.SDL_WINDOWPOS_UNDEFINED,
                                   w, h, 0)
    if not window:
        print("Fail2.", sdl2.SDL_GetError())
        exit(1)

    sdl2.SDL_SetHint(sdl2.SDL_HINT_RENDER_SCALE_QUALITY, b"linear")
    renderer = sdl2.SDL_CreateRenderer(window, -1, sdl2.SDL_RENDERER_ACCELERATED)
    if not renderer:
        print("Fail3.", sdl2.SDL_GetError())
        exit(1)

    return window, renderer


def arg_parser():
    parser = argparse.ArgumentParser(description="Simple and stupid Commodore 64 emulator",
                                     formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument("program", nargs="*", type=str,
                        help="Program file to add in list of quick-load programs."
                             " Next program from the list is run by pressing F9."
                             " Note that emulation must be in the basic prompt before pressing F9!")
    parser.add_argument("--zoom", type=int, default=2, help="Zoom factor.")

    return parser.parse_args()


def main():
    args = arg_parser()

    ram = RAM()
    bus = Bus()

    w, h = Renderer.window_size(args.zoom)
    window, renderer = init(w, h, b"pyc64")

    clock = Clock()
    cpu = CPU(bus, clock, history_length=16)

    pla = PLA(bus)
    bus.register(pla)
    clock.cpu = cpu

    vic2 = VIC2(bus, cpu)

    io = Multiplex()
    pla.i_io = bus.register(io)

    # IO
    keys = Keyboard(key_map.keyboard_map())
    keys.unknown_key = key_map.unknown_key_handler

    cia1 = CIA(0xDC00, clock, CPU.IRQ.IRQ)
    cia1.pio1 = CIA1AB(keys, is_b=False)
    cia1.pio2 = CIA1AB(keys, is_b=True)
    cia1.pio2.other_port = cia1.pio1
    cia1.pio1.other_port = cia1.pio2

    cia2 = CIA(0xDD00, clock, CPU.IRQ.NMI)
    cia2.pio1 = CIA2A(vic2)


    io.add(cia1)
    io.add(cia2)
    c_ram = ColorRAM()
    io.add(c_ram)
    io.add(vic2)

    clock.register(cia1)
    clock.register(cia2)

    # ROMs
    pla.i_kernal = bus.register(MMap("kernal", "kernal", 0xe000, 0xffff))
    pla.i_basic = bus.register(MMap("basic", "basic", 0xa000, 0xbfff))
    pla.i_chargen = bus.register(MMap("chargen", "chargen", 0xd000, 0xdfff))

    text_renderer = TextRenderer(renderer, bus, zoom=args.zoom)
    bus.register(text_renderer)

    bus.register(ram)
    bus.mem = ram.mem

    display = Renderer(ram, c_ram, vic2, text_renderer, window, renderer, zoom=args.zoom)

    bus.reset()
    cpu.reset()

    start = time.time()
    run = True
    dump_index = 0

    inject = ProgramInject(args.program, bus, ram)

    # 40000 cycles = 0.04 s = 25 1/s .. if the emulation could run so fast.
    # 20k gives slightly better keyboard interaction.
    while run and cpu.run(20000) == 0:
        event = sdl2.SDL_Event()
        while sdl2.SDL_PollEvent(event):
            if event.type == sdl2.SDL_QUIT:
                run = False
                break
            if event.type == sdl2.SDL_KEYDOWN:
                scancode = event.key.keysym.scancode
                if scancode == sdl2.SDL_SCANCODE_PAUSE:
                    # RESTORE
                    print(">NMI")
                    cpu.irq = cpu.IRQ.NMI
                elif scancode == sdl2.SDL_SCANCODE_F9:
                    inject.inject_next()
                elif scancode == sdl2.SDL_SCANCODE_F10:
                    cpu.fault_log("")
                elif scancode == sdl2.SDL_SCANCODE_F11:
                    print("Reset")
                    bus.reset()
                    cpu.reset()
                elif scancode == sdl2.SDL_SCANCODE_F12:
                    ram.dump(f"dump-{dump_index}.dat")
                    dump_index += 1
                else:
                    keys.handle_key_down(scancode)
            elif event.type == sdl2.SDL_KEYUP:
                keys.handle_key_up(event.key.keysym.scancode)
            elif event.type == sdl2.SDL_MOUSEBUTTONDOWN:
                x = event.button.x - 50
                x //= 2
                y = event.button.y - 50
                y //= 2
                if 0 <= x <= 320 and 0 <= y <= 200:
                    vic2.set_lightpen_pos(x, y)
        display.draw()

    print("took", time.time() - start, "s")
    clock.stats()
    print()


if __name__ == '__main__':
    main()

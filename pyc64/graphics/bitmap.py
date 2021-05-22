# -*- coding: utf-8 -*-
# Copyright (C) 2021  Jyrki Launonen

from __future__ import annotations

import typing

import sdl2

if typing.TYPE_CHECKING:
    from py65xx.bus import RAM

from pyc64.vic2 import Colors


class BitmapRenderer:
    def __init__(self, size_multiplier: int = 2):
        self._clear = sdl2.SDL_Rect(0, 0, 8 * size_multiplier, size_multiplier)
        self._pix = sdl2.SDL_Rect(0, 0, size_multiplier, size_multiplier)
        self._size_multiplier = size_multiplier

    def draw_hires(self, renderer, bitmap_base: int, color_base: int, mem: RAM):
        colors = [Colors(i).rgb for i in range(16)]
        left = 50
        top = 50
        multiplier = self._size_multiplier
        self._pix.w = multiplier

        # 8000 = 40 "chars" * 200 lines. (also 320*200/8)
        for i in range(8000):
            # 1 cell = 1 pixel;  byte.bitmask
            #   0.10000000 0.01000000 ... 0.00000001  8.10000000 ... ... 312.10000000 ... 312.00000001
            #   1.10000000 1.01000000     1.00000001  9.10000000         ...
            #   2.10000000 2.01000000     2.00000001 10.10000000
            #   ...
            #   7.10000000 7.01000000     7.00000001 15.10000000         319.10000000     319.00000001
            # 320.10000000 ...

            line = i & 7  # or, i % 8
            x = i % 320
            x -= line  # make x to always be first of 8 consecutive pixels.
            row = i // 320
            y = row * 8 + line  # "line"

            x = left + x * multiplier
            y = top + y * multiplier

            c = mem[color_base + i // 8]
            bg = c & 0xF
            fg = c >> 4

            # Clear whole 8-pixel horizontal line by whole with background color.
            # The loop below will draw foreground pixels when needed.
            sdl2.SDL_SetRenderDrawColor(renderer, *colors[bg], 255)
            self._clear.x = x
            self._clear.y = y
            sdl2.SDL_RenderDrawRect(renderer, self._clear)

            sdl2.SDL_SetRenderDrawColor(renderer, *colors[fg], 255)
            d = mem[bitmap_base + i]
            self._pix.y = y
            for cx in range(8):
                if d & (1 << (7 - cx)):
                    self._pix.x = x + cx * multiplier
                    sdl2.SDL_RenderDrawRect(renderer, self._pix)

    def draw_multi_color(
        self,
        renderer,
        bitmap_base: int,
        video_matrix: int,
        color_mem,
        mem: RAM,
        bg_color: tuple,
    ):
        colors = [Colors(i).rgb for i in range(16)]
        left = 50
        top = 50
        multiplier = self._size_multiplier
        self._pix.w = multiplier * 2

        # 8000 = 40 "chars" * 200 lines. (also 320*200/8)
        for i in range(8000):
            # 1 cell = 1 dot (=2 pixels wide);  byte.bitmask
            #   0.11000000 0.00110000 ... 0.00000011  8.11000000 ... ... 312.11000000 ... 312.00000011
            #   1.11000000 1.00110000     1.00000011  9.11000000         ...
            #   2.11000000 2.00110000     2.00000011 10.11000000
            #   ...
            #   7.11000000 7.00110000     7.00000011 15.11000000         319.11000000     319.00000011
            # 320.11000000 ...

            line = i & 7  # or, i % 8
            x = i % 320
            x -= line  # make x to always be first of 8 consecutive pixels.
            row = i // 320
            y = row * 8 + line  # "line"

            x = left + x * multiplier
            y = top + y * multiplier

            screen_memory_color = mem[video_matrix + i // 8]
            color_memory_color = color_mem[i // 8]

            d = mem[bitmap_base + i]
            self._pix.y = y
            for cx in (0, 2, 4, 6):
                c = (d >> (6 - cx)) & 3
                if c == 0:
                    # Background
                    real_color = bg_color
                elif c == 1:
                    # Upper 4 bits
                    real_color = colors[screen_memory_color >> 4]
                elif c == 2:
                    # Lower 4 bits
                    real_color = colors[screen_memory_color & 0xF]
                else:
                    # Color memory
                    real_color = colors[color_memory_color]
                sdl2.SDL_SetRenderDrawColor(renderer, *real_color, 255)

                self._pix.x = x + cx * multiplier
                sdl2.SDL_RenderDrawRect(renderer, self._pix)

# -*- coding: utf-8 -*-
# Copyright (C) 2021  Jyrki Launonen

from __future__ import annotations

import typing

import sdl2

if typing.TYPE_CHECKING:
    from py65xx.bus import RAM
    from pyc64.vic2 import ColorRAM, VIC2

from pyc64.vic2 import Colors, DisplayMode

from . import BitmapRenderer, TextRenderer


class Renderer:
    def __init__(
        self,
        mem: RAM,
        colors: ColorRAM,
        vic: VIC2,
        font: TextRenderer,
        window,
        renderer,
        zoom: int = 2,
    ):
        self._last_draw_age = 0
        self._mem = mem
        self._colors = colors
        self._vic = vic
        self._font = font
        self._window = window
        self._renderer = renderer
        self._bitmap = BitmapRenderer()

        self._size_multiplier = m = zoom
        # TODO: Make these work better. Hard-coded borders...
        self._scroll_y_top = sdl2.SDL_Rect(50 - 8 * m, 50 - 4 * m, 640 + 16 * m, 8 * m)
        self._scroll_y_bottom = sdl2.SDL_Rect(
            50 - 8 * m, 450 - 4 * m, 640 + 16 * m, 8 * m
        )
        self._scroll_x_left = sdl2.SDL_Rect(50, 50 - 4 * m, 8 * m, 400 + 8 * m)
        self._scroll_x_right = sdl2.SDL_Rect(674, 50 - 4 * m, 16 * m, 400 + 8 * m)

    @staticmethod
    def window_size(zoom: int) -> typing.Tuple[int, int]:
        return (
            # 25px border each side, 40x25 chars, 8x8px per char.
            25 * 2 * zoom + 40 * 8 * zoom,
            25 * 2 * zoom + 25 * 8 * zoom,
        )

    # noinspection PyProtectedMembe
    def draw(self):
        mode = self._vic.mode()
        if self._vic.den and mode < 3:
            # Set before clearing since this changes render target.
            self._font.set_base_addr_and_mode(self._vic.font_base, mode)

        sdl2.SDL_SetRenderTarget(self._renderer, None)

        border = Colors(self._vic.bord_cl)

        sdl2.SDL_SetRenderDrawColor(self._renderer, *border.rgb, 255)
        sdl2.SDL_RenderClear(self._renderer)

        if self._vic.den:
            if mode < 3:
                self._draw_char_mode(border)
            elif mode == DisplayMode.BM_STANDARD:
                self._bitmap.draw_hires(
                    self._renderer,
                    self._vic.graphics_base,
                    self._vic.display_base,
                    self._mem,
                )
            elif mode == DisplayMode.BM_MULTI_COLOR:
                bg = Colors(self._vic.bg_cl[0]).rgb
                self._bitmap.draw_multi_color(
                    self._renderer,
                    self._vic.graphics_base,
                    self._vic.display_base,
                    self._colors,
                    self._mem,
                    bg,
                )
            else:
                print("Unknown mode", mode)

        sdl2.SDL_RenderPresent(self._renderer)

    def _draw_char_mode(self, border):
        bgs = [Colors(s) for s in self._vic.bg_cl]

        # 1000 characters.
        char_base = self._vic.display_base  # Display address. Default 0x400
        chrs = self._mem.mem[char_base : char_base + 1000]
        colors = self._colors.mem

        # XXX: This isn't actual accurate. Setting scroll values in large modes still cause scroll to happen.
        if self._vic.can_scroll_x:
            x_start = 50 + self._vic.scroll_x * self._size_multiplier
        else:
            x_start = 50
        if self._vic.can_scroll_y:
            # Move half line up; overlays after font drawing reduces effective screen size by one line.
            y_start = (
                50
                + self._vic.scroll_y * self._size_multiplier
                - 4 * self._size_multiplier
            )
        else:
            y_start = 50

        for row in range(25):
            start = row * 40
            end = start + 40
            chars_and_colors = zip(chrs[start:end], colors[start:end])

            y = y_start + row * 8 * 2
            self._font.draw(self._window, (x_start, y), chars_and_colors, bgs)

        if self._vic.can_scroll_x:
            sdl2.SDL_SetRenderDrawColor(self._renderer, *border.rgb, 255)
            sdl2.SDL_RenderFillRect(self._renderer, self._scroll_x_left)
            sdl2.SDL_RenderFillRect(self._renderer, self._scroll_x_right)

        if self._vic.can_scroll_y:
            sdl2.SDL_SetRenderDrawColor(self._renderer, *border.rgb, 255)
            sdl2.SDL_RenderFillRect(self._renderer, self._scroll_y_top)
            sdl2.SDL_RenderFillRect(self._renderer, self._scroll_y_bottom)

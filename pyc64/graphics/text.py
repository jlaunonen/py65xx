# -*- coding: utf-8 -*-
# Copyright (C) 2021  Jyrki Launonen

from __future__ import annotations

import typing

import sdl2

if typing.TYPE_CHECKING:
    from py65xx.bus import Bus
    from py65xx.defs import TData, TAddr, BusRet

from py65xx.defs import BusPart
from pyc64.vic2 import Colors, DisplayMode


class TextRenderer(BusPart):
    def __init__(self, renderer, bus: Bus, zoom: int = 2):
        w = 8 * 256 * zoom
        h = 8 * zoom

        # Single-color font.
        self._fnt1 = sdl2.SDL_CreateTexture(
            renderer, sdl2.SDL_PIXELFORMAT_ARGB8888, sdl2.SDL_TEXTUREACCESS_TARGET, w, h
        )
        sdl2.SDL_SetTextureBlendMode(self._fnt1, sdl2.SDL_BLENDMODE_BLEND)

        # 4-color font, one row per (non-clear) color.
        self._fnt2 = sdl2.SDL_CreateTexture(
            renderer,
            sdl2.SDL_PIXELFORMAT_ARGB8888,
            sdl2.SDL_TEXTUREACCESS_TARGET,
            w,
            h * 3,
        )
        sdl2.SDL_SetTextureBlendMode(self._fnt2, sdl2.SDL_BLENDMODE_BLEND)

        self._renderer = renderer
        self._bus = bus

        self._size = 8
        render_size = self._size * zoom
        self._size_multiplier = zoom
        self._render_size = render_size
        self._out_rect = sdl2.SDL_Rect(0, 0, render_size, render_size)
        self._src_rect = sdl2.SDL_Rect(0, 0, render_size, render_size)
        self._tmp = sdl2.SDL_Rect(0, 0, 740, 16)
        self._tmp2 = sdl2.SDL_Rect(0, 0, 740, 16)
        self._base_addr = -1
        self._mode = DisplayMode.TEXT_STANDARD
        self._pix = sdl2.SDL_Rect(0, 0, zoom, zoom)

        # Mild optimization to skip bus delay when using default character set.
        with open("chargen", "rb") as f:
            self._rom = list(f.read())

    def draw(self, screen, pos, txt: typing.Iterable[typing.Tuple[int, int]], bgs):
        # maybe not needed:
        sdl2.SDL_SetRenderDrawBlendMode(self._renderer, sdl2.SDL_BLENDMODE_BLEND)

        if (
            self._mode == DisplayMode.TEXT_STANDARD
            or self._mode == DisplayMode.TEXT_EXTENDED
        ):
            self._draw_mode_0(pos, txt, bgs)
        elif self._mode == DisplayMode.TEXT_MULTI_COLOR:
            self._draw_mode_1(pos, txt, bgs)

    def _draw_mode_0(self, pos, txt: typing.Iterable[typing.Tuple[int, int]], bgs):
        multi_bg = self._mode == DisplayMode.TEXT_EXTENDED
        if not multi_bg:
            sdl2.SDL_SetRenderDrawColor(self._renderer, *bgs[0].rgb, 255)

        prev_color = -1
        self._src_rect.y = 0
        self._out_rect.y = pos[1]
        for i, (char, color_index) in enumerate(txt):
            if multi_bg:
                bg = char >> 6
                char &= 0x3F
                sdl2.SDL_SetRenderDrawColor(self._renderer, *bgs[bg].rgb, 255)

            self._src_rect.x = char * self._render_size
            self._out_rect.x = pos[0] + i * self._render_size

            sdl2.SDL_RenderFillRect(self._renderer, self._out_rect)

            if prev_color != color_index:
                prev_color = color_index
                color_value = Colors(color_index).rgb
                sdl2.SDL_SetTextureColorMod(self._fnt1, *color_value)

            sdl2.SDL_RenderCopy(
                self._renderer, self._fnt1, self._src_rect, self._out_rect
            )

    def _draw_mode_1(self, pos, txt, bgs):
        sdl2.SDL_SetRenderDrawColor(self._renderer, *bgs[0].rgb, 255)
        fnt = self._fnt2
        self._out_rect.y = pos[1]
        for i, (char, color_index) in enumerate(txt):
            self._src_rect.x = char * self._render_size
            self._out_rect.x = pos[0] + i * self._render_size

            # Background 0; common for both chars.
            sdl2.SDL_RenderFillRect(self._renderer, self._out_rect)
            self._src_rect.y = 0

            if color_index & 0x8:
                # Multi-color char:

                # Background 1
                sdl2.SDL_SetTextureColorMod(fnt, *bgs[1].rgb)
                sdl2.SDL_RenderCopy(self._renderer, fnt, self._src_rect, self._out_rect)

                # Background 2
                self._src_rect.y = self._render_size
                sdl2.SDL_SetTextureColorMod(fnt, *bgs[2].rgb)
                sdl2.SDL_RenderCopy(self._renderer, fnt, self._src_rect, self._out_rect)

                # 3 bits of ram color.
                self._src_rect.y = self._render_size * 2
                color_value = Colors(color_index & 7).rgb
                sdl2.SDL_SetTextureColorMod(fnt, *color_value)
                sdl2.SDL_RenderCopy(self._renderer, fnt, self._src_rect, self._out_rect)
            else:
                # High-res char:
                color_value = Colors(color_index & 7).rgb
                sdl2.SDL_SetTextureColorMod(fnt, *color_value)

                sdl2.SDL_RenderCopy(self._renderer, fnt, self._src_rect, self._out_rect)

    @property
    def base_addr(self):
        return self._base_addr

    @property
    def mode(self) -> DisplayMode:
        return self._mode

    def set_base_addr_and_mode(self, base_address: int, mode: int):
        reload = False
        if self._base_addr != base_address:
            # 0x1000-0x1fff and 0x9000-0x9fff is character rom (some times visible in bus 0xd000).
            self._base_addr = base_address
            reload = True

        if self._mode != mode:
            self._mode = mode
            reload = True

        if reload:
            self._reload()

    def _reload(self):
        print("Reload font from", hex(self._base_addr), "using", repr(self._mode))
        if (
            self._mode == DisplayMode.TEXT_STANDARD
            or self._mode == DisplayMode.TEXT_EXTENDED
        ):
            self._load_mode_0()
        elif self._mode == DisplayMode.TEXT_MULTI_COLOR:
            self._load_mode_1()

    def _load_mode_0(self):
        sdl2.SDL_SetRenderTarget(self._renderer, self._fnt1)

        # Make draw calls to actually make required RGBA values for pixels.
        sdl2.SDL_SetRenderDrawBlendMode(self._renderer, sdl2.SDL_BLENDMODE_NONE)

        for c in range(0, 0x800, 8):
            char_addr = self._base_addr + c

            for line in range(8):
                val = self._read(char_addr + line)
                self._load_mode_0_line(line, c, val)

    def _load_mode_0_line(self, line, x, val):
        pix = self._pix
        size_multiplier = self._size_multiplier
        renderer = self._renderer
        for b in range(8):
            pix.x = (x + b) * size_multiplier
            pix.y = line * size_multiplier
            if val & (128 >> b):
                sdl2.SDL_SetRenderDrawColor(renderer, 255, 255, 255, 255)
            else:
                sdl2.SDL_SetRenderDrawColor(renderer, 0, 0, 0, 0)
            sdl2.SDL_RenderFillRect(renderer, pix)

    def _read(self, addr: int):
        if 0x1000 <= addr <= 0x1FFF:
            return self._rom[addr - 0x1000]
        elif 0x9000 <= addr <= 0x9FFF:
            return self._rom[addr - 0x9000]
        else:
            return self._bus.read(addr)

    def _load_mode_1(self):
        sdl2.SDL_SetRenderTarget(self._renderer, self._fnt2)

        # Make draw calls to actually make required RGBA values for pixels.
        sdl2.SDL_SetRenderDrawBlendMode(self._renderer, sdl2.SDL_BLENDMODE_NONE)

        # Make _pix to write two font pixels at a time.
        self._pix.w = self._size_multiplier * 2
        for c in range(0, 0x800, 8):
            char_addr = self._base_addr + c
            for line in range(8):
                val = self._read(char_addr + line)
                self._load_mode_1_line(line, c, val)
        self._pix.w = self._size_multiplier

    def _load_mode_1_line(self, line, x, val):
        pix = self._pix
        size_multiplier = self._size_multiplier
        renderer = self._renderer

        for b in range(4):
            color = (val >> (b * 2)) & 3
            pix.x = (x + ((3 - b) * 2)) * size_multiplier

            # All font planes need to be updated to ensure correct result when they are
            # drawn top of each other.
            for plane in range(3):
                pix.y = line * size_multiplier + self._render_size * plane

                # color 0 (=bg color 0) is not present in the font texture.
                # plane 0 is color 01, plane 1 is color 10, plane 2 is color 11.
                if color == plane + 1:
                    sdl2.SDL_SetRenderDrawColor(renderer, 255, 255, 255, 255)
                else:
                    sdl2.SDL_SetRenderDrawColor(renderer, 0, 0, 0, 0)
                sdl2.SDL_RenderFillRect(renderer, pix)

    def __del__(self):
        sdl2.SDL_DestroyTexture(self._fnt1)
        sdl2.SDL_DestroyTexture(self._fnt2)

    def read_address(self, addr: TAddr) -> BusRet:
        pass  # never readable?

    def write_address(self, addr: TAddr, data: TData):
        # 0x1000-0x1FFF and 0x9000-0x9FFF is default rom addresses and as so not alterable.
        if (
            self._base_addr not in (-1, 0x1000, 0x1800, 0x9000, 0x9800)
            and self._base_addr <= addr < self._base_addr + 0x800
        ):
            print("Update", hex(addr), bin(data))

            line = (addr - self._base_addr) % 8
            x = (addr - self._base_addr) - line

            sdl2.SDL_SetRenderDrawBlendMode(self._renderer, sdl2.SDL_BLENDMODE_NONE)
            if (
                self._mode == DisplayMode.TEXT_STANDARD
                or self._mode == DisplayMode.TEXT_EXTENDED
            ):
                sdl2.SDL_SetRenderTarget(self._renderer, self._fnt1)
                self._load_mode_0_line(line, x, data)
            elif self._mode == DisplayMode.TEXT_MULTI_COLOR:
                self._pix.w = self._size_multiplier * 2
                sdl2.SDL_SetRenderTarget(self._renderer, self._fnt2)
                self._load_mode_1_line(line, x, data)
                self._pix.w = self._size_multiplier

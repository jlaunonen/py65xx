# -*- coding: utf-8 -*-
# Copyright (C) 2021  Jyrki Launonen

import typing


class Keyboard:
    # fmt: off
    LIST = [
        # B0: A0..A7
        "DELETE", "3", "5", "7", "9", "+", "£", "1",
        # B1: ...
        "RETURN", "W", "R", "Y", "I", "P", "*", "<-",
        # B2
        "RIGHT", "A", "D", "G", "J", "L", ";", "CTRL",
        # B3
        "F7", "4", "6", "8", "0", "-", "HOME", "2",
        # B4
        "F1", "Z", "C", "B", "M", ".", "RSHIFT", "SPACE",
        # B5
        "F3", "S", "F", "H", "K", ":", "=", "C=",
        # B6: ^ is arrow up / power
        "F5", "E", "T", "U", "O", "@", "^", "Q",
        # B7
        "DOWN", "LSHIFT", "X", "V", "N", ",", "/", "STOP",
    ]
    # fmt: on
    assert len(LIST) == 64

    __slots__ = ("_a_values", "_b_values", "_key_map", "_key_to_pos", "unknown_key")

    def __init__(self, key_map: typing.Dict[int, int]):
        self._key_map = key_map
        self.unknown_key: typing.Optional[typing.Callable[[int], None]] = None

        # Name of key to (a,b) position. Could simplified to be scancode to (a,b).
        self._key_to_pos = {}

        # Currently active keys, as seen from b by writing a bit (index) to a.
        # Key is value written to a-port, value is value that can be read from b-port.
        self._a_values = [0] * 8

        # Currently active keys, as seen from a by writing a bit (index) to b.
        # Key is value written to b-port, value is value that can be read from a-port.
        self._b_values = [0] * 8

        for i, key in enumerate(self.LIST):
            a = i % 8
            b = i // 8
            self._key_to_pos[key] = a, b

    def push(self, key):
        pos = self._key_to_pos.get(key)
        if pos is not None:
            a, b = pos
            self._a_values[a] |= 1 << b
            self._b_values[b] |= 1 << a

    def release(self, key):
        pos = self._key_to_pos.get(key)
        if pos is not None:
            a, b = pos
            self._a_values[a] &= ~(1 << b)
            self._b_values[b] &= ~(1 << a)

    def reset(self):
        for i in range(8):
            self._a_values[i] = 0
            self._b_values[i] = 0

    def by_a(self, mask: int):
        """
        :param mask: Mask being tested. Should contain only one 1 bit.
        """
        r = 0
        for a in range(8):
            if (1 << a) & mask:
                r |= self._a_values[a]
        return r

    def by_b(self, mask: int):
        r = 0
        for b in range(8):
            if (1 << b) & mask:
                r |= self._b_values[b]
        return r

    # Special keys.
    # SDL = {
    #     sdl2.SDL_SCANCODE_RETURN: "RETURN",
    #     sdl2.SDL_SCANCODE_SPACE: "SPACE",
    #     sdl2.SDL_SCANCODE_BACKSPACE: "DELETE",
    #     sdl2.SDL_SCANCODE_LSHIFT: "LSHIFT",
    #     sdl2.SDL_SCANCODE_RSHIFT: "RSHIFT",
    #     sdl2.SDL_SCANCODE_ESCAPE: "STOP",
    #     sdl2.SDL_SCANCODE_HOME: "HOME",
    #     sdl2.SDL_SCANCODE_DOWN: "DOWN",
    #     sdl2.SDL_SCANCODE_RIGHT: "RIGHT",
    #     sdl2.SDL_SCANCODE_UP: ("LSHIFT", "DOWN"),
    #     sdl2.SDL_SCANCODE_LEFT: ("LSHIFT", "RIGHT"),
    #     sdl2.SDL_SCANCODE_SEMICOLON: ":",
    #     sdl2.SDL_SCANCODE_APOSTROPHE: ";",
    #     sdl2.SDL_SCANCODE_F1: "F1",
    #     sdl2.SDL_SCANCODE_F2: ("LSHIFT", "F1"),
    #     sdl2.SDL_SCANCODE_F3: "F3",
    #     sdl2.SDL_SCANCODE_F4: ("LSHIFT", "F3"),
    #     sdl2.SDL_SCANCODE_F5: "F5",
    #     sdl2.SDL_SCANCODE_F6: ("LSHIFT", "F5"),
    #     sdl2.SDL_SCANCODE_F7: "F7",
    #     sdl2.SDL_SCANCODE_F8: ("LSHIFT", "F7"),
    #     sdl2.SDL_SCANCODE_LCTRL: "CTRL",
    #     sdl2.SDL_SCANCODE_RCTRL: "CTRL",
    #     sdl2.SDL_SCANCODE_COMMA: ",",
    #     sdl2.SDL_SCANCODE_PERIOD: ".",
    #     sdl2.SDL_SCANCODE_SLASH: "/",
    #     sdl2.SDL_SCANCODE_MINUS: "-",
    #     sdl2.SDL_SCANCODE_BACKSLASH: "*",
    #     sdl2.SDL_SCANCODE_KP_PLUS: "+",
    #     sdl2.SDL_SCANCODE_KP_DIVIDE: "=",
    #     sdl2.SDL_SCANCODE_KP_MULTIPLY: "£",
    #     sdl2.SDL_SCANCODE_NONUSBACKSLASH: "<-",
    #     sdl2.SDL_SCANCODE_PAGEUP: "^",
    #     sdl2.SDL_SCANCODE_LEFTBRACKET: "@",
    #     sdl2.SDL_SCANCODE_GRAVE: "C="
    # }
    # # Number keys.
    # for i in range(10):
    #     k = getattr(sdl2, f"SDL_SCANCODE_{i}")
    #     SDL[k] = str(i)
    # # Alpha keys.
    # for i in range(ord('a'), ord('z') + 1):
    #     c = chr(i).upper()
    #     k = getattr(sdl2, f"SDL_SCANCODE_{c}")
    #     SDL[k] = c

    def handle_key_down(self, scancode: int):
        k = self._key_map.get(scancode)
        if isinstance(k, tuple):
            for x in k:
                self.push(x)
        elif k is not None:
            self.push(k)
        elif self.unknown_key is not None:
            self.unknown_key(scancode)

    def handle_key_up(self, scancode: int):
        k = self._key_map.get(scancode)
        if isinstance(k, tuple):
            for x in k:
                self.release(x)
        elif k is not None:
            self.release(k)

    @classmethod
    def test(cls):
        k = cls()
        k.push("A")
        print(k._a_values)
        print(k._b_values)
        for i in range(8):
            print(k.by_a(1 << i))
        for i in range(8):
            print(k.by_b(1 << i))


# def to_sdlname(k):
#     import sdl2
#     for e in dir(sdl2):
#         if getattr(sdl2, e) == k:
#             print("SDL: ", k, "==", e)
#     else:
#         print("Not found")

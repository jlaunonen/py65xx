# -*- coding: utf-8 -*-
# Copyright (C) 2021  Jyrki Launonen

import sdl2


def keyboard_map():
    # Special keys.
    keys = {
        sdl2.SDL_SCANCODE_RETURN: "RETURN",
        sdl2.SDL_SCANCODE_SPACE: "SPACE",
        sdl2.SDL_SCANCODE_BACKSPACE: "DELETE",
        sdl2.SDL_SCANCODE_LSHIFT: "LSHIFT",
        sdl2.SDL_SCANCODE_RSHIFT: "RSHIFT",
        sdl2.SDL_SCANCODE_ESCAPE: "STOP",
        sdl2.SDL_SCANCODE_HOME: "HOME",
        sdl2.SDL_SCANCODE_DOWN: "DOWN",
        sdl2.SDL_SCANCODE_RIGHT: "RIGHT",
        sdl2.SDL_SCANCODE_UP: ("LSHIFT", "DOWN"),
        sdl2.SDL_SCANCODE_LEFT: ("LSHIFT", "RIGHT"),
        sdl2.SDL_SCANCODE_SEMICOLON: ":",
        sdl2.SDL_SCANCODE_APOSTROPHE: ";",
        sdl2.SDL_SCANCODE_F1: "F1",
        sdl2.SDL_SCANCODE_F2: ("LSHIFT", "F1"),
        sdl2.SDL_SCANCODE_F3: "F3",
        sdl2.SDL_SCANCODE_F4: ("LSHIFT", "F3"),
        sdl2.SDL_SCANCODE_F5: "F5",
        sdl2.SDL_SCANCODE_F6: ("LSHIFT", "F5"),
        sdl2.SDL_SCANCODE_F7: "F7",
        sdl2.SDL_SCANCODE_F8: ("LSHIFT", "F7"),
        sdl2.SDL_SCANCODE_LCTRL: "CTRL",
        sdl2.SDL_SCANCODE_RCTRL: "CTRL",
        sdl2.SDL_SCANCODE_COMMA: ",",
        sdl2.SDL_SCANCODE_PERIOD: ".",
        sdl2.SDL_SCANCODE_SLASH: "/",
        sdl2.SDL_SCANCODE_MINUS: "-",
        sdl2.SDL_SCANCODE_BACKSLASH: "*",
        sdl2.SDL_SCANCODE_KP_PLUS: "+",
        sdl2.SDL_SCANCODE_KP_DIVIDE: "=",
        sdl2.SDL_SCANCODE_KP_MULTIPLY: "£",
        sdl2.SDL_SCANCODE_NONUSBACKSLASH: "<-",
        sdl2.SDL_SCANCODE_PAGEUP: "^",
        sdl2.SDL_SCANCODE_LEFTBRACKET: "@",
        sdl2.SDL_SCANCODE_GRAVE: "C=",
    }
    # Number keys.
    for i in range(10):
        k = getattr(sdl2, f"SDL_SCANCODE_{i}")
        keys[k] = str(i)
    # Alpha keys.
    for i in range(ord("a"), ord("z") + 1):
        c = chr(i).upper()
        k = getattr(sdl2, f"SDL_SCANCODE_{c}")
        keys[k] = c

    return keys


def unknown_key_handler(k):
    for e in dir(sdl2):
        if getattr(sdl2, e) == k:
            print("SDL: ", k, "==", e)
    else:
        print("Not found")

# Py65xx

A dumb emulator for 65xx-series CPU.
Why? For fun.

Note, that this emulation is not cycle-accurate nor performant.
Depending on configuration, the emulation speed might spend 2–22 times
more time per cycle than a real 65xx CPU.


## Testing

[test_instructions.py](test_instructions.py) contains a simple setup to run
[test suite made by Klaus2m5](https://github.com/Klaus2m5/6502_65C02_functional_tests).
It runs about 53 million cycles, so it takes a while.


## Acknowledgements

- The 6502_65C02_functional_tests was great supplement to implement things right.
- Idea spun from [OneLoneCoder NES Emulator video](https://www.youtube.com/watch?v=8XmxKPJDGU0). How hard can it be?


# PyC64

A simple ('ish) Commodore 64 emulator using the py65xx as the CPU.

To actually run this, you need `kernal`, `basic` and `chargen` rom files in the root of the project.
Also requires pysdl2.


## Current features

- Screen (by "snapshots", i.e. one screen at a time instead of streamed pixel per pixel).
- High resolution, multicolor and extended background text modes.
- High resolution and multicolor bitmap modes.
- Keyboard.
- Single file program injection from .PRG or single-file .T64.
- Scrolling (mostly).
- Light pen (by mouse click, might not work correctly).


## Limitations

Since the CPU emulation speed is horrendous, this is not better.
Screen updates happen every 40k cycles which would result 25fps IF the emulation could run that
fast (and the cycles were calculated correctly). In reality, that's probably somewhere around 5 fps.

- Because the screen updates are quantized, mixed mode graphics do not work.
- No sprites (aka MOBs).
- No audio.
- No actual I/O such as disk drive or tape.
  This means that the only way to load anything is to inject it directly into the memory using F9.
- Input from real keyboard to emulation is also quantized to same frequency as screen updates
  so keys need to be pressed a while for them to appear into the screen.
- No game controller support, although this shouldn't be too hard to implement because keyboard is
  already working. Whether any game can actually be played with this is different question, though.


## Keyboard layout

    C= 1 2 3 4 5 6 7 8 9 0 -
       Q W E R T Y U I O P @
       A S D F G H J K L : ; *
    <- Z X C V B N M , . /

Shift:

       ! " # $ % & ´ ( ) 0 |

                         [ ] –
                     < > ?

- `ESC` = RUN/STOP
- `BREAK` = RESTORE
- `HOME` = HOME
- `KP-PLUS` = `+`
- `KP-DIV` = `=`
- `KP-MUL` = `£`
- `PGUP` = UPARROW (power operator)
- `F9` = load and run next program
- `F11` = cold restart
- `F12` = debug (dump memory, to be changed...)


## Acknowledgements

- Various internet resources for information.
- VICE for some times being a (black box) reference.
  - Cyan and both blue color values are sourced from c64s palette.

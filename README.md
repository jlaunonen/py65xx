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

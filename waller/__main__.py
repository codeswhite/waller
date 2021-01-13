#!env python3
# coding=utf-8

import curses
import random
import os, sys

from interutils import pr

from .waller import curses_entry, Waller

def parse_args() -> (str, None):
    if len(sys.argv) < 2:
        return

    run_mode = sys.argv[1].lower()
    if run_mode in ('r', 'n', 'p'):
        return run_mode


def main():
    if os.getuid() == 0:
        print("[X] This program shouldn't run as root!")
        exit(3)

    # Parse args
    batch = parse_args()

    if batch:
        # Batch mode
        w = Waller(None)
        # Get current wallpaper
        _, current_id = w.get_current_wall()

        if batch == 'r':
            current_id = random.randint(0, len(w.available))
        elif batch == 'n':
            current_id += 1
            if current_id >= len(w.available):
                current_id = 0
        elif batch == 'p':
            current_id -= 1
            if current_id < 0:
                current_id = len(w.available) - 1
        w.apply(current_id)

    else:
        try:
            curses.wrapper(curses_entry)

        except curses.error:
            print('[X] An curses error occurred!')
            from traceback import print_exc

            print_exc()


if __name__ == '__main__':
    main()

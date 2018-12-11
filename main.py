#!/usr/bin/env python3
# coding=utf-8

""" Return Codes:
    0 == OK
    1 == Wallpaper not found
    3 == Running as root (don't)
"""

import curses
from os import listdir, path, getuid
from random import randint
from subprocess import check_output, call

from utils import banner, pr

directory = '/home/maximus/wallpapers'


def init_curses():
    curses.use_default_colors()
    curses.init_pair(2, curses.COLOR_RED, -1)
    curses.init_pair(3, curses.COLOR_GREEN, -1)
    curses.init_pair(4, curses.COLOR_BLUE, -1)
    curses.init_pair(5, curses.COLOR_YELLOW, -1)


def clear_win(win):
    win.clear()
    win.addstr(banner('Wall'), curses.color_pair(4))


def get_monitors():
    for line in check_output('xrandr').decode().split('\n'):
        if 'connected' in line:
            yield line.split(' ')[0]


def get_cmd(monitor_id: int):
    return ['xfconf-query', '-c', 'xfce4-desktop', '-p',
            '/backdrop/screen0/monitor%d/workspace0/last-image' % monitor_id]


def apply(name, mon_id):
    cmd = get_cmd(mon_id) + ['-s', path.join(directory, name)]
    call(cmd)


def main(win):
    init_curses()

    mon_id = 0
    mons = tuple(get_monitors())

    while 1:  # Monitor l00p
        clear_win(win)

        # Get current wallpaper path & available wallpapers
        current = check_output(get_cmd(mon_id))[:-1].decode()
        available = sorted([i for i in listdir(directory) if
                            len([f for f in ('png', 'jpg', 'jpeg') if i.endswith('.' + f)])])
        try:
            cid = available.index(path.split(current)[1])
        except ValueError:
            win.addstr('[X] Current wall not found in %s\n' % directory, curses.color_pair(2))
            win.addstr('[+] Press [R] to reset to the first image from the supported directory', curses.color_pair(5))
            if win.getkey() != 'r':
                exit(1)
            cid = 0
            current = available[cid]
            apply(current, mon_id)

        while 1:
            clear_win(win)

            # show info
            if len(mons) > 1:
                win.addstr('[+] Using monitor: ')
                win.addstr('%s\n' % mons[mon_id], curses.color_pair(3))
            win.addstr('[+] Current wall: ')
            win.addstr('%s (%d/%d)' % (path.split(current)[1], cid + 1, len(available)), curses.color_pair(3))

            o = str(win.getkey()).lower()
            if not o:
                continue

            if o == 'r':
                cid = randint(0, len(available))
            elif o == 'key_left':
                cid -= 1
                if cid < 0:
                    cid = len(available) - 1
            elif o == 'key_right':
                cid += 1
                if cid >= len(available):
                    cid = 0
            elif o == 'm':
                mon_id += 1
                if mon_id >= len(mons):
                    mon_id = 0
                break  # Back to monitor loop

            # Application
            current = available[cid]
            apply(current, mon_id)


if __name__ == '__main__':
    if getuid() == 0:
        pr("This program shouldn't run as root!", 'X')
        exit(3)

    try:
        curses.wrapper(main)
    except KeyboardInterrupt:
        pass  # Normal exit

    except curses.error:
        pr('An curses error occurred!', 'X')
        from traceback import print_exc

        print_exc()

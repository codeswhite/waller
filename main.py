#!/usr/bin/env python3
# coding=utf-8

"""
[*] Return Codes:
0 == OK
1 == Wallpaper not found
3 == Running as root (don't)

[*] TODO
CHECK & SET permissions of all 'available' images,
don't forget to set 'o+r' for the image that is used in the 'LightDM GTK greeter'
"""

import curses
from os import listdir, path, getuid
from random import randint
from subprocess import check_output, call
from typing import List, Generator

from utils import banner, pr, is_image

DIRECTORY = '/home/maximus/wallpapers'


def clear_win(win) -> None:
    """
    A simple function to clear the screen and print our banner :)
    :param win: The curses window
    :return: Nope
    """
    win.clear()
    win.addstr(banner('Wall'), curses.color_pair(4))


def get_lightdm() -> str:
    """
    A function that will return the path of the image that is used by the "LightDM GTK greeter"
    :return: The full path to the image
    """
    conf = '/etc/lightdm/lightdm-gtk-greeter.conf'
    with open(conf) as file:
        for line in file:
            if line.startswith('background'):
                return line.strip().split(' ')[2]

    raise LookupError("Couldn't fetch the background path from 'LightDM GTK greeter' config file!")


def get_monitors() -> Generator[str, str, None]:
    """
    Runs xRandr to check which monitors are connected
    :return: Monitor names
    """
    for line in check_output('xrandr').decode().split('\n'):
        if 'connected' in line:
            yield line.split(' ')[0]


def get_cmd(monitor_id: int) -> List[str]:
    """
    The system command which will return path of monitor's wallpaper
    """

    return ['xfconf-query', '-c', 'xfce4-desktop', '-p',
            '/backdrop/screen0/monitor%d/workspace0/last-image' % monitor_id]


def apply(name, mon_id) -> None:
    """
    The application function

    :param name: Image name in the directory
    :param mon_id: Desired monitor ID
    """

    cmd = get_cmd(mon_id) + ['-s', path.join(DIRECTORY, name)]
    call(cmd)


def main(win) -> None:
    """
    A Program to switch between wallpapers from a specified directory across various monitors
    """
    # Curses initialization
    curses.use_default_colors()
    curses.init_pair(2, curses.COLOR_RED, -1)
    curses.init_pair(3, curses.COLOR_GREEN, -1)
    curses.init_pair(4, curses.COLOR_BLUE, -1)
    curses.init_pair(5, curses.COLOR_YELLOW, -1)

    mon_id = 0
    mons = tuple(get_monitors())

    while 1:  # Monitor l00p
        clear_win(win)

        # Get current wallpaper path & available wallpapers
        stream = bytes(check_output(get_cmd(mon_id)))
        current = stream.strip().decode()

        available = sorted([i for i in listdir(DIRECTORY) if is_image(path.join(DIRECTORY, i))])

        current_name = path.split(current)[1]
        try:
            cid = available.index(current_name)
        except ValueError:
            win.addstr('[X] Current wall "%s" not found in %s\n' %
                       (current_name, DIRECTORY), curses.color_pair(2))
            win.addstr('[+] Press [R] to reset to the first image', curses.color_pair(5))
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
            win.addstr('%s (%d/%d)' % (path.split(current)[1], cid + 1,
                                       len(available)), curses.color_pair(3))

            key = str(win.getkey()).lower()
            if not key:
                continue
            elif key in ('x', 'q'):
                return
            elif key == 'm':
                mon_id += 1
                if mon_id >= len(mons):
                    mon_id = 0
                break  # Back to monitor loop

            if key == 'r':
                cid = randint(0, len(available))
            elif key == 'key_left':
                cid -= 1
                if cid < 0:
                    cid = len(available) - 1
            elif key == 'key_right':
                cid += 1
                if cid >= len(available):
                    cid = 0

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
        pass

    except curses.error:
        pr('An curses error occurred!', 'X')
        from traceback import print_exc

        print_exc()

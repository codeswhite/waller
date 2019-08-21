#!/usr/bin/env python3
# coding=utf-8

"""
[*] Return Codes:
0 == OK
1 == Wallpaper not found
3 == Running as root (don't)

TODO:
* Add commands:
* Structure: pop a main menu function
* Add support for multiple LDM greeters (and DMs)
* Fix: current image name not changing
* Fix: when pressing [M] check for the existance of the next monitor
  and pop a message for the user if the monitor not present
"""

import curses
import os
import stat
import random
from subprocess import check_output, check_call, call, CalledProcessError
from typing import List, Iterator, Tuple

from utils import banner, pr, is_image

from ldm_gtk import LdmGtk
from conf import Config


def clear_win(win) -> None:
    """
    A simple function to clear the screen and print our banner :)
    :param win: The curses window
    :return: Nope
    """
    win.clear()
    win.addstr(banner('Wall'), curses.color_pair(4))


def get_cmd(monitor_id: int) -> List[str]:
    """
    The system command which will return path of monitor's wallpaper
    """
    return ['xfconf-query', '-c', 'xfce4-desktop', '-p',
            f'/backdrop/screen0/monitor{monitor_id}/workspace0/last-image']


def apply(path, mon_id) -> None:
    """
    The application function

    :param path: Image absolute path
    :param mon_id: Desired monitor ID
    """
    cmd = get_cmd(mon_id) + ['-s', path]
    call(cmd)


def reset_permissions(current_dir: str, avail: tuple, ldm_bg_path: str) -> None:
    """
    Sets proper permissions [400] for all the images
     and [404] for the DM background image
    :param avail: Available images
    :param ldm_bg_path: DM's background image path
    """
    for wall in avail:
        path = os.path.join(current_dir, wall)
        perm = stat.S_IRUSR
        if path == ldm_bg_path:
            perm |= stat.S_IROTH
        os.chmod(path, perm)


def collect_available(current_dir: str) -> Iterator[str]:
    """
    Collect available images in the specified directory
    :param current_dir: Current wallpapers directory
    :return: File-names
    """
    for wall in os.listdir(current_dir):
        if is_image(os.path.join(current_dir, wall)):
            yield wall


def collect_monitors() -> Iterator[list]:
    """
    Collect connected monitors, via xRandr
    :return: Monitor names
    """
    for line in check_output('xrandr').decode().split('\n'):
        if 'connected' in line:
            seg = line.split(' ')
            if 'disconnected' in seg:
                continue
            yield seg[0]


def get_current_wall(win, current_dir: str, monitor_id: int, available: tuple) -> Tuple[str, int]:
    """
    Find currently used wallpaper for the specific monitor-ID and return its name,
    as well as the index of the file in the directory

    :param win: Curses window handle
    :param current_dir: Current wallpapers directory
    :param monitor_id: Specified monitor
    :param available: Available images
    :return: A tuple of (IMG-NAME, IMG-ID)
    """
    stream = bytes(check_output(get_cmd(monitor_id)))
    name = os.path.split(stream.strip().decode())[1]

    try:
        return name, available.index(name)

    except ValueError:
        win.addstr(
            f'[X] Current wall "{name}" not found in {current_dir}\n', curses.color_pair(2))
        win.addstr('[+] Press [R] to reset to the first image',
                   curses.color_pair(5))
        if win.getkey() != 'r':
            exit(1)

        # Set current to first
        current_id = 0
        name = available[current_id]
        apply(os.path.join(current_dir, name), monitor_id)
        return name, current_id


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

    # Init config
    conf = Config('/home/maximus/.config/wall.json')
    current_dir = conf.current()

    # Get 'LDM GTK greeter' wallpaper
    ldm_bg_path = LdmGtk.get_bg()

    # Get available
    available = tuple(collect_available(current_dir))

    # Set permissions
    reset_permissions(current_dir, available, ldm_bg_path)

    # Check monitors
    mon_id = 0
    mons = tuple(collect_monitors())

    # while 1:  # Monitor Loop
    #     clear_win(win)

    while 1:  # Inner Loop
        clear_win(win)

        # Get current wallpaper
        current_name, current_id = get_current_wall(
            win, current_dir, mons[mon_id], available)

        # show info
        if len(mons) > 1:
            win.addstr('[*] Using monitor: ')
            win.addstr(f'{mons[mon_id]}\n', curses.color_pair(3))
        win.addstr('[+] Current wall: ')
        win.addstr(
            f'({current_id + 1}/{len(available)}) {current_name}\n', curses.color_pair(3))

        win.addstr('\n>> Controls: [<] or [>] or [R]\n' +
                   '[L] to set LDM GTK background\n')
        if len(mons) > 1:
            win.addstr('[M] to switch monitor\n', curses.color_pair(5))
        win.addstr('[X] or [Q] to exit\n', curses.color_pair(5))

        key = str(win.getkey()).lower()
        if not key:
            continue
        elif key in ('x', 'q'):
            return
        elif key == 'm':
            if len(mons) == 1:
                continue
            mon_id += 1
            if mon_id >= len(mons):
                mon_id = 0
            continue
        elif key == 'r':  # Random
            current_id = random.randint(0, len(available))
        elif key == 'key_left':
            current_id -= 1
            if current_id < 0:
                current_id = len(available) - 1
        elif key == 'key_right':
            current_id += 1
            if current_id >= len(available):
                current_id = 0

        # DM background
        elif key == 'l':
            new_bg = available[current_id]
            if not LdmGtk.set_bg(win, os.path.split(ldm_bg_path)[1], new_bg):
                continue

            ldm_bg_path = os.path.join(current_dir, new_bg)
            reset_permissions(current_dir, available, ldm_bg_path)
            continue

        # Application
        apply(os.path.join(current_dir, available[current_id]), mons[mon_id])


if __name__ == '__main__':
    if os.getuid() == 0:
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

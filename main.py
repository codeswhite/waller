#!/usr/bin/env python3
# coding=utf-8

"""
[*] Return Codes:
0 == OK
1 == Wallpaper not found
3 == Running as root (don't)

TODO:
* Add support for multiple LDM greeters (and DMs)
"""

import curses
import os
import stat
from random import randint
from subprocess import check_output, check_call, call, CalledProcessError
from typing import List, Generator, Tuple

from utils import banner, pr, is_image

DIRECTORY = '/home/maximus/wallpapers'
LDM_GTK_CONF = '/etc/lightdm/lightdm-gtk-greeter.conf'


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
            '/backdrop/screen0/monitor%d/workspace0/last-image' % monitor_id]


def apply(name, mon_id) -> None:
    """
    The application function

    :param name: Image name in the directory
    :param mon_id: Desired monitor ID
    """
    cmd = get_cmd(mon_id) + ['-s', os.path.join(DIRECTORY, name)]
    call(cmd)


def get_ldm_bg() -> str:
    """
    Fetch the background image of the LDM's GTK greeter from the config file
    :return: Full path to the background image
    """
    with open(LDM_GTK_CONF) as ldm_file:
        for line in ldm_file:
            if line.startswith('background'):
                return line.strip().split(' ')[2]
    raise LookupError("[ERR] Couldn't find the LDM greeter's background!")


def set_ldm_bg(win, ldm_bg_name, wall_name) -> bool:
    """
    Set the background image of the LDM's GTK greeter in the config file
    :return: True on success
    """
    if ldm_bg_name == wall_name:
        win.addstr('[!] Cannot change DM background to the same one!\n', curses.color_pair(5))
        win.getkey()
        return False

    try:
        check_call("sudo sed -i 's/%s/%s/g' " % (ldm_bg_name, wall_name) + LDM_GTK_CONF, shell=True)
    except (KeyboardInterrupt, PermissionError, CalledProcessError):
        win.addstr("[X] An external error occurred while change DM's background!\n",
                   curses.color_pair(2))
        win.getkey()
        return False

    win.addstr('[+] Lock-screen background replaced!\n', curses.color_pair(3))
    win.getkey()
    return True


def reset_permissions(avail: tuple, ldm_bg_path: str) -> None:
    """
    Sets proper permissions [400] for all the images
     and [404] for the DM background image
    :param avail: Available images
    :param ldm_bg_path: DM's background image path
    """
    for wall in avail:
        path = os.path.join(DIRECTORY, wall)
        perm = stat.S_IRUSR
        if path == ldm_bg_path:
            perm |= stat.S_IROTH
        os.chmod(path, perm)


def collect_available() -> Generator[str, str, None]:
    """
    Collect available images in the specified directory
    :return: File-names
    """
    for wall in os.listdir(DIRECTORY):
        if is_image(os.path.join(DIRECTORY, wall)):
            yield wall


def collect_monitors() -> Generator[str, str, None]:
    """
    Collect connected monitors, via xRandr
    :return: Monitor names
    """
    for line in check_output('xrandr').decode().split('\n'):
        if 'connected' in line:
            yield line.split(' ')[0]


def get_current_wall(win, monitor_id: int, available: tuple) -> Tuple[str, int]:
    """
    Find currently used wallpaper for the specific monitor-ID and return its name,
    as well as the index of the file in the directory

    :param win: Curses window handle
    :param monitor_id: Specified monitor
    :param available: Available images
    :return: A tuple of (IMG-NAME, IMG-ID)
    """
    stream = bytes(check_output(get_cmd(monitor_id)))
    name = os.path.split(stream.strip().decode())[1]

    try:
        return name, available.index(name)

    except ValueError:
        win.addstr('[X] Current wall "%s" not found in %s\n' %
                   (name, DIRECTORY), curses.color_pair(2))
        win.addstr('[+] Press [R] to reset to the first image', curses.color_pair(5))
        if win.getkey() != 'r':
            exit(1)

        # Set current to first
        current_id = 0
        name = available[current_id]
        apply(name, monitor_id)
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

    # Get 'LDM GTK greeter' wallpaper
    ldm_bg_path = get_ldm_bg()

    # Get available
    available = tuple(collect_available())

    # Set permissions
    reset_permissions(available, ldm_bg_path)

    # Check monitors
    mon_id = 0
    mons = tuple(collect_monitors())

    while 1:  # Monitor Loop
        clear_win(win)

        # Get current wallpaper
        current_name, current_id = get_current_wall(win, mon_id, available)

        while 1:  # Inner Loop
            clear_win(win)

            # show info
            if len(mons) > 1:
                win.addstr('[+] Using monitor: ')
                win.addstr('%s\n' % mons[mon_id], curses.color_pair(3))
            win.addstr('[+] Current wall: ')
            win.addstr('%s (%d/%d)\n' % (current_name, current_id + 1,
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
                current_id = randint(0, len(available))
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
                if not set_ldm_bg(win, os.path.split(ldm_bg_path)[1], new_bg):
                    continue

                ldm_bg_path = os.path.join(DIRECTORY, new_bg)
                reset_permissions(available, ldm_bg_path)
                continue

            # Application
            apply(available[current_id], mon_id)


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

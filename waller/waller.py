
import curses
import os
import stat
import random
import sys
from pathlib import PosixPath
from subprocess import check_output, check_call, call, CalledProcessError
from typing import List, Iterator, Tuple

from .ldm_gtk import LdmGtk


def get_cmd(monitor_name: str) -> List[str]:
    """
    The system command which will return path of monitor's wallpaper
    * Depends on 'xfconf'
    """
    return ['xfconf-query', '-c', 'xfce4-desktop', '-p',
            f'/backdrop/screen0/monitor{monitor_name}/workspace0/last-image']


def img_format(image_path: PosixPath) -> (str, None):
    """
    Checks the file signature (magic number)
            for an image

    :param image_path: The path to the image
    :return: True if the image is PNG or JPG
    """

    signatures = {'JPG': 'ffd8ff',
                  'PNG': '89504e',
                  'GIF': '474946'}

    with image_path.open('rb') as img_file:
        signature = img_file.read(3).hex()
        for sig in signatures:
            if signature == signatures[sig]:
                return sig
    return None


def collect_monitors() -> Iterator[str]:
    """
    Collect connected monitors, via xRandr
    :return: Monitor names
    """
    for line in check_output('xrandr').decode().split('\n'):
        if ' connected' in line:
            yield line.split(' ')[0]


class Waller:
    def __init__(self, win):
        super().__init__()
        self.win = win

        # Check monitors
        self.mon_id = 0
        self.mons = tuple(collect_monitors())

        # Get currently used wallaper
        current_path = self.get_current_wall()
        self.current_name = current_path.name
        self.current_dir = current_path.parent.resolve()

        # Get 'LDM GTK greeter' wallpaper
        self.ldm_bg_path = PosixPath(LdmGtk.get_bg())

        # Get available
        self.available = tuple(self.collect_available())

        # Set permissions
        self.reset_permissions()

        if win is None:
            return
        try:
            self.interactive()
        except KeyboardInterrupt:
            pass
        # finally:
        #     config.save()

    def interactive(self):
        while 1:  # Inner Loop
            self.win.clear()

            # Get current wallpaper
            self.current_name = self.get_current_wall().name
            current_id = self.get_current_id()

            self.show_info(
                f'({current_id + 1}/{len(self.available)}) {self.current_name}\n')

            key = str(self.win.getkey()).lower()
            if not key:
                continue
            elif key in ('x', 'q'):
                return
            elif key == 'm':
                if len(self.mons) == 1:
                    continue
                self.mon_id += 1
                if self.mon_id >= len(self.mons):
                    self.mon_id = 0
                continue
            elif key == 'r':  # Random
                current_id = random.randint(0, len(self.available))
            elif key == 'key_left':
                current_id -= 1
                if current_id < 0:
                    current_id = len(self.available) - 1
            elif key == 'key_right':
                current_id += 1
                if current_id >= len(self.available):
                    current_id = 0
            elif key == 'l':  # DM background
                self.change_ldm_bg(self.available[current_id])
                continue
            else:
                continue

            # Application
            self.apply(current_id)

    def get_mon(self) -> str:
        return self.mons[self.mon_id]

    def apply(self, current_id: int) -> None:
        """
        The application function
        """
        path = self.current_dir / self.available[current_id]
        cmd = get_cmd(self.get_mon()) + ['-s', path]
        call(cmd)

    def show_info(self, current: str) -> None:
        if len(self.mons) > 1:
            self.win.addstr('[*] Using monitor: ')
            self.win.addstr(
                f'{self.get_mon()}\n', curses.color_pair(3))
        self.win.addstr('[+] Current wall: ')
        self.win.addstr(current, curses.color_pair(3))

        self.win.addstr('\n>> Controls: [<] or [>] or [R]\n' +
                        '[L] to set LDM GTK background\n')
        if len(self.mons) > 1:
            self.win.addstr('[M] to switch monitor\n',
                            curses.color_pair(5))
        self.win.addstr('[X] or [Q] to exit\n', curses.color_pair(5))

    def change_ldm_bg(self, new_bg: str) -> None:
        if not LdmGtk.set_bg(self.win, self.ldm_bg_path.name, new_bg):
            return

        self.ldm_bg_path = self.current_dir / new_bg
        self.reset_permissions()

    def reset_permissions(self) -> None:
        """
        Sets proper permissions [400] for all the images
        and [404] for the DM background image
        :param avail: Available images
        :param ldm_bg_path: DM's background image path
        """
        for wall in self.available:
            path = self.current_dir / wall
            perm = stat.S_IRUSR
            if path == self.ldm_bg_path:
                perm |= stat.S_IROTH
            os.chmod(path, perm)

    def collect_available(self) -> Iterator[str]:
        """
        Collect available images in the specified directory
        :param current_dir: Current wallpapers directory
        :return: File-names
        """
        for wall in os.listdir(self.current_dir):
            if img_format(self.current_dir / wall):
                yield wall

    def get_current_wall(self) -> PosixPath:
        """
        :return: A Path to the current image of primary monitor
        """
        return PosixPath(check_output(get_cmd(self.get_mon())).decode().strip())

    def get_current_id(self) -> int:
        """
        :return: index of current image among other images in the same directory
        """
        try:
            return self.available.index(self.current_name)

        except ValueError:
            self.win.addstr(
                f'[X] Current wall "{self.current_name}" not found in {self.current_dir}\n', curses.color_pair(2))
            self.win.addstr('[+] Press [R] to reset to the first image',
                            curses.color_pair(5))
            if self.win.getkey() != 'r':
                exit(1)

            # Set current to first
            current_id = 0
            self.current_name = self.available[current_id]
            apply(self.current_dir / self.current_name, self.mon_id)
            return current_id


def curses_entry(win: curses.window) -> None:
    # Curses initialization
    curses.use_default_colors()
    curses.init_pair(2, curses.COLOR_RED, -1)
    curses.init_pair(3, curses.COLOR_GREEN, -1)
    curses.init_pair(4, curses.COLOR_BLUE, -1)
    curses.init_pair(5, curses.COLOR_YELLOW, -1)

    Waller(win)

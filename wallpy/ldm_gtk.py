import curses
import subprocess


class LdmGtk:
    LDM_GTK_CONF = '/etc/lightdm/lightdm-gtk-greeter.conf'

    @staticmethod
    def get_bg() -> str:
        """
        Fetch the background image of the LDM's GTK greeter from the config file
        :return: Full path to the background image
        """
        with open(LdmGtk.LDM_GTK_CONF) as ldm_file:
            for line in ldm_file:
                if line.startswith('background'):
                    return line.strip().split(' ')[2]
        raise LookupError(
            "[ERR] Couldn't locate the LDM greeter's background!")

    @staticmethod
    def set_bg(win, ldm_bg_name: str, wall_name: str) -> bool:
        """
        Set the background image of the LDM's GTK greeter in the config file
        :return: True on success
        """
        if ldm_bg_name == wall_name:
            win.addstr(
                '[!] Cannot change DM background to the same one!\n', curses.color_pair(5))
            win.getkey()
            return False

        try:
            subprocess.check_call(
                ['sudo', 'sed', '-i', f"s/{ldm_bg_name}/{wall_name}/g", LdmGtk.LDM_GTK_CONF])
        except (KeyboardInterrupt, PermissionError, subprocess.CalledProcessError):
            win.addstr("[X] An external error occurred while change DM's background!\n",
                       curses.color_pair(2))
            win.getkey()
            return False

        win.addstr('[+] Lock-screen background replaced!\n',
                   curses.color_pair(3))
        win.getkey()
        return True

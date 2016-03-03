#!/usr/bin/env python3

# Copyright (c) 2016 Stanislav Kontar
# License: MIT

"""
Update Checker is a simple application used to check for updates on Fedora 22+ systems (e.g. the
ones using DNF as package manager). It is meant for XFCE desktop environment but should be working
in any desktop environment supporting notifications and system tray notification icons with slight
modification.

It checks for updates in time intervals and notifies user about updates being ready by notification
and yellow/red icon (for regular/security updates). As a default it only cares about security
updates and checks every 4 hours.
"""

import argparse
from os import path
from subprocess import Popen, PIPE, call
import sys
from threading import Thread

import gi
gi.require_version('Gtk', '3.0')
gi.require_version('Notify', '0.7')
from gi.repository import GLib, Gtk, Notify  # @IgnorePep8


COMMAND_DNF_UPDATEINFO = 'nice -n 19 dnf updateinfo list updates'
COMMAND_DNF_UPGRADE = 'sudo dnf upgrade'
BASH_COMMAND = 'bash -c \'echo {dnf}; {dnf}; read -p "Press ENTER to close window"\''
COMMAND_TERMINAL = 'xfce4-terminal --maximize -x {}'.format(BASH_COMMAND)
COMMAND_TERMINAL_DROPDOWN = 'xfce4-terminal --tab --title Update --drop-down -x {}'.format(BASH_COMMAND)

WD = path.dirname(path.abspath(sys.argv[0]))  # Manage to run script anywhere in the path
ICON_YELLOW = path.join(WD, 'Hopstarter-Soft-Scraps-Button-Blank-Yellow.ico')
ICON_RED = path.join(WD, 'Hopstarter-Soft-Scraps-Button-Blank-Red.ico')


def dnf_check_updates():
    """
    Get list of updates using dnf and categorize by update type.

    Returns:
        (dict): dictionary of lists of updated packages classified by update type
    """
    p = Popen(COMMAND_DNF_UPDATEINFO, shell=True, stdout=PIPE, stderr=PIPE)
    result = p.communicate()
    stdout_data = [a.decode('utf-8') for a in result[0].split(b'\n')]
    updates = {'bugfix': [], 'enhancement': [], 'security': []}
    for line in stdout_data:
        if any(a in line for a in updates.keys()):
            update_type, package = line.split()[1:]
            package_name = '-'.join(package.split('-')[:-2])
            updates[update_type].append(package_name)
    return updates


def dnf_upgrade(normal_terminal=False, packages=None):
    """
    Run terminal and start dnf upgrade command.

    Args:
        normal_terminal (bool): use command in normal terminal window, dropdown terminal is used
                                by default
        packages (list): list of packages to upgrade, all packages are updated by default
    """
    if normal_terminal:
        command = COMMAND_TERMINAL
    else:
        command = COMMAND_TERMINAL_DROPDOWN
    if packages is None:
        call(command.format(dnf=COMMAND_DNF_UPGRADE), shell=True)
    else:
        call(command.format(dnf=COMMAND_DNF_UPGRADE + ' ' + ' '.join(packages)), shell=True)


class Application:
    def __init__(self, all_updates, normal_terminal, interval):
        self.normal_terminal = normal_terminal
        self.all_updates = all_updates
        self.interval = interval
        self.worker_check_thread = None
        self.worker_upgrade_thread = None
        self.notification = None
        self.updates = None
        self.updates_nr = 0
        self.security_updates_nr = 0

        # Status icon
        self.status_icon = Gtk.StatusIcon(visible=False)

        # Menu
        self.menu = Gtk.Menu()

        upgrade_security = Gtk.ImageMenuItem('Upgrade security')
        upgrade_security.set_image(Gtk.Image.new_from_icon_name(Gtk.STOCK_STOP, Gtk.IconSize.MENU))
        upgrade_security.connect('activate', self.on_menu_upgrade_security, None)
        self.menu.append(upgrade_security)

        upgrade = Gtk.ImageMenuItem('Upgrade all')
        upgrade.set_image(Gtk.Image.new_from_icon_name(Gtk.STOCK_APPLY, Gtk.IconSize.MENU))
        upgrade.connect('activate', self.on_menu_upgrade, None)
        self.menu.append(upgrade)

        close = Gtk.ImageMenuItem(Gtk.STOCK_QUIT, use_stock=True)
        close.connect('activate', self.on_menu_close, None)
        self.menu.append(close)

        # Callbacks
        self.status_icon.connect('activate', self.on_icon_click)
        self.status_icon.connect('popup-menu', self.on_menu)

        # Start
        self.on_timer()
        GLib.timeout_add_seconds(self.interval * 3600, self.on_timer)

    def worker_check(self):
        """
        Runs the check for updates in another thread to not block the GUI.
        """
        self.updates = dnf_check_updates()
        self.updates_nr = sum(len(self.updates[update_type]) for update_type in self.updates)
        self.security_updates_nr = len(self.updates['security'])
        if (self.updates_nr > 0 and self.all_updates) or self.security_updates_nr > 0:
            GLib.idle_add(self.found_updates)
        else:
            GLib.idle_add(self.no_updates)

    def worker_upgrade(self, all_packages=False):
        """
        Runs DNF update based on user preferences in another thread to not block GUI.
        """
        if all_packages:
            dnf_upgrade(self.normal_terminal)
        else:
            dnf_upgrade(self.normal_terminal, self.updates['security'])

    def found_updates(self):
        """
        Shows appropriate status icon, tooltip and notification.
        """
        if self.security_updates_nr > 0:
            template = 'Found {} updates, {} of them are security related'
            message = template.format(self.updates_nr, self.security_updates_nr)
            self.status_icon.set_from_file(ICON_RED)
        else:
            template = 'Found {} updates'
            message = template.format(self.updates_nr)
            self.status_icon.set_from_file(ICON_YELLOW)
        self.status_icon.set_tooltip_text(message)
        self.status_icon.set_visible(True)
        self.notification = Notify.Notification.new(message)
        if self.security_updates_nr > 0:
            self.notification.add_action('clicked_upgrade_security', 'Upgrade security',
                                         self.on_notification_upgrade_security)
        self.notification.add_action('clicked_upgrade', 'Upgrade all', self.on_notification_upgrade)
        self.notification.add_action('clicked_dismiss', 'Dismiss', self.on_notification_dismiss)
        self.notification.show()

    def no_updates(self):
        self.status_icon.set_visible(False)

    def upgrade(self, all_packages=False):
        self.status_icon.set_visible(False)
        self.worker_upgrade_thread = Thread(target=self.worker_upgrade, args=[all_packages])
        self.worker_upgrade_thread.start()

    def on_timer(self):
        self.worker_check_thread = Thread(target=self.worker_check)
        self.worker_check_thread.start()
        return True

    def on_icon_click(self, sender):
        self.status_icon.set_visible(False)

    def on_menu(self, sender, button, time):
        self.menu.show_all()
        self.menu.popup(None, None, Gtk.StatusIcon.position_menu, sender, button, time)

    def on_menu_close(self, widget, event):
        for thread in (self.worker_check_thread, self.worker_upgrade_thread):
            if thread is not None:
                thread.join()
        Gtk.main_quit()

    def on_menu_upgrade(self, widget, event):
        self.upgrade(all_packages=True)

    def on_menu_upgrade_security(self, widget, event):
        self.upgrade()

    def on_notification_upgrade(self, notification, action_name):
        self.upgrade(all_packages=True)

    def on_notification_upgrade_security(self, notification, action_name):
        self.upgrade()

    def on_notification_dismiss(self, notification, action_name):
        self.status_icon.set_visible(False)
        self.notification.close()


if __name__ == '__main__':
    Notify.init('update_checker')
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument('-a', '--all', action='store_true',
                        help='report on all updates, not just security ones')
    parser.add_argument('-n', '--normal-terminal', action='store_true',
                        help='use normal terminal window, by default dropdown terminal is used')
    parser.add_argument('-i', '--interval', type=float, default=4.0,
                        help='check for updates every INTERVAL hours (can be fraction)')
    args = parser.parse_args()
    app = Application(args.all, args.normal_terminal, args.interval)
    Gtk.main()

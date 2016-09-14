# Fedora XFCE Update Checker

Update Checker is a simple application used to check for updates on Fedora 22+ systems (e.g. the
ones using DNF as package manager). It is meant for XFCE desktop environment but should be working
in any desktop environment supporting notifications and system tray notification icons with slight
modification.

It checks for updates in time intervals and notifies user about updates being ready by notification
and yellow/red icon (for regular/security updates). As a default it only cares about security
updates and checks every 4 hours.


## Installation

Prerequisites are `python3` and `python3-gobject` packages, which should be installed on Fedora by
default.

Download the application directory and put it anywhere. Add `update_checker.py` to your startup
script.


## Usage

Run `update_checker.py`. The application runs on background and appears only when updates are
detected. It also has a few commandline switches:

    -h, --help            show this help message and exit
    -a, --all             report on all updates, not just security ones
                          (default: False)
    -n, --normal-terminal
                          use normal terminal window, by default dropdown
                          terminal is used (default: False)
    -i INTERVAL, --interval INTERVAL
                          check for updates every INTERVAL hours (can be
                          fraction) (default: 4.0)


## Testing

It was tested on various Fedora 22 and Fedora 23 desktop systems, mostly XFCE spins.


## Icons artwork

Website: [IconArchive](http://www.iconarchive.com/show/soft-scraps-icons-by-hopstarter.html)  
Artist: [Hopstarter (Jojo Mendoza)](http://www.iconarchive.com/artist/hopstarter.html)  
License: [CC Attribution-Noncommercial-No Derivate 4.0](http://creativecommons.org/licenses/by-nc-nd/4.0/)


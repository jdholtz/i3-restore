# i3-restore

A simple Python and Bash script to restore your [i3] session. It works very similar to how Firefox restores a previous session.
The script can correctly restore terminal subprocesses (such as Vim and ssh) and web browser instances exactly how they were before.

Additionally, with its plugin system i3-restore can save and restore specific programs much more extensively. Currently, the Kitty
terminal has a plugin to restore tabs, windows, and scrollback. Pull Requests are welcome to add plugins for more programs!

## Table of Contents
- [Features](#features)
- [Getting Started](#getting-started)
    * [Dependencies](#dependencies)
- [Upgrading](#upgrading)
- [Configuring](#configuring)
- [Automating the Script](#automating-the-script)
    * [Saving](#saving)
    * [Restoring](#restoring)
    * [Restoring Programs in Assigned Workspaces](#restoring-programs-in-assigned-workspaces)
- [Limitations](#limitations)
- [Similar Software](#similar-software)
    * [i3-resurrect](#i3-resurrect)
- [Troubleshooting](#troubleshooting)
- [Contributing](#contributing)

## Features
i3-restore has the following features (fill out a feature request for more to be added!):
- [x] Configuration to save and restore desired terminals, web browsers, and terminal subprocesses from your latest i3 session
- [x] Automatic saving and restoring of all i3 window layouts and programs running in your current i3 session
- [x] Correct restoring of subprocesses within terminals (such as Vim and ssh) and web browser instances
- [x] Restoring Kitty terminal tabs, windows, and scrollback. Enable this using the [Kitty plugin](CONFIGURATION.md#kitty)

## Getting Started

### Dependencies
- [Python 3.10+]
- [Pip]
- [Jq]
- [Perl-anyevent-i3]
- [Xdotool]

First, download the script onto your computer
```shell
git clone https://github.com/jdholtz/i3-restore.git
cd i3-restore
```

Next, install the needed packages for the script
```shell
pip install -r requirements.txt
```

Then, verify the script is working
```shell
./i3-save
```

Make sure to read the [Configuring](#configuring) section before officially using the script to ensure programs specific
to you are set up correctly (terminals, web browsers, etc.).

To get a more comprehensive understanding of what each mode in the script provides, run
```shell
./i3-save --help
```
or
```shell
./i3-restore --help
```
\
On Gentoo you can emerge [x11-misc/i3-restore]

## Upgrading
When upgrading this script, it is important to follow the [Changelog](CHANGELOG.md) for any actions that need to be performed,
as many changes will not be made backwards compatible.

Check the version of the script
```shell
./i3-save --version
```

To upgrade, pull the latest changes from the repository
```shell
git pull
```

Again, verify the script is working
```shell
./i3-save
```

If you want the latest cutting edge features, you can use the `develop` branch. However, keep in mind that changes to this branch
do not guarantee reliability nor are changes documented in the Changelog.

## Configuring
To use the default configuration file, copy `config.example.json` to `config.json`.

For information on how to set up the configuration for your needs, see [Configuration.md](CONFIGURATION.md)

## Automating the Script
i3-restore can be automatically triggered every time i3 stops and starts. This is useful if you want to automatically restore
your session after a restart or logging out. You can also configure the script to save your session on an interval to ensure
you don't lose your current session layout if `i3-save` wasn't triggered.

### Saving
To automatically save your session before exiting i3, simply trigger `i3-save` to run by putting it in your i3 configuration file.
Example:
```
mode "exit: [l]ogout, [r]eboot, [h]ibernate, [s]leep, [p]oweroff" {
    bindsym l exec "/path/to/i3-restore/i3-save && i3-msg 'exit'"
    bindsym r exec "/path/to/i3-restore/i3-save && systemctl reboot"
    bindsym h exec systemctl hibernate
    bindsym s exec systemctl suspend
    bindsym p exec "/path/to/i3-restore/i3-save && systemctl poweroff"
    # Fallback if script fails to save
    bindsym Return exec i3-msg exit
    bindsym Escape mode "default"
}
```

### Restoring
Similarly, you can also automatically restore your session upon starting i3. To do this, simply put this line in your i3 configuration file:
```
exec /path/to/i3-restore/i3-restore
```

To automatically save your session on an interval, pass the `--save-interval` flag into the script. You can also configure how often
the save is triggered (it defaults to 10 minutes if no argument is passed in).
```
exec /path/to/i3-restore/i3-restore --save-interval <minutes>
```
**Note**: To restore web browsers correctly, you need to have their "Restore previous session" feature enabled

### Restoring Programs in Assigned Workspaces
Some programs that take a few seconds to start (such as Discord) might not restore on the correct workspace. To mitigate this issue, simply use
the [assign][assign workspace] function in i3 and add it to your i3 configuration file.

## Limitations
Due to i3-restore relying partially on program load times and i3 swallowing, there are some limitations to how it restores your process.

First, i3-restore cannot restore fully programs that it does not have permission to access. For example, this can be seen when saving a root
terminal while i3-restore is running under an unprivileged user. In this case, the window may not be placed in the same location when it is
restored (although, the program used to run the root terminal--such as `sudo` or `su`--will be called).

Second, programs that take more than a few seconds to load (such as Discord) may not be placed in the correct location. Look at
[Restoring Programs In Assigned Workspaces](#restoring-programs-in-assigned-workspaces) for information on how to make restores more reliable
for these programs.

Last, since i3-restore relies on i3 swallowing and how well individual programs can be restored to their last used state, the restoring process
is not always 100% reliable. Occasionally, windows will be in different places or not fully restored. If you have ideas or fixes for making the
restoring process, you're welcome to submit an [issue][GitHub Issues] or [pull request][GitHub Pull Request] so these can be implemented.

## Similar Software
### i3-resurrect
While [i3-resurrect] has more flexible and configurable restoring options for i3, i3-restore is designed to only restore your previous i3
session. While i3-restore can be configured to your specific use case, the default configuration is designed to be sufficient for most programs and
work out of the box. Additionally, i3-restore can be easily configured to save your session right before you log out and restore it upon login (see
[Automating the Script](#automating-the-script) for more information on how to configure that).

### tmux-resurrect
[Tmux-resurrect] is a Tmux plugin to restore your tmux environment after a system restart.

### firefox-i3-workspaces
[Firefox-i3-workspaces] is a Firefox plugin and Python script to restore multiple windows
of Firefox on i3.

## Troubleshooting
To troubleshoot a problem, run the script with the `-v` flag. This will display debug messages so you can get a better overview of the problem.
Using `-vv` will print out all commands executed by the script so you can trace through it and understand where and why a problem is occurring.

If you run into any issues, please file it via [GitHub Issues]. Please attach any relevant logs (can be found in
`logs/i3-restore.log`) to the issue. The logs may contain sensitive information such as directory names, program
launch commands, and configuration settings, so make sure to remove any information you don't want to be shared before
attaching them.

If you have any questions or discussion topics, start a [GitHub Discussion].

## Contributing
Contributions are always welcome. Please read [Contributing.md](CONTRIBUTING.md) if you are considering making contributions.

[i3]: https://github.com/i3/i3
[Python 3.10+]: https://www.python.org/downloads/
[Pip]: https://pip.pypa.io/en/stable/installation/
[Jq]: https://stedolan.github.io/jq/download/
[Perl-anyevent-i3]: https://github.com/i3/i3/blob/next/AnyEvent-I3/README
[Xdotool]: https://github.com/jordansissel/xdotool
[x11-misc/i3-restore]: https://github.com/gentoo/guru/tree/master/x11-misc/i3-restore
[assign workspace]: https://i3wm.org/docs/userguide.html#assign_workspace
[GitHub Issues]: https://github.com/jdholtz/i3-restore/issues/new/choose
[GitHub Pull Request]: https://github.com/jdholtz/i3-restore/compare
[GitHub Discussion]: https://github.com/jdholtz/i3-restore/discussions/new/choose
[i3-resurrect]: https://github.com/JonnyHaystack/i3-resurrect
[tmux-resurrect]: https://github.com/tmux-plugins/tmux-resurrect
[Firefox-i3-workspaces]: https://github.com/yurikhan/firefox-i3-workspaces

# i3-restore

A simple Python and Bash script to restore your [i3][0] session. It works very similar to how Firefox restores a previous session.
The script can correctly restore terminal sessions (such as Vim and ssh) and web browser instances exactly how they were before.

## Table of Contents
- [Getting Started](#getting-started)
    * [Dependencies](#dependencies)
- [Upgrading](#upgrading)
- [Configuring](#configuring)
- [Automating The Script](#automating-the-script)
    * [Saving](#saving)
    * [Restoring](#restoring)
    * [Restoring Programs In Assigned Workspaces](#restoring-programs-in-assigned-workspaces)
- [Troubleshooting](#troubleshooting)
- [Contributing](#contributing)

## Getting Started

### Dependencies
- [Python 3.7+][1]
- [Pip][2]
- [Jq][3]
- [Perl-anyevent-i3][4]
- [Xdotool][5]

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

## Automating The Script
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

To automatically save your session on an interval, pass the `--interval` flag into the script. You can also configure how often
the save is triggered (it defaults to 10 minutes if no argument is passed in).
```
exec /path/to/i3-restore/i3-restore --interval <minutes>
```
**Note**: To restore web browsers correctly, you need to have their "Restore previous session" feature enabled

### Restoring Programs In Assigned Workspaces
Some programs that take a few seconds to start (such as Discord) might not restore on the correct workspace. To mitigate this issue, simply use
the [assign][6] function in i3 and add it to your i3 configuration file.

## Troubleshooting
To troubleshoot a problem, run the script with the `-v` flag. This will display debug messages so you can get a better overview of the problem.
Using `-vv` will print out all commands executed by the script so you can trace through it and understand where and why a problem is occurring.

If you run into any issues, please file it via [GitHub Issues][7]. Please attach any relevant logs (can be found in
`logs/i3-restore.log`) to the issue. The logs may contain sensitive information such as directory names, program
launch commands, and configuration settings, so make sure to remove any information you don't want to be shared before
attaching them.

If you have any questions or discussion topics, start a [GitHub Discussion][8].

## Contributing
Contributions are always welcome. Please read [Contributing.md](CONTRIBUTING.md) if you are considering making contributions.

[0]: https://github.com/i3/i3
[1]: https://www.python.org/downloads/
[2]: https://pip.pypa.io/en/stable/installation/
[3]: https://stedolan.github.io/jq/download/
[4]: https://github.com/i3/i3/blob/next/AnyEvent-I3/README
[5]: https://github.com/jordansissel/xdotool
[6]: https://i3wm.org/docs/userguide.html#assign_workspace
[7]: https://github.com/jdholtz/i3-restore/issues/new/choose
[8]: https://github.com/jdholtz/i3-restore/discussions/new/choose

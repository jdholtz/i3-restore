# i3-restore

A simple Python script to restore your [i3][0] session. It works very similar to how Firefox restores a previous session.
The script can correctly restore terminal editor sessions (such as Vim) and web browser instances exactly how they were before.

## Table of Contents
- [Getting Started](#getting-started)
    * [Dependencies](#dependencies)
- [Upgrading](#upgrading)
- [Configuring](#configuring)
    * [Setting A Custom Save Path](#setting-a-custom-save-path)
    * [Configuring Special Programs To Restore Correctly](#configuring-special-programs-to-restore-correctly)
- [Automating The Script](#automating-the-script)
    * [Saving](#saving)
    * [Restoring](#restoring)
    * [Restoring Programs In Assigned Workspaces](#restoring-programs-in-assigned-workspaces)
- [Contributing](#contributing)

## Getting Started

### Dependencies
- [Python 3+][1]
- [Pip][2]
- [Jq][3]
- [Perl-anyevent-i3][4]
- [Xdotool][5]

First, download the script onto your computer
```shell
$ git clone https://github.com/jdholtz/i3-restore.git
$ cd i3-restore
```

Next, install the needed packages for the script
```shell
$ pip install -r requirements.txt
```

Then, verify the script is working
```shell
$ ./i3-save
```

## Upgrading
When upgrading this script, it is important to follow the [Changelog](CHANGELOG.md) for any actions that need to be performed,
as many changes will not be made backwards compatible.

Check the version of the script
```shell
$ ./i3-save --version
```

To upgrade, pull the latest changes from the repository
```shell
$ git pull
```

Again, verify the script is working
```shell
$ ./i3-save
```

If you want the latest cutting edge features, you can use the `develop` branch. However, keep in mind that changes to this branch
do not guarantee reliability nor are changes documented in the Changelog.

## Configuring

### Setting A Custom Save Path
By default, the layout and program files are saved under `$HOME/.config/i3`. To change this, set the `i3_PATH` environment variable to
the desired location.

### Configuring Special Programs To Restore Correctly
The configuration file the script uses to restore "special" programs (terminal editors, web browsers) is in `programs/config.py`.
If you want to add another program (or change an existing one) to the configuration file, follow the documentation in the file
to enter the correct information.

**Note**: Pull requests are always welcome, especially if you want to add a new program to the configuration file

## Automating The Script
i3-restore can be automatically triggered every time i3 stops and starts. This is useful if you want to automatically restore
your session after a restart or logging out.

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
**Note**: To restore web browsers correctly, you need to have their "Restore previous session" feature enabled

### Restoring Programs In Assigned Workspaces
Some programs that take a few seconds to start (such as Discord) might not restore on the correct workspace. To mitigate this issue, simply use
the [assign][6] function in i3 and add it to your i3 configuration file.


## Contributing
If you run into any issues, please file an issue.

Pull requests are always welcome, whether that be to fix any bugs or add new features.
Use [pre-commit][7] to automatically format your changes.

[0]: https://github.com/i3/i3
[1]: https://www.python.org/downloads/
[2]: https://pip.pypa.io/en/stable/installation/
[3]: https://stedolan.github.io/jq/download/
[4]: https://archlinux.org/packages/community/any/perl-anyevent-i3/
[5]: https://github.com/jordansissel/xdotool
[6]: https://i3wm.org/docs/userguide.html#assign_workspace
[7]: https://pre-commit.com/

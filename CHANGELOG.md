# Changelog
When upgrading to a new version, make sure to follow the directions under the "Upgrading" header of the corresponding version.
If there is no "Upgrading" header for that version, no post-upgrade actions need to be performed.


## Upcoming
### New Features
- Official support for Python 3.13


## 4.4 (2024-10-03)
### New Features
- Add scrollback, tab, and window restoring for the Kitty terminal
([#24](https://github.com/jdholtz/i3-restore/pull/24))
    - Refer to the [Kitty Configuration](CONFIGURATION.md#kitty) for information on how to enable this feature

### Improvements
- Fix an issue where a window not being swallowed could cause the restore process to exit early


## 4.3 (2024-08-11)
### Improvements
- Restore workspaces on their correct displays, if possible
([#17](https://github.com/jdholtz/i3-restore/issues/17))
- The `--interval` flag was renamed to `--save-interval` to reduce confusion about the flag's
purpose ([#18](https://github.com/jdholtz/i3-restore/issues/18))

### Upgrading
- If you have the `--interval` flag in your i3 config file, it needs to be changed to
`--save-interval`


## 4.2 (2024-07-06)
### New Features
- A [Similar Software](README.md#similar-software) and [Limitations](README.md#limitations) section has been added to the Readme
([#11](https://github.com/jdholtz/i3-restore/issues/11) and [#13](https://github.com/jdholtz/i3-restore/issues/13))
- Directions on installing on Gentoo Linux using emerge have been added to the Readme
([#20](https://github.com/jdholtz/i3-restore/pull/20) by [@vitaly-zdanevich](https://github.com/vitaly-zdanevich))

### Bug Fixes
- Fix saving windows with classes that aren't retrieved from i3-msg


## 4.1 (2024-01-07)
### Bug Fixes
- Fix log messages messing up the restoring process when using a verbosity
- Fix programs not restoring correctly when the default shell is not Bash


## 4.0 (2024-01-03)
### New Features
- Official support for Python 3.12
- A help flag (`--help` or `-h`) can now be used on either script to get its usage
- A verbose flag (`-v`) can be used to show debug messages while running the script. A double verbose flag (`-vv`) can
be used to additionally show all commands executed by the script
- A [Features](README.md#features) section has been added to the Readme

### Changes
- The shorthand for the version flag has been changed from `-v` to `-V`


## 3.5 (2023-09-23)
### New Features
- The currently focused container is now saved and restored next session


## 3.4 (2023-08-12)
### New Features
- This project is now licensed under the GPLv3 license instead of the MIT license
- Natively support restoring `pipenv`, `sudo`, and `su` in the configuration
- More specific criteria is now supported for saving subprocesses, allowing you to include `args` that need to be included
in the subprocess command for it to be restored. See the [subprocess configuration](CONFIGURATION.md#subprocesses) for more
information
- The `launch_command` in the subprocess configuration now defaults to `{command}` so there is no need to specify that in your
configuration file


## 3.3 (2023-03-18)
### Improvements
- Restoring subprocesses is now handled better (and works with the kitty terminal!)

### Upgrading
- Subprocess configuration has changed. Please refer to both the [Subprocess](CONFIGURATION.md#subprocesses) configuration
section and the [example configuration file](config.example.json) to adjust your configuration correctly
- Python 3.7+ is now needed as a dependency (previously Python 3+)


## 3.2 (2023-01-16)
### Improvements
- The configuration file was changed from `programs/config.py` to `config.json`, making it much easier to configure i3-restore.
Additionally, a [Configuration](CONFIGURATION.md) guide was written to facilitate the script's configuration.
- Added [a note](CONFIGURATION.md#restoring-vim-and-neovim-sessions) in the Configuration Doc about restoring Vim/Neovim sessions
more reliably

### Upgrading
- Make sure to transfer your configuration from `programs/config.py` to `config.json`. Be sure to look at the
[Configuration.md](CONFIGURATION.md) guide to properly set up the configuration. Most of this can be done by copy-pasting your
old configuration into the new file.


## 3.1 (2023-01-05)
### New Features
- An `--interval` flag can now be specified to automatically save your i3 session every X minutes. See more information on
how to use this in the [Restoring section of the README](README.md#restoring)
- Natively support restoring `ssh` and `man` in the configuration
- A [Contributing.md](CONTRIBUTING.md) doc and [License](LICENSE) were added to clarify how to contribute to this project
- A [GitHub workflow](.github/workflows/lint-format.yml) was added to ensure the integrity of the code

### Bug Fixes
- Fix restoring not working correctly on setups with multiple outputs/monitors
- Skip saving containers that don't have valid PIDs or access is denied to information about the programs running on them


## 3.0 (2022-12-24)
### New Features
- New formatting standards were added for Contributors

### Improvements
- Restoring was once again significantly improved. It now works with restoring subprocesses in
terminals with different window titles (Vim, Emacs, cmus, etc.)

### Upgrading
A couple of changes need to be done when upgrading to this version:
1. [xdotool](https://github.com/jordansissel/xdotool) is now needed as a dependency
2. `i3-restore.sh` was changed to `i3-restore` and `i3-save.sh` was changed to `i3-save`. Please
make the necessary changes within your i3 config


## 2.0 (2022-11-08)
### New Features
- A button was added to the i3-nagbars that allows the user to run the script manually to view the error that occurred

### Improvements
- Restoring was changed significantly. It is now more efficient and reliable

### Upgrading
When upgrading to this version, make sure to delete all files in you `i3_Path` that end with `programs.json`, as those files
will never be removed (the file names changed).


## 1.2 (2022-10-29)
### New Features
- A logger was added to make it easier to debug the script
- An [i3-nagbar](https://man.archlinux.org/man/community/i3-wm/i3-nagbar.1.en) will now appear when an error occurs while
running the script, making it easier for the user to see what is wrong.

### Bug Fixes
- Subprocess programs are now saved correctly (e.g vim, cmus, etc.)


## 1.1 (2022-08-13)
### New Features
- The version can now be retrieved by using the `--version` or `-v` flag when running either one of the two shell scripts
  - `./i3-save.sh --version`
  - `./i3-restore.sh --version`
- A changelog has been added to make it easier for users to upgrade to the newest version and to keep track of past changes

### Bug Fixes
- Fix inability to save correctly when there is a `/` in a workspace name ([#1](https://github.com/jdholtz/i3-restore/issues/1))

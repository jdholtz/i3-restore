# Changelog
When upgrading to a new version, make sure to follow the directions under the "Upgrading" header of the corresponding version.
If there is no "Upgrading" header for that version, no post-upgrade actions need to be performed.


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

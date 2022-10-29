# Changelog
When upgrading to a new version, make sure to follow the directions under the "Upgrading" header of the corresponding version.
If there is no "Upgrading" header for that version, no post-upgrade actions need to be performed.

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

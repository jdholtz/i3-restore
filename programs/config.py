# This config file is used to customize how i3-restore restores select programs.


# A list of all terminals you use.
#
# Include the class of the terminal window as well as the command used to launch the terminal.
# The class can be found in the WM_CLASS(STRING) variable after running 'xprop' inside of the window.
TERMINALS = [
    {
        "class": "Alacritty",
        "command": "alacritty",
    },
]


# A list of programs that run as subprocesses of a shell (vim, emacs, cmus, etc.). These are usually
# programs that run in the same window the command is executed in and, when exited, they return to the shell.
#
# 'name' is the command used to launch the program itself (usually the same as the programs's name)

# 'launch_command' is how you want the program to be launched upon startup (processes that run in
# the shell will need to be launched from the terminal itself to maintain the exact structure (exiting
# doesn't quit the entire session, but it brings you back to the shell). The {command} placeholder is
# where you actually want the terminal editor launch command to go. The script will replace this placeholder
# with the actual command at runtime.
SUBPROCESS_PROGRAMS = [
    {
        "name": "vim",
        "launch_command": 'alacritty -e bash -c "TERM=xterm-256color && {command} && bash"',
    },
    {
        "name": "cmus",
        "launch_command": 'alacritty -e bash -c "{command}"',
    },
]


# A list of all web browsers you use.
#
# This is used to ensure only one instance of each browser pops up
# because the web browser itself will restore every window, so doing
# it in the script only creates extra windows.
WEB_BROWSERS = [
    "firefox",
]

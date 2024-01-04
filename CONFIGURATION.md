# Configuration
This guide contains all the information you need to configure i3-restore to your needs. A default/example configuration
file can be found at [config.example.json](config.example.json)

Pull requests are encouraged if you have added and tested a new program in the configuration file. See [Contributing.md](CONTRIBUTING.md)
for more information.

## Table of Contents
- [Terminals](#terminals)
- [Subprocesses](#subprocesses)
- [Web Browsers](#web-browsers)
- [Setting A Custom Save Path](#setting-a-custom-save-path)
- [Restoring Vim And Neovim Sessions](#restoring-vim-and-neovim-sessions)

## Terminals
Two things are needed to set up terminal configuration:
1. The terminal class name
2. The terminal launch command

To get the class name of the desired terminal, focus on the terminal and run the following command
```shell
xdotool getactivewindow getwindowclassname
```

The terminal launch command is the command used to launch your terminal

Next, input the information into the `terminals` section of the configuration. Make sure the `terminals` section is
a list that contains the configured terminals.
```json
{
  "terminals": [
    {
      "class": "<class name>",
      "command": "<launch command>"
    }
  ]
}
```

## Subprocesses
Subprocesses are programs that run in the same window their command was executed in and return to the shell on exit. Examples
include vim, emacs, less, and man.

Four things are needed to set up subprocess configuration:
1. A line in your shell's rcfile to execute the subprocess correctly (only done once)
2. The subprocess name
3. Arguments the subprocess has to include to be saved (Optional)
4. The desired subprocess launch command (Optional. Default: "{command}")

To restore subprocesses correctly, each subprocess command is saved in a separate script. When i3-restore attempts to restore
your session, it will set an environment variable (`I3_RESTORE_SUBPROCESS_SCRIPT`) pointing to the path of the script and execute
the command to launch your terminal. To have the subprocess script execute, you need to add a line in your shell's rcfile to
correctly execute it. Here is an example of what this line looks like for Bash:
```bash
trap 'unset I3_RESTORE_SUBPROCESS_SCRIPT' SIGINT # Unset the variable on Ctrl+C as well
[[ -n $I3_RESTORE_SUBPROCESS_SCRIPT ]] && "${I3_RESTORE_SUBPROCESS_SCRIPT}" && unset I3_RESTORE_SUBPROCESS_SCRIPT
```

The subprocess is the initial command used to launch the subprocess(e.g. Vim's initial command is `vim`).

The launch command of the subprocess is how you want the program to be launched on startup. Subprocesses are a bit special
because they need to be restored in a way that the terminal launches them, and you should be returned back to the terminal
when they exit (exactly what would happen if you were to launch the subprocess in the terminal).

Additionally, `{command}` can be used as a placeholder to inject the actual command used to invoke the subprocess into the
launch command. You might need to play around with this before putting it in your configuration file to make sure it performs
exactly how you want it to. For examples, refer to the [example configuration file](config.example.json).

To include more specific criteria to save the subprocess, you can use the `args` option in the configuration. Then, the subprocess
would only be restored if it was launched with one of the arguments specified. For example, including the `"args": ["-i"]` configuration
for the `sudo` subprocess would only restore the subprocess if it was launched with the `-i` flag.

Next, input the information into the `subprocesses` section of the configuration. Make sure the `subprocesses` section is
a list that contains the configured terminals.
```json
{
  "subprocesses": [
    {
      "name": "<name>",
      "args": ["<arg>", "<arg>"],
      "launch_command": "<launch command>"
    }
  ]
}
```

## Web Browsers
Only the launch command is needed to configure web browsers correctly. Make sure the `web_browsers` section is a list that
contains the configured web browsers
```json
{
    "web_browsers": [
        "browser 1 launch command",
        "browser 2 launch command"
    ]
}
```

## Setting A Custom Save Path
By default, the layout and program files are saved under `$HOME/.config/i3`. To change this, set the `i3_PATH` environment variable to
the desired location.

## Restoring Vim And Neovim Sessions
It is recommended to use [vim-prosession](https://github.com/dhruvasagar/vim-prosession) to manage your vim/neovim sessions, allowing for
more reliable restores.

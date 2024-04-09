# Contributing to i3-restore
Welcome! Thanks for considering contributing to the development of **i3-restore**. This guide contains useful tips and guidelines
to contribute to this project.

Please submit all changes to the `develop` branch. This allows for separation between new changes and the latest stable release. When submitting a
pull request, make sure to add the change/feature to the [Upcoming](CHANGELOG.md#upcoming) section of the changelog with a reference to the
pull request (this can be done after submitting the PR or separately by me).

## Adding To The Configuration
Adding/modifying the configuration file is highly encouraged to increase i3-restore's compatibility with common software. Simply add
your desired programs to the [config.example.json](config.example.json), test it, and submit a PR!

## Coding Conventions
This project follows [Google's Shell Style Guide][0]. Please use your best judgement when
following the conventions in this guide.

It is highly recommended for you to use [pre-commit][1] to ensure you are following these conventions.

### Linting
[Shellcheck][2] is used to lint the bash scripts and [Flake8][3] is used to lint the Python scripts. When validating your code
against these linters, use your best judgement to determine whether to fix the issue or disable the warning.

### Formatting
[Shfmt][4] is used to format the bash scripts and [Black][5] is used to format the Python scripts. Using a common formatter
ensures that the code looks the same throughout the project.

It is also highly recommended to use an [EditorConfig][6] plugin for your code editor to maintain a consistent coding style for all project files.

[0]: https://google.github.io/styleguide/shellguide.html
[1]: https://pre-commit.com
[2]: https://www.shellcheck.net
[3]: https://flake8.pycqa.org/en/latest
[4]: https://github.com/mvdan/sh
[5]: https://black.readthedocs.io/en/stable
[6]: https://editorconfig.org/

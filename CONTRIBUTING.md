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
This project follows [Google's Shell Style Guide]. Please use your best judgement when
following the conventions in this guide.

It is highly recommended for you to use [pre-commit] to ensure you are following these conventions.

### Linting
[Shellcheck] is used to lint the bash scripts and [Flake8] is used to lint the Python scripts. When validating your code
against these linters, use your best judgement to determine whether to fix the issue or disable the warning.

### Formatting
[Shfmt] is used to format the bash scripts and [Black] is used to format the Python scripts. Using a common formatter
ensures that the code looks the same throughout the project.

It is also highly recommended to use an [EditorConfig] plugin for your code editor to maintain a consistent coding style for all project files.

[Google's Shell Style Guide]: https://google.github.io/styleguide/shellguide.html
[pre-commit]: https://pre-commit.com
[Shellcheck]: https://www.shellcheck.net
[Flake8]: https://flake8.pycqa.org/en/latest
[Shfmt]: https://github.com/mvdan/sh
[Black]: https://black.readthedocs.io/en/stable
[EditorConfig]: https://editorconfig.org/

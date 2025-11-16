# Contributing to i3-restore
Welcome! Thanks for considering contributing to the development of **i3-restore**. This guide contains useful tips and guidelines
to contribute to this project.

Please submit all changes to the `develop` branch. This allows for separation between new changes and the latest stable release.

## Adding to the Configuration
Adding/modifying the configuration file is highly encouraged to increase i3-restore's compatibility with common software. Simply add
your desired programs to the [config.example.json](config.example.json), test it, and submit a PR!

## Testing
This project uses [Pytest] for Python unit testing and [Bats] for Bash unit testing. When
adding/modifying the code, you may need to add a new test or modify an existing test.

The goal of these tests is to provide 100% code coverage (only measured for the Python tests) to increase the reliability of existing
features and smoothly integrate new ones into the project. To learn about running tests for **i3-restore**, visit the [Testing README](tests/README.md).

## Coding Conventions
This project follows [Google's Shell Style Guide]. Please use your best judgement when
following the conventions in this guide.

It is highly recommended for you to use [pre-commit] to ensure you are following these conventions.

### Linting
[Shellcheck] is used to lint the bash scripts and [Ruff] (`ruff check`) is used to lint the Python scripts. When validating your code
against these linters, use your best judgement to determine whether to fix the issue or disable the warning.

### Formatting
[Shfmt] is used to format the bash scripts and [Ruff] (`ruff format`) is used to format the Python scripts. Using a common formatter
ensures that the code looks the same throughout the project.

It is also highly recommended to use an [EditorConfig] plugin for your code editor to maintain a consistent coding style for all project files.

[Pytest]: https://docs.pytest.org
[Bats]: https://github.com/bats-core/bats-core
[Google's Shell Style Guide]: https://google.github.io/styleguide/shellguide.html
[pre-commit]: https://pre-commit.com
[Shellcheck]: https://www.shellcheck.net
[Ruff]: https://docs.astral.sh/ruff/
[Shfmt]: https://github.com/mvdan/sh
[EditorConfig]: https://editorconfig.org/

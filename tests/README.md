# Automated Testing
The following guide covers how to run all unit tests for i3-restore. They are grouped by
implementation language:

- `python/` contains unit tests to validate Python helpers and plugins using [Pytest].
- `bash/` contains unit tests to validate Bash functionality using [Bats].

The unit test naming and formatting conventions can be replicated from the tests that already
exist.

## Running Tests
### Python
#### Setup
Install all the requirements needed
```shell
pip install -r tests/python/requirements.txt
```

#### Running the Tests
To run all the Python tests
```shell
pytest
```

To run all tests for a specific module
```shell
pytest tests/python/test_<module name>.py
```

Or multiple
```shell
pytest tests/python/test_<module1>.py tests/python/test_<module2>.py
```

To get a coverage report
```shell
pytest --cov
```

### Bash
#### Setup
Bats is included as git submodules, so make sure the submodules are initialized:

```shell
git submodule update --init --recursive
```

#### Running the Tests
```shell
tests/bash/bats-core/bin/bats tests/bash
```

To run all tests for a specific file

```shell
tests/bash/bats-core/bin/bats tests/bash/test_<script name>.bats
```

Or multiple

```shell
tests/bash/bats-core/bin/bats tests/bash/test_<script1>.bats tests/bash/test_<script2>.bats
```

[Pytest]: https://docs.pytest.org
[Bats]: https://github.com/bats-core/bats-core

# Legal Kural Development Environment

## Python

Legal Kural uses Python 3.12 inside a repository-local virtual environment.

```text
.venv/
```

The system Python and Homebrew-managed Python environments are never modified.

## Bootstrap

```bash
./bin/bootstrap
```

## Commands

```bash
./bin/python --version
./bin/pip list
./bin/legalkural --help
./bin/aidpl-orchestrator --help
./bin/aidpl-intake --help
```

## Rule

All Legal Kural Python execution must use `.venv/bin/python` through the repository wrappers in `bin/`.

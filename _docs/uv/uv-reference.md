# uv command reference

Consolidated from `uv-commands.md` and `uv-common-workflow.md`.
Reviewed on **2026-09-26**; local CLI help checked with **uv 0.10.9**.

This is a reference for your saved commands, not a recommendation to install
every package below. Version numbers are retained examples, not claims about
the latest releases. Code blocks show independent choices unless labeled as a
workflow. Replace illustrative project names, package paths, and URLs as needed.

Run project commands from the folder containing the intended `pyproject.toml`.
macOS commands work on Intel and Apple Silicon; native-package availability can
still differ by Python version and CPU. Windows-specific commands are labeled.

## Contents

- [Quick lookup](#quick-lookup)
- [1. Install uv and get help](#1-install-uv-and-get-help)
- [2. Create a project](#2-create-a-project)
- [3. Choose Python and manage the environment](#3-choose-python-and-manage-the-environment)
- [4. Add dependencies](#4-add-dependencies)
- [5. Use Git, local files, URLs, and requirements files](#5-use-git-local-files-urls-and-requirements-files)
- [6. Change, upgrade, remove, or reinstall packages](#6-change-upgrade-remove-or-reinstall-packages)
- [7. Lock, sync, and control updates](#7-lock-sync-and-control-updates)
- [8. Run code and tools](#8-run-code-and-tools)
- [9. Common workflows](#9-common-workflows)
- [10. Corrections and official references](#10-corrections-and-official-references)

## Quick lookup

| I want to…                                  | Command                              |
|---------------------------------------------|--------------------------------------|
| Start an application with Python 3.13       | `uv init --app --python 3.13 agents` |
| Select Python for this project              | `uv python pin 3.13`                 |
| Install Python explicitly                   | `uv python install 3.13`             |
| Install/update the project environment      | `uv sync`                            |
| Add a runtime dependency                    | `uv add requests`                    |
| Add a development dependency                | `uv add --dev pytest`                |
| Add to a named dependency group             | `uv add --group lint ruff`           |
| Remove a dependency                         | `uv remove requests`                 |
| Run a Python file                           | `uv run python main.py`              |
| Run tests                                   | `uv run pytest`                      |
| Upgrade one package and install it          | `uv sync --upgrade-package fastapi`  |
| Reinstall one package                       | `uv sync --reinstall-package httpx`  |
| Check that the lockfile matches the project | `uv lock --check`                    |
| Sync without allowing lockfile changes      | `uv sync --locked`                   |

### The four project files and folders

| Item              | Purpose                                                               |
|-------------------|-----------------------------------------------------------------------|
| `pyproject.toml`  | Project settings, allowed Python versions, and declared dependencies. |
| `.python-version` | Python version requested for local project commands.                  |
| `uv.lock`         | Resolved package versions: the exact dependency selection.            |
| `.venv/`          | The local Python environment and its installed packages.              |

```text
pyproject.toml ── uv lock ──> uv.lock ── uv sync ──> .venv
                                  uv run ──> prepare environment, then run code
```

`uv sync` also refreshes the lockfile when needed. `uv add` and `uv remove`
normally update the dependency declaration, lockfile, and environment together.
Keep the project metadata and lockfile in version control; exclude `.venv/`.

## 1. Install uv and get help

**macOS / Linux installation** — installs uv on the machine; run only if needed:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

**Windows installation:**

```powershell
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
```

**Inspect the installed version or command help:**

```bash
uv --version
uv help
uv help add
uv help sync
```

## 2. Create a project

Choose one initialization command:

| Purpose                                     | Command                              |
|---------------------------------------------|--------------------------------------|
| Initialize the current directory            | `uv init .`                          |
| Create a new project folder                 | `uv init my-project`                 |
| Explicitly create an application            | `uv init --app my-app`               |
| Create a library with a `src/` layout       | `uv init --lib my-lib`               |
| Create an application targeting Python 3.13 | `uv init --app --python 3.13 agents` |

After creating a folder, enter it before managing that project:

```bash
cd my-project
```

## 3. Choose Python and manage the environment

### Install, pin, and create

These are different operations:

| Operation                             | Python 3.13 example      | Python 3.12 alternative  |
|---------------------------------------|--------------------------|--------------------------|
| Download/install Python               | `uv python install 3.13` | `uv python install 3.12` |
| Record the project's requested Python | `uv python pin 3.13`     | `uv python pin 3.12`     |
| Explicitly create `.venv`             | `uv venv --python 3.13`  | `uv venv --python 3.12`  |

For a uv project, `uv sync` or `uv run` can create the environment automatically.
Explicit `uv venv` and shell activation are usually unnecessary for that workflow.
Python can also be downloaded automatically when required, if downloads are enabled.

### Activate only when you want bare shell commands

Activation makes commands such as `python` use `.venv` in the current shell.
`uv run` selects the project environment without activation.

**macOS / Linux (bash or zsh):**

```bash
source .venv/bin/activate
```

**Windows PowerShell:**

```powershell
.venv\Scripts\Activate.ps1
```

**Windows Command Prompt:**

```bat
.venv\Scripts\activate.bat
```

Leave an activated environment with `deactivate`.

### Verify the requested and actual Python versions

From the project folder on macOS / Linux:

```bash
cat .python-version
grep requires-python pyproject.toml
uv run python --version
```

### Restrict the project to Python 3.13

`.python-version` selects a local interpreter. `requires-python` declares which
Python versions the project supports; pinning does not replace that declaration.

Edit the existing `requires-python` entry under `[project]` in `pyproject.toml`:

```toml
requires-python = ">=3.13,<3.14"
```

The saved alternatives `~=3.13.0` and `==3.13.*` also express a 3.13-series
requirement. Do not add multiple `requires-python` entries.

Then run, in order:

```bash
uv python pin 3.13
uv lock
uv sync
uv run python --version
```

To request a particular patch release, the saved syntax example is
`uv python pin 3.13.0`. That older release is an example, not an upgrade target.
`uv lock` updates dependency resolution; it does not rebuild `.venv`.
`uv sync` handles the environment and recreates it when its interpreter is
incompatible with the requested Python.

## 4. Add dependencies

A **runtime dependency** is needed by the application. A **development
dependency** supports work such as testing or linting. An **extra** is an optional
feature's set of dependencies.

### Runtime packages

```bash
# One package
uv add requests

# Multiple packages
uv add requests httpx pydantic

# Saved web application examples
uv add fastapi "uvicorn[standard]"
uv add python-dotenv
```

### Version constraints

Quote requirements containing comparison operators or square brackets.

| Constraint      | Saved example               | Meaning                |
|-----------------|-----------------------------|------------------------|
| Minimum version | `uv add "httpx>=0.27"`      | Allow 0.27 or newer.   |
| Bounded range   | `uv add "django>=5.0,<6.0"` | Allow Django 5.x.      |
| Exact version   | `uv add "numpy==2.1.0"`     | Require exactly 2.1.0. |

These preserve your command-syntax examples. For an exact declaration, use `==`
with the version you have selected and tested. The lockfile records exact resolved
versions even when the declaration permits a range.

### Development packages

```bash
uv add --dev "debugpy>=1.8"
uv add --dev "pytest>=8.3.0"
uv add --dev "ruff>=0.9.0"
uv add --dev pytest-asyncio mypy
```

`--dev` means `--group dev`. The `dev` group is included by default, unless the
project changes its default groups.

### Named groups

```bash
uv add --group lint ruff black
uv add --group docs mkdocs mkdocs-material
uv add --group test pytest pytest-cov
```

The original `_docs` group name has been corrected to `docs`: dependency-group
names must start and end with a letter or digit. This is unrelated to the
workspace's `_docs/` directory, whose name does not need to change.

To include a named group during later syncs:

```bash
uv sync --group lint
uv sync --group docs
uv sync --group test
```

Each line is a separate choice. Combine `--group` options to include multiple
groups in the same sync.

### Optional project dependencies versus a package's extras

**Define your project's `gpu` extra:**

```bash
uv add --optional gpu torch
uv sync --extra gpu
```

The second command enables that extra in the environment. The name `gpu` is only
a feature label; it does not configure GPU hardware or guarantee acceleration.

**Request extras supplied by another package:**

```bash
uv add "fastapi[standard]"
uv add "uvicorn[standard]"
```

### Conditional dependencies: environment markers

A marker limits when a dependency applies:

```bash
# Linux only
uv add "jax; sys_platform == 'linux'"

# Python below 3.11 only
uv add "tomli; python_version < '3.11'"
```

The `tomli` condition does not apply to a project restricted to Python 3.13.

## 5. Use Git, local files, URLs, and requirements files

### Git repository

```bash
# Repository's default branch
uv add git+https://github.com/psf/requests

# Specific tag
uv add "git+https://github.com/psf/requests@v2.31.0"

# Named branch
uv add "git+https://github.com/psf/requests@main"
```

The text after `@` can also be a commit hash. A branch can move; the lockfile
records the resolved commit. These lines are alternatives for the same package.

### Local package or wheel

These are path templates; supply existing files inside your workspace:

```bash
uv add ./path/to/local-package
uv add ./path/to/package-1.0.0-py3-none-any.whl
uv add --editable ./path/to/local-package
```

An absolute path is also accepted. An **editable** install makes local source
changes available without reinstalling after each edit.

### Direct URL

Replace this illustrative URL with a real distribution URL:

```bash
uv add "https://example.com/package-1.0.0-py3-none-any.whl"
```

### Import requirements into the project

```bash
uv add -r requirements.txt
```

This adds the requirements to `pyproject.toml` and normally updates the lockfile
and environment. Run it once; the repeated line in the original notes was a duplicate.

## 6. Change, upgrade, remove, or reinstall packages

### Change a declared constraint

```bash
uv add "httpx>0.28"
```

This changes `pyproject.toml`; `>0.28` excludes version 0.28 itself.

### Upgrade within the declared constraints

**Update only the lockfile, then install the result:**

```bash
uv lock --upgrade-package fastapi
uv sync
```

**Or update the lockfile and environment together:**

```bash
uv sync --upgrade-package fastapi
```

**Saved add-and-upgrade form:**

```bash
uv add httpx --upgrade-package httpx
```

**Upgrade all packages within their allowed constraints:**

```bash
uv lock --upgrade
uv sync
```

An exact `==` requirement prevents an upgrade to a different version until you
change the declaration. Upgrading one package can also require changes to its
dependencies. Ordinary `uv sync` does not request the newest release of every package.

### Remove from the correct dependency section

```bash
uv remove requests
uv remove --dev pytest
uv remove --group lint ruff
```

### Reinstall without requesting an upgrade

```bash
uv sync --reinstall-package httpx
```

Use the actual installed package name in place of `httpx`. This forces a fresh
installation of that package; it does not request a newer version.

## 7. Lock, sync, and control updates

### Core operations

| Command            | Purpose                                                              |
|--------------------|----------------------------------------------------------------------|
| `uv lock`          | Create/update dependency resolution in `uv.lock`; do not install it. |
| `uv sync`          | Refresh resolution if needed and install the selected dependencies.  |
| `uv lock --check`  | Fail if the lockfile is missing or out of date.                      |
| `uv sync --locked` | Require an up-to-date lockfile and install from it.                  |
| `uv sync --frozen` | Install from the existing lockfile without checking freshness.       |

`uv sync` normally removes packages outside the selected dependency set.
Use group and extra options consistently when you need them.

### Flags depend on the command

| Command / flag                                         | Effect                                                                      |
|--------------------------------------------------------|-----------------------------------------------------------------------------|
| `uv add … --no-sync` / `uv remove … --no-sync`         | Update the declaration and lockfile, but skip installation.                 |
| `uv add … --frozen` / `uv remove … --frozen`           | Edit the declaration without updating the lockfile or environment.          |
| `uv sync --locked` / `uv run --locked …`               | Reject a missing or stale lockfile instead of changing it.                  |
| `uv sync --frozen` / `uv run --frozen …`               | Use the existing lockfile without checking it against changed declarations. |
| `uv run --no-sync …`                                   | Run without environment syncing; also implies `--frozen`.                   |
| `--upgrade` with `lock`, `sync`, or `run`              | Request newer allowed versions for all packages.                            |
| `--upgrade-package NAME` with `lock`, `sync`, or `run` | Request an upgrade for a selected package.                                  |

The `…` entries are syntax summaries, not commands to paste. Use `--locked` when
you want inconsistency detected. `--frozen` can leave newly declared dependencies
unavailable because they have not reached the lockfile.

Details: [uv locking and syncing](https://docs.astral.sh/uv/concepts/projects/sync/)
and [uv command reference](https://docs.astral.sh/uv/reference/cli/).

## 8. Run code and tools

```bash
# Run an existing Python file
uv run python main.py

# Run tests, with pytest added to the project
uv run pytest

# Saved MCP development command
uv run mcp dev server.py
```

The MCP command requires a compatible `server.py`, the MCP SDK's CLI dependencies
(the `mcp[cli]` extra), and the Inspector's Node.js prerequisites. It is an MCP
tool command launched through uv, not a feature built into uv.

Normally, `uv run` checks the lockfile and prepares the environment before running
the command. To require the existing lockfile to be current:

```bash
uv run --locked python main.py
uv run --locked pytest
```

## 9. Common workflows

### Start a minimal application

From the parent directory where you want a new `agents/` project, run in order.
Use a fresh folder name if `agents/` already exists:

```bash
uv init --app --python 3.13 agents
cd agents
uv sync
uv run python main.py
```

This is the expanded version of your saved one-line initialization workflow.
Activation is optional; use the command in section 3 if desired.

### Resume an existing project

From its project directory:

```bash
uv sync --locked
uv run --locked python main.py
```

If the lockfile is missing or intentionally needs updating, use `uv sync`, review
the resulting `uv.lock` changes, and then run the application.

### Saved application dependency bundle

Historical example from your workflow notes; these versions have not been
tested together during this documentation review:

```bash
uv add \
  "httpx>=0.27" \
  "uvicorn[standard]" \
  "numpy==2.4.4" \
  "pandas==3.0.2" \
  "sqlalchemy==2.0.49" \
  psycopg2-binary
```

### Explain the workflow professionally

“We declare dependencies in `pyproject.toml`, record their resolved versions in
`uv.lock`, and use `uv sync` to prepare the environment. We run project commands
through `uv run` so they use that environment.”

## 10. Corrections and official references

Changes made while consolidating the two source files:

- Removed repeated commands and merged overlapping setup and workflow sections.
- Corrected the `tomli` comment from “Python 3.12+” to “Python below 3.11.”
- Corrected `_docs` to `docs` for the dependency-group name.
- Split the flag table by command: `--frozen` and `--no-sync` have different
  implications for `add`, `sync`, and `run`.
- Clarified that `uv lock` does not rebuild `.venv`, and ordinary syncing does
  not automatically upgrade every package.
- Distinguished the local Python pin from `requires-python` compatibility.
- Made virtual-environment creation and activation optional in project workflows.
- Added shell-specific Windows activation commands and prerequisites for MCP.
- Preserved saved package versions as examples rather than treating them as
  current recommendations.

Official references for command behavior:

- [CLI reference](https://docs.astral.sh/uv/reference/cli/)
- [Managing dependencies](https://docs.astral.sh/uv/concepts/projects/dependencies/)
- [Locking and syncing](https://docs.astral.sh/uv/concepts/projects/sync/)
- [Python version management](https://docs.astral.sh/uv/concepts/python-versions/)
- [Installation](https://docs.astral.sh/uv/getting-started/installation/)
- [Dependency-group name specification](https://packaging.python.org/en/latest/specifications/dependency-groups/)
- [MCP Python SDK development tools](https://github.com/modelcontextprotocol/python-sdk)

Validation covered the source notes, CLI help, and documentation. No installation,
dependency upgrade, or environment change was performed to prepare this reference.

"""Pre-commit hook: bump the FamiCent version number on every commit.

Rules (R52–R54):
  - Reads __version__ from src/famicent/__init__.py.
  - Applies bump logic: patch+1, with rollover for n and m.
  - Writes the new version back.
  - Rewrites the commit message to prepend: v{m.n.p} build {yyyy-mm-dd-hhmm}
"""
from __future__ import annotations

import re
import sys
from datetime import datetime
from pathlib import Path

VERSION_FILE = Path(__file__).resolve().parent.parent / "src" / "famicent" / "__init__.py"
_VERSION_RE = re.compile(r'^__version__\s*=\s*"(\d+)\.(\d)\.(\d)"', re.MULTILINE)


def _read_version() -> tuple[int, int, int]:
    """Read the current version from __init__.py."""
    content = VERSION_FILE.read_text(encoding="utf-8")
    m = _VERSION_RE.search(content)
    if not m:
        print("ERROR: Could not find __version__ in", VERSION_FILE, file=sys.stderr)
        sys.exit(1)
    return int(m.group(1)), int(m.group(2)), int(m.group(3))


def _bump(major: int, minor: int, patch: int) -> tuple[int, int, int]:
    """Apply patch-increment with minor/major rollover (R52)."""
    patch += 1
    if patch > 9:
        patch = 0
        minor += 1
    if minor > 9:
        minor = 0
        major += 1
    return major, minor, patch


def _write_version(major: int, minor: int, patch: int) -> None:
    """Update __version__ in __init__.py in-place."""
    content = VERSION_FILE.read_text(encoding="utf-8")
    new_version = f"{major}.{minor}.{patch}"
    new_content = _VERSION_RE.sub(f'__version__ = "{new_version}"', content)
    VERSION_FILE.write_text(new_content, encoding="utf-8")


def _rewrite_commit_message(msg_file: Path, version: str) -> None:
    """Prepend version+timestamp to the commit message (R54)."""
    msg = msg_file.read_text(encoding="utf-8").strip()
    timestamp = datetime.now().strftime("%Y-%m-%d-%H%M")
    new_msg = f"v{version} build {timestamp} {msg}"
    msg_file.write_text(new_msg, encoding="utf-8")


def main() -> None:
    """Entry point invoked by the pre-commit hook."""
    major, minor, patch = _read_version()
    major, minor, patch = _bump(major, minor, patch)
    _write_version(major, minor, patch)

    version_str = f"{major}.{minor}.{patch}"
    print(f"[bump_version] Version bumped to {version_str}")

    # If a commit message file path is passed (git hook passes COMMIT_EDITMSG)
    if len(sys.argv) > 1:
        msg_file = Path(sys.argv[1])
        if msg_file.exists():
            _rewrite_commit_message(msg_file, version_str)


if __name__ == "__main__":
    main()

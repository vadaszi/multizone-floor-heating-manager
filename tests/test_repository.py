"""Repository checks: every relative link in the Markdown files points to an existing file
and heading, and the integration's brand images are in place."""

from __future__ import annotations

import json
import os
import re
import subprocess
from functools import cache
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SKIPPED_FOLDERS = {".git", ".venv", "node_modules", "__pycache__"}


def _walk() -> list[str]:
    """Every file in the folder, without tool folders and hidden folders (but `.github`)."""
    files = []
    for folder, folders, names in os.walk(ROOT):
        folders[:] = [
            name
            for name in folders
            if name not in SKIPPED_FOLDERS and (not name.startswith(".") or name == ".github")
        ]
        files += [str((Path(folder) / name).relative_to(ROOT)) for name in names]
    return files


@cache
def published_files() -> list[Path]:
    """The tracked and new files of the git checkout; without git (e.g. an unpacked
    release archive) every file in the folder."""
    try:
        listed = subprocess.run(
            ["git", "ls-files", "--cached", "--others", "--exclude-standard"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=True,
        ).stdout.splitlines()
    except OSError, subprocess.CalledProcessError:
        listed = _walk()
    return sorted(ROOT / name for name in listed if (ROOT / name).is_file())


LINK = re.compile(r"(?<!!)\[[^\]]*\]\(([^)\s]+)\)|!\[[^\]]*\]\(([^)\s]+)\)")
HEADING = re.compile(r"^(#{1,6})\s+(.*?)\s*#*\s*$")
FENCE = re.compile(r"^\s*(```|~~~)")


def _anchor(heading: str) -> str:
    """GitHub's anchor for a heading."""
    text = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", heading)  # links -> their text
    text = text.replace("`", "").replace("*", "").strip().lower()
    text = re.sub(r"[^\w\- ]", "", text)
    return text.replace(" ", "-")


@cache
def _anchors(path: Path) -> set[str]:
    anchors: set[str] = set()
    seen: dict[str, int] = {}
    fenced = False
    for line in path.read_text(encoding="utf-8").splitlines():
        if FENCE.match(line):
            fenced = not fenced
        if fenced or not (match := HEADING.match(line)):
            continue
        anchor = _anchor(match.group(2))
        count = seen.get(anchor, 0)
        seen[anchor] = count + 1
        anchors.add(anchor if count == 0 else f"{anchor}-{count}")
    return anchors


def _links(path: Path) -> list[str]:
    links = []
    fenced = False
    for line in path.read_text(encoding="utf-8").splitlines():
        if FENCE.match(line):
            fenced = not fenced
        if not fenced:
            links += [a or b for a, b in LINK.findall(line)]
    return links


@pytest.mark.parametrize(
    "path",
    [path for path in published_files() if path.suffix == ".md"],
    ids=lambda path: str(path.relative_to(ROOT)),
)
def test_relative_links_resolve(path: Path) -> None:
    problems = []
    for link in _links(path):
        if re.match(r"^[a-z][a-z0-9+.-]*:", link):  # https:, mailto:, ...
            continue
        target, _, anchor = link.partition("#")
        file = (path.parent / target).resolve() if target else path
        if not file.exists():
            problems.append(f"{link}: no such file")
        elif file.is_dir():
            problems.append(f"{link}: a folder, link a file in it")
        elif anchor and file.suffix == ".md" and anchor not in _anchors(file):
            problems.append(f"{link}: no heading #{anchor}")
    assert not problems, "\n".join(problems)


@pytest.mark.parametrize(
    ("name", "size"),
    [("icon.png", 256), ("icon@2x.png", 512), ("dark_icon.png", 256), ("dark_icon@2x.png", 512)],
)
def test_brand_images(name: str, size: int) -> None:
    """Home Assistant shows the integration's icon from its `brand` folder."""
    data = (
        ROOT / "custom_components" / "multizone_floor_heating_manager" / "brand" / name
    ).read_bytes()
    assert data[:8] == b"\x89PNG\r\n\x1a\n"
    width, height = int.from_bytes(data[16:20], "big"), int.from_bytes(data[20:24], "big")
    assert (width, height) == (size, size)


def test_manifest_links_to_the_repository() -> None:
    """The manifest's links point to the repository that the README installs from."""
    manifest = json.loads(
        (
            ROOT / "custom_components" / "multizone_floor_heating_manager" / "manifest.json"
        ).read_text(encoding="utf-8")
    )
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    repositories = set(re.findall(r"https://github\.com/[\w.-]+/[\w.-]+", readme))
    raw = {
        f"https://github.com/{owner}/{name}"
        for owner, name in re.findall(
            r"https://raw\.githubusercontent\.com/([\w.-]+)/([\w.-]+)/", readme
        )
    }
    assert repositories | raw == {manifest["documentation"]}
    assert manifest["issue_tracker"] == manifest["documentation"] + "/issues"

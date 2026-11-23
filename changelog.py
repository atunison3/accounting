"""Generate docs/change-log.md from Git; also supports manual entries.

    python changelog.py
    python changelog.py --version v1.0.0 --include-commits

Generation replaces the output with first-parent Git history, newest first.
Semantic version tags define releases; untagged changes go under Unreleased.
By default only merge commits appear. Squash/direct commits require
--include-commits because Git cannot reliably distinguish them.
"""

import argparse
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable


PROJECT_ROOT = Path(__file__).resolve().parent
DEFAULT_CHANGELOG = PROJECT_ROOT / "docs" / "change-log.md"


def add_changelog_entry(
    summary: str,
    details: Iterable[str] = (),
    *,
    path: str | Path = DEFAULT_CHANGELOG,
) -> Path:
    """Append a UTC-dated Markdown entry, creating the changelog if necessary.

    Existing entries are preserved, with new entries added at the bottom.
    The default path is the project's docs/change-log.md, regardless of the current
    working directory. Explicit relative paths resolve from the working directory.
    Returns the resolved output path. Intended for a single writer at a time.

    Example:
        add_changelog_entry(
            "Fixed service booking links",
            [
                "All Explore service buttons now link to the booking calendar.",
                "Preserved booking-click tracking.",
            ],
        )
    """
    if not isinstance(summary, str) or not summary.strip():
        raise ValueError("summary must be a nonempty string")
    if "\n" in summary or "\r" in summary:
        raise ValueError("summary must be a single line")
    if isinstance(details, (str, bytes)):
        raise TypeError("details must be an iterable of strings, not a single string")

    bullets = []
    for detail in details:
        if not isinstance(detail, str) or not detail.strip():
            raise ValueError("Each detail must be a nonempty string")
        lines = detail.strip().splitlines()
        bullets.append("- " + lines[0] + "".join("\n  " + line for line in lines[1:]))

    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    entry = f"## {timestamp} — {summary.strip()}\n"
    if bullets:
        entry += "\n" + "\n".join(bullets) + "\n"

    output = Path(path).expanduser().resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("a+", encoding="utf-8") as handle:
        handle.seek(0)
        existing = handle.read()
        if not existing:
            handle.write("# Change Log\n\n")
        elif not existing.endswith("\n\n"):
            handle.write("\n" if existing.endswith("\n") else "\n\n")
        handle.write(entry)
    return output


def generate_changelog(
    *,
    repo: str | Path = PROJECT_ROOT,
    path: str | Path = DEFAULT_CHANGELOG,
    version: str | None = None,
    include_commits: bool = False,
) -> Path:
    """Replace the changelog with version-grouped first-parent Git history.

    version labels changes after the latest tag (or all history with no tags).
    It does not create a Git tag or infer/bump a version. Only vX.Y.Z or X.Y.Z
    tags on the current branch's first-parent history define release boundaries.
    Manual entries in the output are replaced. Empty sections have no bullets.
    """
    repo = Path(repo).expanduser().resolve()
    version_pattern = r"v?(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)"
    if version is not None:
        if not re.fullmatch(version_pattern, version):
            raise ValueError("version must have the form vX.Y.Z, for example v1.0.0")
        version = "v" + version.removeprefix("v")

    def git(*args):
        result = subprocess.run(
            ["git", "-C", str(repo), *args], capture_output=True, text=True,
            encoding="utf-8", errors="replace", check=False,
        )
        if result.returncode:
            raise RuntimeError(result.stderr.strip() or "Git command failed")
        return result.stdout.strip()

    history = git("log", "--first-parent", "--format=%H%x09%P%x09%s", "HEAD").splitlines()
    commits = [line.split("\t", 2) for line in history]
    chain = {commit[0] for commit in commits}
    tags = {}
    for tag in git("tag", "--merged", "HEAD").splitlines():
        if not re.fullmatch(version_pattern, tag):
            continue
        commit = git("rev-parse", f"refs/tags/{tag}^{{commit}}")
        if commit in chain:
            normalized = "v" + tag.removeprefix("v")
            if commit in tags and tags[commit] != normalized:
                raise ValueError(f"Multiple release versions tag commit {commit[:7]}")
            tags[commit] = normalized

    head = commits[0][0]
    if version and version in tags.values() and tags.get(head) != version:
        raise ValueError("That version is already tagged; choose a new version")
    if version and head in tags and tags[head] != version:
        raise ValueError(f"HEAD is already tagged {tags[head]}")
    sections = []
    label = version or "Unreleased"
    entries = []
    for commit, parents, subject in commits:
        if commit in tags:
            if entries or (label != "Unreleased" and commit != head):
                sections.append((label, entries))
            label, entries = tags[commit], []
        if include_commits or len(parents.split()) > 1:
            entries.append(f"- {commit[:7]} - {subject}")
    # Retain tagged releases even if they have no merge commits.
    sections.append((label, entries))
    if version and not any(label == version for label, _ in sections):
        sections.insert(0, (version, []))

    content = "# Change Log\n\n"
    content += "\n\n".join(
        (f"## Release {label}" if label != "Unreleased" else "## Unreleased")
        + ("\n\n" + "\n".join(entries) if entries else "")
        for label, entries in sections
    ) + "\n"
    output = Path(path).expanduser().resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(content, encoding="utf-8")
    return output


def main():
    parser = argparse.ArgumentParser(description="Generate a versioned changelog from Git (replaces output).")
    parser.add_argument("--version", help="Release heading for untagged changes, e.g. v1.0.0")
    parser.add_argument("--include-commits", action="store_true", help="Include direct/squash commits as well as merges")
    parser.add_argument("--output", type=Path, default=DEFAULT_CHANGELOG)
    args = parser.parse_args()
    try:
        output = generate_changelog(path=args.output, version=args.version, include_commits=args.include_commits)
    except (ValueError, RuntimeError, OSError) as exc:
        parser.exit(1, f"Error: {exc}\n")
    print(f"Updated {output}")
    print("Release headings use Git tags; untagged changes use --version or Unreleased.")
    if not args.include_commits:
        print("Only merges are listed. Use --include-commits to include direct/squash commits.")


if __name__ == "__main__":
    main()

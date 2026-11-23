"""Commit chosen working-tree files onto a branch without touching HEAD, the index or the checkout.

Why this exists: this checkout's HEAD is `codex/public-website`, while the files on disk are
`feat/phase1-completion` plus uncommitted work plus another tool's website files. Plain `git status`,
`git add -A`, `git commit` and `git diff <branch>` are therefore wrong here (hundreds of false
deletions, a mega commit on the wrong branch). This script loads a throwaway index from the branch,
adds only the files you list, and makes one commit on top of the branch tip.

  python commit_paths.py candidates [--branch B]
      What differs from the branch tip (M = modified, A = new, D? = gone from disk), minus files
      that are not ours.
  python commit_paths.py commit --paths-file paths.txt --message-file message.txt [--branch B]
      One commit on B (default feat/phase1-completion). A listed path that is gone from disk is
      removed. Not pushed.
  python commit_paths.py snapshot --message-file message.txt
      The handoff branch (handoff/verity-dev, GitHub only): refresh the private notes copy in
      docs/handoff/private/, then commit everything on disk that differs, deletions included. Only
      PRIVATE paths are left out. Not pushed.
  python commit_paths.py refresh-notes
      Only the notes copy step of snapshot.
  python commit_paths.py push [--branch B]
      Plain push of B to origin, never forced, never tags. Only when the owner has said to push.

On the handoff branch every file of the project is ours except PRIVATE; on any other branch the
LEAVE list applies (other tools' work, the website, local notes).

paths.txt: one repo-relative path per line (forward slashes); blank lines and # lines are ignored.
message.txt: the commit message, written with the Write tool (a heredoc mangles quotes and backslashes).
Author is mehboob14 and there is never a Co-Authored-By trailer: the owner's standing rule.
"""

from __future__ import annotations

import argparse
import os
import pathlib
import re
import shutil
import subprocess
import sys
import tempfile

REPO = pathlib.Path(__file__).resolve().parents[2]
DEFAULT_BRANCH = "feat/phase1-completion"
HANDOFF_BRANCH = "handoff/verity-dev"
NUL = chr(0)
CR_LF = bytes([13, 10])

IDENTITY = {
    "GIT_AUTHOR_NAME": "mehboob14",
    "GIT_AUTHOR_EMAIL": "mehboobarshad300@gmail.com",
    "GIT_COMMITTER_NAME": "mehboob14",
    "GIT_COMMITTER_EMAIL": "mehboobarshad300@gmail.com",
}

# Never committed anywhere: the live notes and their entry shims (a scrubbed copy of the notes goes
# to the handoff branch through docs/handoff/private/), and secrets.
PRIVATE = (
    "local-context/",
    "CLAUDE.local.md",
    "AGENTS.override.md",
    ".cursor/rules/00-verity-local-context.mdc",
    ".env",
)

# Not ours to commit onto feat/phase1-completion (the client's snapshot source). Edit this list
# when ownership changes (and tell the owner).
LEAVE = PRIVATE + (
    "AGENTS.md",  # the Codex guide, edited by another tool
    "README.md",  # same
    "website/",  # the public site, shipped from feat/website-deploy
    "website-v0-source",
    "openspec/changes/add-public-website/",
    "openspec/changes/revamp-public-website/",
    "docs/product/continuous-compliance-plan.md",  # written by another tool
    "docs/product/control-evidence-sufficiency.md",  # same
    "docs/handoff/",  # the handoff guide and notes copy belong to the GitHub handoff branch only
)

INDEX = pathlib.Path(tempfile.gettempdir()) / "verity_commit_paths_index"

# The notes copy on the handoff branch. Session tokens, the TOTP seed and the browser profile stay home.
NOTES_COPY = REPO / "docs" / "handoff" / "private"
NOTES_SKIP = re.compile(r"(chrome-profile|demo_session|demo_call_totp|__pycache__)")
SHIMS = ("CLAUDE.local.md", "AGENTS.override.md", ".cursor/rules/00-verity-local-context.mdc")
SECRET = re.compile(
    # "github" "_pat_" is split so this file does not match itself.
    r"BEGIN [A-Z ]*PRIVATE KEY|ghp_[A-Za-z0-9]{20,}|github" r"_pat_[A-Za-z0-9_]{20,}|AKIA[0-9A-Z]{16}"
    r"|(?<![A-Za-z0-9])sk-[A-Za-z0-9_-]{20,}|xox[bp]-[0-9A-Za-z-]{10,}|AIza[0-9A-Za-z_-]{30,}"
)


def git(*args: str, temp_index: bool = True, binary: bool = False) -> str | bytes:
    env = dict(os.environ, **IDENTITY)
    if temp_index:
        env["GIT_INDEX_FILE"] = str(INDEX)
    result = subprocess.run(["git", "-C", str(REPO), *args], env=env, capture_output=True)
    if result.returncode:
        sys.exit(f"git {' '.join(args)} failed:\n{result.stderr.decode('utf-8', 'replace')}")
    return result.stdout if binary else result.stdout.decode("utf-8", "replace")


def load_branch(branch: str) -> str:
    if INDEX.exists():
        INDEX.unlink()
    tip = str(git("rev-parse", f"refs/heads/{branch}", temp_index=False)).strip()
    git("read-tree", tip)
    return tip


def is_ours(path: str, branch: str) -> bool:
    return not path.startswith(PRIVATE if branch == HANDOFF_BRANCH else LEAVE)


def differing() -> list[str]:
    """Paths that differ between the loaded branch tip and the disk."""
    modified = str(git("diff", "--name-only", "-z")).split(NUL)
    untracked = str(git("ls-files", "--others", "--exclude-standard", "-z")).split(NUL)
    return sorted({p for p in modified + untracked if p})


def candidates(branch: str) -> None:
    load_branch(branch)
    untracked = set(str(git("ls-files", "--others", "--exclude-standard", "-z")).split(NUL))
    skipped = 0
    for path in differing():
        if not is_ours(path, branch):
            skipped += 1
            continue
        exists = (REPO / path).exists()
        flag = "A" if path in untracked else ("M" if exists else "D?")
        print(flag, path)
    print(f"\n{skipped} paths skipped as not ours. Review the list: it can include other tools' work.")


def stage(tip: str, path: str) -> None:
    """Put the disk's version of one path into the throwaway index, or remove it when gone."""
    if not (REPO / path).is_file():
        git("update-index", "--force-remove", path)
        return
    branch_blob = subprocess.run(
        ["git", "-C", str(REPO), "cat-file", "-p", f"{tip}:{path}"], capture_output=True
    )
    # core.autocrlf turns a CRLF working copy into LF as it is hashed; what matters is the stored blob.
    blob = str(git("hash-object", "-w", "--path", path, str(REPO / path))).strip()
    stored = git("cat-file", "blob", blob, binary=True)
    had_crlf = branch_blob.returncode == 0 and CR_LF in branch_blob.stdout
    binary_file = path.endswith((".png", ".jpg", ".webp", ".ico", ".xlsx", ".zip", ".pdf", ".woff2"))
    if CR_LF in stored and not had_crlf and not binary_file:
        sys.exit(f"{path} would be stored with CRLF line endings but the branch stores LF")
    listing = str(git("ls-tree", tip, "--", path)).split()
    mode = listing[0] if listing else ("100755" if path.endswith(".sh") else "100644")
    git("update-index", "--add", "--cacheinfo", f"{mode},{blob},{path}")


def write_commit(branch: str, tip: str, message_file: str, count: int) -> None:
    tree = str(git("write-tree")).strip()
    if tree == str(git("rev-parse", f"{tip}^{{tree}}")).strip():
        print(f"{branch}: nothing differs from {tip[:10]}; no commit.")
        return
    new = str(git("commit-tree", tree, "-p", tip, "-F", message_file)).strip()
    git("update-ref", f"refs/heads/{branch}", new, tip, temp_index=False)
    print(f"{branch}: {tip[:10]} -> {new[:10]} ({count} paths). Not pushed.")


def commit(branch: str, paths_file: str, message_file: str) -> None:
    paths = [
        line.strip()
        for line in pathlib.Path(paths_file).read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    ]
    if not paths:
        sys.exit("no paths listed")
    tip = load_branch(branch)
    for path in paths:
        if not is_ours(path, branch):
            sys.exit(f"{path} is not ours to commit onto {branch}")
        stage(tip, path)
    write_commit(branch, tip, message_file, len(paths))


def refresh_notes() -> None:
    """Copy the live notes, their entry shims and Claude's project memory into docs/handoff/private,
    without session tokens or the browser profile, and refuse anything that looks like a secret."""
    copies: list[tuple[pathlib.Path, pathlib.Path]] = []
    for src in (REPO / "local-context").rglob("*"):
        rel = src.relative_to(REPO / "local-context")
        if src.is_file() and not NOTES_SKIP.search(rel.as_posix()):
            copies.append((src, NOTES_COPY / "local-context" / rel))
    for shim in SHIMS:
        if (REPO / shim).is_file():
            copies.append((REPO / shim, NOTES_COPY / "shims" / shim))
    for folder in (pathlib.Path.home() / ".claude" / "projects").glob("*/memory"):
        if (folder / "verity-keycloak-sso.md").is_file():
            copies.extend((src, NOTES_COPY / "claude-memory" / src.name) for src in folder.glob("*.md"))
    gitlab_script = REPO.parent / "push-gitlab.bat"
    if gitlab_script.is_file():
        copies.append((gitlab_script, NOTES_COPY / "push-gitlab.bat"))
    for src, _ in copies:
        if SECRET.search(src.read_text(encoding="utf-8", errors="replace")):
            sys.exit(f"{src} looks like it holds a secret; scrub it before a snapshot")
    if NOTES_COPY.exists():
        shutil.rmtree(NOTES_COPY)
    for src, dst in copies:
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(src, dst)
    print(f"notes copy refreshed: {len(copies)} files in {NOTES_COPY.relative_to(REPO).as_posix()}")


def snapshot(message_file: str) -> None:
    refresh_notes()
    tip = load_branch(HANDOFF_BRANCH)
    paths = [p for p in differing() if is_ours(p, HANDOFF_BRANCH)]
    for path in paths:
        stage(tip, path)
    write_commit(HANDOFF_BRANCH, tip, message_file, len(paths))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("mode", choices=["candidates", "commit", "snapshot", "refresh-notes", "push"])
    parser.add_argument("--branch", default=DEFAULT_BRANCH)
    parser.add_argument("--paths-file")
    parser.add_argument("--message-file")
    args = parser.parse_args()
    if args.mode == "candidates":
        candidates(args.branch)
    elif args.mode == "commit":
        if not (args.paths_file and args.message_file):
            sys.exit("commit needs --paths-file and --message-file")
        commit(args.branch, args.paths_file, args.message_file)
    elif args.mode == "snapshot":
        if not args.message_file:
            sys.exit("snapshot needs --message-file")
        snapshot(args.message_file)
    elif args.mode == "refresh-notes":
        refresh_notes()
    else:
        print(git("push", "origin", f"refs/heads/{args.branch}:refs/heads/{args.branch}", temp_index=False))


main()

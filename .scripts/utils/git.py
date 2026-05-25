import subprocess
import os
from typing import Optional


def get_current_branch() -> str:
    result = subprocess.run(
        ["git", "rev-parse", "--abbrev-ref", "HEAD"],
        capture_output=True, text=True, timeout=10
    )
    if result.returncode != 0:
        return "unknown"
    return result.stdout.strip()


def get_git_diff() -> str:
    result = subprocess.run(
        ["git", "diff", "--staged"],
        capture_output=True, text=True, timeout=10
    )
    return result.stdout


def stage_and_commit(files: list[str], message: str) -> tuple[bool, str]:
    try:
        add_result = subprocess.run(
            ["git", "add"] + files,
            capture_output=True, text=True, timeout=10
        )
        if add_result.returncode != 0:
            return False, f"git add failed: {add_result.stderr}"

        commit_result = subprocess.run(
            ["git", "commit", "-m", message],
            capture_output=True, text=True, timeout=10
        )
        if commit_result.returncode != 0:
            return False, f"git commit failed: {commit_result.stderr}"
        return True, commit_result.stdout
    except subprocess.TimeoutExpired:
        return False, "Git operation timed out"


def gh_auth_status() -> tuple[bool, str]:
    result = subprocess.run(
            ["gh", "auth", "status"],
        capture_output=True, text=True, timeout=10
    )
    if result.returncode != 0:
        return False, "gh CLI not authenticated. Run `gh auth login` and then retry."
    return True, result.stdout


def gh_create_pr(title: str, body: str) -> tuple[bool, str]:
    try:
        result = subprocess.run(
            ["gh", "pr", "create", "--title", title, "--body", body],
            capture_output=True, text=True, timeout=30
        )
        if result.returncode != 0:
            return False, f"gh pr create failed: {result.stderr}"
        return True, result.stdout.strip()
    except subprocess.TimeoutExpired:
        return False, "gh pr create timed out"

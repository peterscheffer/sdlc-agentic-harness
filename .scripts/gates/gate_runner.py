import os
import re
import subprocess
from typing import Callable, Optional

from utils.state import GateResults, SDLCPersistedState


class GateCheck:
    def __init__(self, name: str, description: str, check_fn: Callable[[], tuple[bool, str]]):
        self.name = name
        self.description = description
        self.check_fn = check_fn

    def run(self) -> tuple[bool, str]:
        return self.check_fn()


def check_file_exists(path: str) -> tuple[bool, str]:
    exists = os.path.exists(path)
    if exists:
        return True, f"{path} exists"
    return False, f"{path} does not exist"


def check_file_not_empty(path: str) -> tuple[bool, str]:
    if not os.path.exists(path):
        return False, f"{path} does not exist"
    size = os.path.getsize(path)
    if size > 0:
        return True, f"{path} is non-empty ({size} bytes)"
    return False, f"{path} is empty"


def check_has_heading(filepath: str, heading: str) -> tuple[bool, str]:
    if not os.path.exists(filepath):
        return False, f"{filepath} does not exist"
    with open(filepath) as f:
        content = f.read()
    if heading in content:
        return True, f"Section '{heading}' found"
    return False, f"Missing required section: {heading}"


def check_has_checkbox_tasks(filepath: str) -> tuple[bool, str]:
    if not os.path.exists(filepath):
        return False, f"{filepath} does not exist"
    with open(filepath) as f:
        content = f.read()
    task_pattern = r'- \[ \]'
    tasks = re.findall(task_pattern, content)
    if len(tasks) >= 1:
        return True, f"Found {len(tasks)} task(s)"
    return False, "PRD.md contains no tasks. At least one task is required."


def check_has_recommendation_line(filepath: str) -> tuple[bool, str]:
    if not os.path.exists(filepath):
        return False, f"{filepath} does not exist"
    with open(filepath) as f:
        content = f.read()
    if "recommendation: PASS" in content or "recommendation: FAIL" in content:
        return True, "Recommendation field found"
    return False, "Missing 'recommendation: PASS' or 'recommendation: FAIL'"


def check_all_files_exist(file_list: list[str]) -> tuple[bool, str]:
    missing = [f for f in file_list if not os.path.exists(f)]
    if not missing:
        return True, f"All {len(file_list)} target files exist"
    return False, f"Missing files: {', '.join(missing)}"


def check_command_exits_ok(command: str, timeout: int = 300) -> tuple[bool, str]:
    if not command or command.strip() == "":
        return False, "Command not configured in sdlc.config.json"
    try:
        result = subprocess.run(
            command, shell=True, capture_output=True, text=True, timeout=timeout
        )
        if result.returncode == 0:
            return True, f"Command exited with code 0"
        detail = result.stderr[:200] if result.stderr else result.stdout[:200]
        return False, f"Command exited with code {result.returncode}: {detail}"
    except subprocess.TimeoutExpired:
        return False, f"Command timed out after {timeout} seconds: {command}"
    except FileNotFoundError:
        return False, f"Command not found: {command}"


def check_git_branch_not_base(base_branch: str = "main") -> tuple[bool, str]:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            capture_output=True, text=True, timeout=10
        )
        branch = result.stdout.strip()
        if branch == base_branch:
            return False, f"Current branch is {branch} (the base branch). Create a feature branch first."
        return True, f"On branch '{branch}' (not base branch '{base_branch}')"
    except Exception as e:
        return False, f"Failed to check git branch: {e}"


def check_gh_auth() -> tuple[bool, str]:
    try:
        result = subprocess.run(
            ["gh", "auth", "status"],
            capture_output=True, text=True, timeout=10
        )
        if result.returncode == 0:
            return True, "gh CLI is authenticated"
        return False, "GitHub CLI (gh) is not authenticated. Run: gh auth login"
    except FileNotFoundError:
        return False, "gh CLI not found. Install GitHub CLI: https://cli.github.com/"
    except Exception as e:
        return False, f"gh auth check failed: {e}"


def run_gate_checks(
    stage: str,
    checks: list[GateCheck],
    state: SDLCPersistedState,
) -> tuple[bool, list[str]]:
    all_passed = True
    messages = []
    gate_results = GateResults()

    stage_entry = state.stages.get(stage)

    for check in checks:
        passed, msg = check.run()
        setattr(gate_results, check.name, passed)
        if passed:
            messages.append(f"  [{stage}] \u2713 {check.description}: passed")
        else:
            messages.append(f"  [{stage}] \u2717 {check.description}: {msg}")
            all_passed = False

    if stage_entry:
        stage_entry.gate_results = gate_results

    return all_passed, messages

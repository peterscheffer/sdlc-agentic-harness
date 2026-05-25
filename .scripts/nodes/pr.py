import os
import subprocess
from datetime import datetime, timezone

from utils.state import SDLCPersistedState
from utils.config import SDLCConfig
from gates.gate_runner import (
    GateCheck, run_gate_checks,
    check_gh_auth, check_git_branch_not_base,
)


def execute_pr(state: SDLCPersistedState, config: SDLCConfig, force: bool = False) -> SDLCPersistedState:
    print("\n[pr] Preparing GitHub Pull Request...")

    state.stages["pr"].status = "in_progress"
    state.current_stage = "pr"

    recommendation = state.stages["review"].recommendation
    if recommendation == "FAIL" and not force:
        print(
            "[pr] \u26a0 Review recommendation is FAIL.\n"
            "Are you sure you want to submit? (yes/no)"
        )
        try:
            response = input().strip().lower()
        except (EOFError, KeyboardInterrupt):
            print("\n[pr] PR submission cancelled.")
            state.stages["pr"].status = "failed"
            state.stages["pr"].reason = "User cancelled force override"
            return state
        if response != "yes":
            print("[pr] PR submission cancelled.")
            state.stages["pr"].status = "failed"
            state.stages["pr"].reason = "User cancelled force override"
            state.current_stage = "review"
            return state

    gh_ok, gh_msg = check_gh_auth()
    if not gh_ok:
        print(f"[pr] \u2717 {gh_msg}")
        state.stages["pr"].status = "failed"
        state.stages["pr"].reason = gh_msg
        state.current_stage = "pr"
        return state

    branch_ok, branch_msg = check_git_branch_not_base(config.github.base_branch)
    if not branch_ok:
        print(f"[pr] \u2717 {branch_msg}")
        state.stages["pr"].status = "failed"
        state.stages["pr"].reason = branch_msg
        state.current_stage = "pr"
        return state

    print("[pr] Committing SDLC artefacts...")

    sdlc_files = _collect_sdlc_artefacts()
    commit_msg = _build_commit_message(state)

    try:
        add_result = subprocess.run(
            ["git", "add"] + sdlc_files,
            capture_output=True, text=True, timeout=10
        )
        if add_result.returncode != 0:
            print(f"[pr] \u2717 git add failed: {add_result.stderr}")
            state.stages["pr"].status = "failed"
            state.stages["pr"].reason = f"git add failed: {add_result.stderr}"
            return state

        commit_result = subprocess.run(
            ["git", "commit", "-m", commit_msg],
            capture_output=True, text=True, timeout=10
        )
        if commit_result.returncode != 0 and "nothing to commit" not in commit_result.stderr:
            print(f"[pr] \u26a0 git commit warning: {commit_result.stderr}")
    except Exception as e:
        print(f"[pr] \u2717 Git operation failed: {e}")
        state.stages["pr"].status = "failed"
        state.stages["pr"].reason = str(e)
        return state

    pr_title = _build_pr_title(state)
    pr_body = _build_pr_body(state)

    print(f"[pr] Creating PR: \"{pr_title}\"")
    print(f"[pr] Using gh pr create...")

    try:
        pr_result = subprocess.run(
            [
                "gh", "pr", "create",
                "--title", pr_title,
                "--body", pr_body,
                "--base", config.github.base_branch,
            ],
            capture_output=True, text=True, timeout=30
        )
        if pr_result.returncode != 0:
            print(f"[pr] \u2717 gh pr create failed: {pr_result.stderr}")
            state.stages["pr"].status = "failed"
            state.stages["pr"].reason = pr_result.stderr
            return state

        pr_url = pr_result.stdout.strip()
    except FileNotFoundError:
        print("[pr] \u2717 gh CLI not found. Install GitHub CLI: https://cli.github.com/")
        state.stages["pr"].status = "failed"
        state.stages["pr"].reason = "gh CLI not found"
        return state
    except subprocess.TimeoutExpired:
        print("[pr] \u2717 gh pr create timed out")
        state.stages["pr"].status = "failed"
        state.stages["pr"].reason = "gh pr create timed out"
        return state

    passed, messages = run_gate_checks("pr", [
        GateCheck("gh_authenticated", "gh CLI authenticated",
                  lambda: check_gh_auth()),
        GateCheck("not_on_base_branch", "Not on base branch",
                  lambda: check_git_branch_not_base(config.github.base_branch)),
        GateCheck("pr_created", "PR created successfully",
                  lambda: (True, pr_url) if pr_url else (False, "PR URL not captured")),
    ], state)

    for msg in messages:
        print(msg)

    if passed:
        state.pr_url = pr_url
        state.stages["pr"].status = "complete"
        state.stages["pr"].completed_at = datetime.now(timezone.utc).isoformat()
        state.current_stage = "complete"
        if "pr" not in state.completed_stages:
            state.completed_stages.append("pr")

        print(f"\n[pr] \u2713 Pull Request created")
        print(f"[pr] URL: {pr_url}")
        print(f"[pr] All artefacts committed to sdlc/")
        print(f"[pr] Pipeline complete!")
    else:
        print(f"[pr] \u2717 PR submission failed")
        state.stages["pr"].status = "failed"

    return state


def _collect_sdlc_artefacts() -> list[str]:
    artefacts = []
    for root, dirs, files in os.walk("sdlc"):
        for f in files:
            artefacts.append(os.path.join(root, f))
    return artefacts


def _build_commit_message(state: SDLCPersistedState) -> str:
    completed = ", ".join(state.completed_stages) if state.completed_stages else "none"
    return (
        f"chore: add SDLC pipeline artefacts\n\n"
        f"Pipeline ID: {state.pipeline_id}\n"
        f"Stages completed: [{completed}]"
    )


def _build_pr_title(state: SDLCPersistedState) -> str:
    intent = state.intent or "feature"
    intent_clean = intent.strip().strip("'\"").strip()
    return f"feat: {intent_clean}"


def _build_pr_body(state: SDLCPersistedState) -> str:
    lines = []

    prd_summary = ""
    if os.path.exists("sdlc/planning/PRD.md"):
        with open("sdlc/planning/PRD.md") as f:
            prd_content = f.read()
        for para in prd_content.split("\n\n"):
            if not para.startswith("#"):
                prd_summary = para.strip()
                break

    lines.append("## Summary")
    lines.append(prd_summary or state.intent or "")
    lines.append("")

    review_content = ""
    if os.path.exists("sdlc/review/REVIEW.md"):
        with open("sdlc/review/REVIEW.md") as f:
            review_content = f.read()

    change_summary = ""
    for line in review_content.split("\n"):
        if line.strip() and not line.startswith("#"):
            change_summary += f"- {line.strip()}\n"

    lines.append("## Changes")
    lines.append(change_summary or "- See diff for details")
    lines.append("")

    test_content = ""
    if os.path.exists("sdlc/testing/TEST_REPORT.md"):
        with open("sdlc/testing/TEST_REPORT.md") as f:
            test_content = f.read()

    test_summary_lines = []
    for line in test_content.split("\n"):
        if "**Tests" in line or "**Coverage" in line or "**Status" in line:
            test_summary_lines.append(f"- {line.strip('*')}")

    lines.append("## Test Evidence")
    if test_summary_lines:
        lines.extend(test_summary_lines)
    else:
        lines.append("- See TEST_REPORT.md for details")
    lines.append("")

    recommendation = state.stages["review"].recommendation or "PASS"
    lines.append("## Review Outcome")
    lines.append(f"recommendation: {recommendation}")
    lines.append("")

    lines.append("## Pipeline Artefacts")
    lines.append("- [PRD](sdlc/planning/PRD.md)")
    lines.append("- [Architecture](sdlc/architecture/ARCH.md)")
    lines.append("- [Review](sdlc/review/REVIEW.md)")
    lines.append("- [Test Report](sdlc/testing/TEST_REPORT.md)")
    lines.append("")

    return "\n".join(lines)

import os
import subprocess
from datetime import datetime, timezone

from utils.state import SDLCPersistedState
from utils.config import SDLCConfig
from utils.llm import call_llm
from gates.gate_runner import (
    GateCheck, run_gate_checks,
    check_file_exists, check_has_recommendation_line,
)
from gates.principles_checker import load_principles

REVIEW_PATH = "sdlc/review/REVIEW.md"


def execute_review(state: SDLCPersistedState, config: SDLCConfig) -> SDLCPersistedState:
    print("\n[review] Generating structured self-review...")

    os.makedirs("sdlc/review", exist_ok=True)

    git_diff = _get_git_diff()
    print("[review] Computing git diff...")

    prd_content = ""
    if os.path.exists("sdlc/planning/PRD.md"):
        with open("sdlc/planning/PRD.md") as f:
            prd_content = f.read()

    arch_content = ""
    if os.path.exists("sdlc/architecture/ARCH.md"):
        with open("sdlc/architecture/ARCH.md") as f:
            arch_content = f.read()

    test_report = ""
    if os.path.exists("sdlc/testing/TEST_REPORT.md"):
        with open("sdlc/testing/TEST_REPORT.md") as f:
            test_report = f.read()

    principles_rules, principles_warning = load_principles()

    system_prompt = (
        "You are a code reviewer. Produce a structured REVIEW.md with the following sections:\n"
        "- ## Change Summary\n"
        "- ## PRD Alignment\n"
        "- ## PRINCIPLES Compliance\n"
        "- ## Test Evidence\n"
        "- ## Recommendation\n"
        "- ## Notes\n\n"
        "The recommendation line must be exactly: 'recommendation: PASS' or 'recommendation: FAIL'"
    )

    context_parts = [
        f"## Git Diff\n```diff\n{git_diff[-2000:]}\n```" if git_diff else "## Git Diff\nNo changes detected.",
        f"## PRD\n{prd_content}" if prd_content else "",
        f"## Architecture\n{arch_content}" if arch_content else "",
        f"## Test Report\n{test_report}" if test_report else "",
    ]

    if principles_rules:
        rules_str = "\n".join(
            f"- {r.rule_id} ({r.severity}): {r.description}" for r in principles_rules
        )
        context_parts.append(f"## PRINCIPLES Rules\n{rules_str}")

    prompt = "\n\n".join(p for p in context_parts if p)

    try:
        content = call_llm(
            prompt=prompt,
            stage="review",
            config=config,
            system_prompt=system_prompt,
        )
    except RuntimeError as e:
        print(f"[review] \u2717 Error: {e}")
        print("Retry with: /sdlc review")
        state.stages["review"].status = "failed"
        state.current_stage = "review"
        return state

    with open(REVIEW_PATH, "w") as f:
        f.write(content)

    print(f"[review] \u2713 REVIEW.md generated at {REVIEW_PATH}")

    recommendation = _extract_recommendation(content)
    if recommendation:
        state.stages["review"].recommendation = recommendation

    passed, messages = run_gate_checks("review", [
        GateCheck("review_exists", "REVIEW.md exists",
                  lambda: check_file_exists(REVIEW_PATH)),
        GateCheck("recommendation_present", "Recommendation field present",
                  lambda: check_has_recommendation_line(REVIEW_PATH)),
    ], state)

    for msg in messages:
        print(msg)

    if passed:
        state.stages["review"].status = "complete"
        state.stages["review"].completed_at = datetime.now(timezone.utc).isoformat()
        state.stages["review"].artefact = REVIEW_PATH
        state.current_stage = "review"
        if "review" not in state.completed_stages:
            state.completed_stages.append("review")

        print(f"\n[review] \u2713 Gate checks passed (2/2)")

        if recommendation == "FAIL":
            reason = _extract_fail_reason(content)
            print(f"[review] \u26a0 Recommendation: FAIL")
            if reason:
                print(f"[review] Reason: {reason}")
            print(f"To override and submit PR anyway: /sdlc pr --force")
            print(f"To re-enter coding: /sdlc coding")
        else:
            print(f"[review] \u2713 Recommendation: PASS")
            print(f"Ready to submit PR. Run: /sdlc pr")
    else:
        print(f"\n[review] \u2717 Gate checks failed")
        state.stages["review"].status = "failed"
        state.current_stage = "review"

    return state


def _get_git_diff() -> str:
    try:
        result = subprocess.run(
            ["git", "diff", "HEAD"],
            capture_output=True, text=True, timeout=10
        )
        if result.returncode == 0 and result.stdout:
            return result.stdout

        result = subprocess.run(
            ["git", "diff", "--cached"],
            capture_output=True, text=True, timeout=10
        )
        return result.stdout
    except Exception:
        return ""


def _extract_recommendation(content: str) -> str:
    for line in content.split("\n"):
        stripped = line.strip()
        if stripped.startswith("recommendation:"):
            parts = stripped.split(":", 1)
            if len(parts) == 2:
                return parts[1].strip()
    return ""


def _extract_fail_reason(content: str) -> str:
    for line in content.split("\n"):
        stripped = line.strip()
        if stripped.startswith("recommendation: FAIL"):
            return "See REVIEW.md for details"
    return ""

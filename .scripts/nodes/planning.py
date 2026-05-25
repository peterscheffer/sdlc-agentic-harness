import os
from datetime import datetime, timezone

from utils.state import SDLCPersistedState
from utils.config import SDLCConfig
from utils.llm import call_llm
from gates.gate_runner import (
    GateCheck, run_gate_checks,
    check_file_exists, check_has_heading, check_has_checkbox_tasks,
)

PRD_PATH = "sdlc/planning/PRD.md"
REQUIRED_SECTIONS = [
    "## Summary",
    "## Goals",
    "## Non-Goals",
    "## Tasks",
    "## Acceptance Criteria",
    "## Affected Files",
]


def execute_planning(state: SDLCPersistedState, config: SDLCConfig, intent: str) -> SDLCPersistedState:
    print("\n[planning] Generating PRD.md from developer intent...")

    os.makedirs("sdlc/planning", exist_ok=True)

    system_prompt = (
        "You are an expert product requirements document generator. "
        "Generate a structured PRD.md following the exact schema specified."
    )
    user_prompt = (
        f"Generate a Product Requirements Document for the following intent:\n\n{intent}\n\n"
        f"The PRD MUST contain these sections:\n"
        f"- ## Summary\n- ## Goals\n- ## Non-Goals\n"
        f"- ## Tasks (with at least one checkbox '- [ ]' item)\n"
        f"- ## Acceptance Criteria\n- ## Affected Files\n\n"
        f"Output the PRD as valid Markdown."
    )

    try:
        content = call_llm(
            prompt=user_prompt,
            stage="planning",
            config=config,
            system_prompt=system_prompt,
        )
    except RuntimeError as e:
        print(f"\n[planning] \u2717 Error: {e}")
        print("Retry with: /sdlc planning '<intent>'")
        state.stages["planning"].status = "failed"
        state.current_stage = "planning"
        return state

    with open(PRD_PATH, "w") as f:
        f.write(content)

    print(f"[planning] \u2713 PRD.md written to {PRD_PATH}")

    passed, messages = run_gate_checks("planning", [
        GateCheck("prd_exists", "PRD.md exists",
                  lambda: check_file_exists(PRD_PATH)),
        GateCheck("prd_schema_valid", "PRD.md schema valid",
                  lambda: _check_prd_schema()),
        GateCheck("tasks_defined", "Tasks defined",
                  lambda: check_has_checkbox_tasks(PRD_PATH)),
    ], state)

    for msg in messages:
        print(msg)

    if passed:
        state.stages["planning"].status = "complete"
        state.stages["planning"].completed_at = datetime.now(timezone.utc).isoformat()
        state.stages["planning"].artefact = PRD_PATH
        state.current_stage = "planning"
        state.completed_stages.append("planning")
        print(f"\n[planning] \u2713 Gate checks passed (3/3)")
        print(f"\nReview {PRD_PATH}, then run: /sdlc ui-design  (or /sdlc architecture to skip UI)")
    else:
        print(f"\n[planning] \u2717 Gate checks failed")
        state.stages["planning"].status = "failed"
        state.current_stage = "planning"

    return state


def _check_prd_schema() -> tuple[bool, str]:
    if not os.path.exists(PRD_PATH):
        return False, f"{PRD_PATH} does not exist"
    with open(PRD_PATH) as f:
        content = f.read()
    missing = [s for s in REQUIRED_SECTIONS if s not in content]
    if missing:
        sections_str = ", ".join(missing)
        return False, f"PRD.md is missing required section(s): {sections_str}"
    return True, "All required sections present"

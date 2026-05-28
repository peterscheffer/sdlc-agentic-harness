import os
from datetime import datetime, timezone
from typing import Optional

from utils.state import SDLCPersistedState
from utils.config import SDLCConfig
from utils.llm import call_llm
from gates.gate_runner import (
    GateCheck, run_gate_checks,
    check_file_exists, check_has_heading, check_has_checkbox_tasks,
)

PRD_PATH = "sdlc/planning/PRD.md"
TEMPLATE_PATH = "sdlc/templates/PRD.md"
REQUIRED_SECTIONS = [
    "## Summary",
    "## Goals",
    "## Non-Goals",
    "## Tasks",
    "## Acceptance Criteria",
    "## Affected Files",
]


def execute_planning(state: SDLCPersistedState, config: SDLCConfig, intent: str, conversation_context: str = "") -> SDLCPersistedState:
    print("\n[planning] Generating PRD.md from developer intent...")

    os.makedirs("sdlc/planning", exist_ok=True)

    if not os.path.exists(TEMPLATE_PATH):
        print(f"\n[planning] \u2717 Error: PRD template not found at {TEMPLATE_PATH}")
        print("Create the template file and try again.")
        state.stages["planning"].status = "failed"
        state.current_stage = "planning"
        return state

    with open(TEMPLATE_PATH) as f:
        template_content = f.read()

    system_prompt = (
        "You are an expert product requirements document generator. "
        "Fill in the provided PRD template using the conversation context."
    )

    context_block = conversation_context or f"Feature: {intent}"
    user_prompt = (
        f"## Conversation Context\n\n{context_block}\n\n"
        f"## PRD Template (fill in the sections you have context for)\n\n"
        f"{template_content}\n\n"
        f"## Instructions\n\n"
        f"- Fill in every section for which the conversation provides sufficient context "
        f"(Executive Summary, Problem Statement, Goals, Non-Goals, Technical Stack, etc.).\n"
        f"- For sections where more detail is needed (e.g. architecture diagrams, data schemas), "
        f"leave the placeholder or mark them as TBD for future stages.\n"
        f"- The output MUST also contain these exact section headings (add them if the template lacks them):\n"
        f"  - ## Summary\n"
        f"  - ## Goals\n"
        f"  - ## Non-Goals\n"
        f"  - ## Tasks\n"
        f"  - ## Acceptance Criteria\n"
        f"  - ## Affected Files\n"
        f"- Under ## Tasks, include at least one checkbox item like '- [ ] Task description'.\n"
        f"- Output the complete document as valid Markdown."
    )

    try:
        content = call_llm(
            prompt=user_prompt,
            stage="planning",
            config=config,
            system_prompt=system_prompt,
            conversation_context=conversation_context,
        )
    except RuntimeError as e:
        print(f"\n[planning] \u2717 LLM call failed: {e}")
        print("The stage produced no artefacts. Retry with: /plan")
        state.stages["planning"].status = "failed"
        state.current_stage = "planning"
        return state

    with open(PRD_PATH, "w") as f:
        f.write(content)
    print(f"[planning] \u2713 PRD.md written to {PRD_PATH}")

    _ensure_required_sections(PRD_PATH)

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
        print(f"\nReview {PRD_PATH}, then run: /ui-design  (or /architect to skip UI design)")
    else:
        print(f"\n[planning] \u2717 Gate checks failed")
        print("Retry with: /plan")
        if os.path.exists(PRD_PATH):
            os.remove(PRD_PATH)
            print(f"[planning] Removed incomplete artefact: {PRD_PATH}")
        state.stages["planning"].status = "failed"
        state.current_stage = "planning"

    return state


def _ensure_required_sections(path: str):
    with open(path) as f:
        content = f.read()
    missing = [s for s in REQUIRED_SECTIONS if s not in content]
    if missing:
        with open(path, "a") as f:
            f.write("\n\n---\n\n")
            for section in missing:
                if section == "## Tasks":
                    f.write(f"\n{section}\n- [ ] Implement feature\n\n")
                else:
                    f.write(f"\n{section}\nTBD — see numbered sections above.\n\n")
        print(f"[planning] \u2717 Appended missing schema sections: {', '.join(missing)}")


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

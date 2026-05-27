import os
import re
from datetime import datetime, timezone

from utils.state import SDLCPersistedState
from utils.config import SDLCConfig
from utils.llm import call_llm
from gates.gate_runner import (
    GateCheck, run_gate_checks,
    check_file_exists, check_has_heading,
)

DESIGN_PATH = "sdlc/ui-design/DESIGN.md"
UI_KEYWORDS = ["component", "page", "view", "screen", "UI", "frontend", "form", "modal", "layout"]

REQUIRED_DESIGN_SECTIONS = ["## Overview"]


def should_skip_ui_design(state: SDLCPersistedState) -> bool:
    prd_path = "sdlc/planning/PRD.md"
    if not os.path.exists(prd_path):
        return True
    with open(prd_path) as f:
        content = f.read().lower()
    for kw in UI_KEYWORDS:
        if kw.lower() in content:
            return False
    return True


def execute_ui_design(state: SDLCPersistedState, config: SDLCConfig, conversation_context: str = "") -> SDLCPersistedState:
    print("\n[ui-design] Checking PRD for UI keywords...")

    skip = should_skip_ui_design(state)
    if skip:
        print("[ui-design] No UI keywords found in PRD. Skipping stage.")
        state.stages["ui-design"].status = "skipped"
        state.stages["ui-design"].reason = "No UI keywords found in PRD"
        return state

    print("[ui-design] UI keywords detected. Generating DESIGN.md...")
    os.makedirs("sdlc/ui-design", exist_ok=True)

    prd_content = ""
    if os.path.exists("sdlc/planning/PRD.md"):
        with open("sdlc/planning/PRD.md") as f:
            prd_content = f.read()

    system_prompt = (
        "You are a UI/UX design specification generator. "
        "Generate a DESIGN.md conforming to the Google Stitch DESIGN.md specification. "
        "Include at minimum: ## Overview and ## Components (or ## Screens) sections."
    )
    user_prompt = (
        f"Based on the following PRD, generate a UI design specification:\n\n{prd_content}\n\n"
        f"The DESIGN.md MUST include:\n"
        f"- ## Overview\n- ## Components (or ## Screens)\n"
        f"- ## States (recommended for interactive components)\n\n"
        f"Output as valid Markdown."
    )

    try:
        content = call_llm(
            prompt=user_prompt,
            stage="ui-design",
            config=config,
            system_prompt=system_prompt,
            conversation_context=conversation_context,
        )
    except RuntimeError as e:
        print(f"\n[ui-design] \u2717 Error: {e}")
        print("Retry with: /ui-design")
        state.stages["ui-design"].status = "failed"
        return state

    with open(DESIGN_PATH, "w") as f:
        f.write(content)

    print(f"[ui-design] \u2713 DESIGN.md written to {DESIGN_PATH}")

    passed, messages = run_gate_checks("ui-design", [
        GateCheck("design_md_exists", "DESIGN.md exists",
                  lambda: check_file_exists(DESIGN_PATH)),
        GateCheck("design_schema_valid", "DESIGN.md schema valid",
                  lambda: _check_design_schema()),
    ], state)

    for msg in messages:
        print(msg)

    if passed:
        state.stages["ui-design"].status = "complete"
        state.stages["ui-design"].completed_at = datetime.now(timezone.utc).isoformat()
        state.stages["ui-design"].artefact = DESIGN_PATH
        state.completed_stages.append("ui-design")
        print(f"\n[ui-design] \u2713 Gate checks passed (2/2)")
        print(f"To proceed with architecture, run: /architecture")
    else:
        print(f"\n[ui-design] \u2717 Gate checks failed")
        state.stages["ui-design"].status = "failed"

    return state


def _check_design_schema() -> tuple[bool, str]:
    if not os.path.exists(DESIGN_PATH):
        return False, f"{DESIGN_PATH} does not exist"
    with open(DESIGN_PATH) as f:
        content = f.read()
    missing = [s for s in REQUIRED_DESIGN_SECTIONS if s not in content]
    if missing:
        sections_str = ", ".join(missing)
        return False, f"DESIGN.md is missing required Stitch section(s): {sections_str}"
    has_components = "## Components" in content
    has_screens = "## Screens" in content
    if not has_components and not has_screens:
        return False, "DESIGN.md is missing required Stitch section: ## Components or ## Screens"
    return True, "All required sections present"

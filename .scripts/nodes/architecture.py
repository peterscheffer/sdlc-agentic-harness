import os
from datetime import datetime, timezone

from utils.state import SDLCPersistedState
from utils.config import SDLCConfig
from utils.llm import call_llm
from gates.gate_runner import (
    GateCheck, run_gate_checks,
    check_file_exists, check_has_heading,
)
from gates.principles_checker import (
    load_principles, validate_architecture,
)

ARCH_PATH = "sdlc/architecture/ARCH.md"
REQUIRED_ARCH_SECTIONS = [
    "## Overview",
    "## Target Files",
    "## Design Decisions",
    "## PRINCIPLES Compliance",
    "## Risks",
]


def execute_architecture(state: SDLCPersistedState, config: SDLCConfig, conversation_context: str = "") -> SDLCPersistedState:
    print("\n[architecture] Generating ARCH.md from PRD and prior stages...")

    os.makedirs("sdlc/architecture", exist_ok=True)

    prd_content = ""
    if os.path.exists("sdlc/planning/PRD.md"):
        with open("sdlc/planning/PRD.md") as f:
            prd_content = f.read()

    design_content = ""
    if os.path.exists("sdlc/ui-design/DESIGN.md"):
        with open("sdlc/ui-design/DESIGN.md") as f:
            design_content = f.read()

    principles_rules, principles_warning = load_principles()
    if principles_warning:
        print(f"[architecture] {principles_warning}")

    rules_context = ""
    if principles_rules:
        rules_lines = []
        for r in principles_rules:
            rules_lines.append(f"- {r.rule_id} ({r.severity}): {r.description}")
        rules_context = "\n".join(rules_lines)

    system_prompt = (
        "You are a software architect. Generate an architecture decision record "
        "that follows the project's PRINCIPLES and produces a clear implementation plan."
    )
    user_prompt_parts = [
        f"PRD:\n{prd_content}",
    ]
    if design_content:
        user_prompt_parts.append(f"UI Design:\n{design_content}")
    if rules_context:
        user_prompt_parts.append(f"PRINCIPLES Rules to validate against:\n{rules_context}")
    user_prompt_parts.append(
        f"IMPORTANT: The conversation context (included in the system prompt) contains the LATEST decisions "
        f"and takes PRECEDENCE over any conflicting information in the PRD or other artefacts.\n\n"
        f"The ARCH.md MUST contain these sections:\n"
        f"- ## Overview\n- ## Target Files (table with File, Action, Description columns)\n"
        f"- ## Design Decisions\n- ## PRINCIPLES Compliance\n- ## Risks\n\n"
        f"Output as valid Markdown."
    )
    user_prompt = "\n\n".join(user_prompt_parts)

    try:
        content = call_llm(
            prompt=user_prompt,
            stage="architecture",
            config=config,
            system_prompt=system_prompt,
            conversation_context=conversation_context,
        )
    except RuntimeError as e:
        print(f"\n[architecture] \u2717 Error: {e}")
        print("Retry with: /sdlc architecture")
        state.stages["architecture"].status = "failed"
        state.current_stage = "architecture"
        return state

    with open(ARCH_PATH, "w") as f:
        f.write(content)

    print(f"[architecture] \u2713 ARCH.md written to {ARCH_PATH}")

    if principles_rules:
        violations, has_errors = validate_architecture(ARCH_PATH, principles_rules)
        if violations:
            print(f"\n[architecture] PRINCIPLES violations detected:")
            for v in violations:
                if v["status"] != "PASS":
                    icon = "\u2717" if v["status"] == "FAIL" else "\u26a0"
                    print(f"  {icon} {v['rule_id']}: {v['description']} [{v['status']}]")
            if has_errors:
                for v in violations:
                    if v["status"] == "FAIL":
                        print(f"\n[architecture] \u2717 Architecture violates PRINCIPLES.md rule: {v['rule_id']}")
                        print(f"  {v['description']}")

    passed, messages = run_gate_checks("architecture", [
        GateCheck("arch_exists", "ARCH.md exists",
                  lambda: check_file_exists(ARCH_PATH)),
        GateCheck("arch_schema_valid", "ARCH.md schema valid",
                  lambda: _check_arch_schema()),
        GateCheck("principles_errors_zero", "Zero error-severity PRINCIPLES violations",
                  lambda: _check_principles_errors(principles_rules if principles_rules else [])),
    ], state)

    for msg in messages:
        print(msg)

    if passed and not _check_principles_errors(principles_rules if principles_rules else [])[0]:
        if principles_rules:
            print(f"\n[architecture] \u2717 PRINCIPLES errors found. Stage failed.")
        state.stages["architecture"].status = "failed"
        state.current_stage = "architecture"
    elif passed:
        state.stages["architecture"].status = "complete"
        state.stages["architecture"].completed_at = datetime.now(timezone.utc).isoformat()
        state.stages["architecture"].artefact = ARCH_PATH
        state.current_stage = "architecture"
        state.completed_stages.append("architecture")
        print(f"\n[architecture] \u2713 Gate checks passed (3/3)")
        print(f"\nReview {ARCH_PATH}, then run: /sdlc coding")
    else:
        print(f"\n[architecture] \u2717 Gate checks failed")
        state.stages["architecture"].status = "failed"
        state.current_stage = "architecture"

    return state


def _check_arch_schema() -> tuple[bool, str]:
    if not os.path.exists(ARCH_PATH):
        return False, f"{ARCH_PATH} does not exist"
    with open(ARCH_PATH) as f:
        content = f.read()
    missing = [s for s in REQUIRED_ARCH_SECTIONS if s not in content]
    if missing:
        sections_str = ", ".join(missing)
        return False, f"ARCH.md is missing required section(s): {sections_str}"
    return True, "All required sections present"


def _check_principles_errors(rules: list) -> tuple[bool, str]:
    arch_content = ""
    if os.path.exists(ARCH_PATH):
        with open(ARCH_PATH) as f:
            arch_content = f.read()
    violations, has_errors = validate_architecture(ARCH_PATH, rules)
    if has_errors:
        error_rules = [v for v in violations if v["status"] == "FAIL"]
        ids = ", ".join(v["rule_id"] for v in error_rules)
        return False, f"Error-severity PRINCIPLES violations: {ids}"
    return True, "Zero error-severity PRINCIPLES violations"

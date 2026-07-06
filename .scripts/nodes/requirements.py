import os
import re
from datetime import datetime, timezone
from typing import Optional

from utils.state import SDLCPersistedState
from utils.config import SDLCConfig, ProfileConfig
from utils.llm import call_llm
from utils.output_validator import validate_stage_output
from gates.gate_runner import (
    GateCheck, run_gate_checks,
    check_file_exists,
)
from profiles import get_profiles, validate_profile_names

REQUIREMENTS_PATH = "sdlc/requirements/REQUIREMENTS.md"
REQUIREMENTS_DIR = "sdlc/requirements"

# Section slots; each slot is satisfied by any of its aliases. The legacy
# "## Behavioural Requirements" heading is accepted where "## Acceptance
# Criteria" is expected so pre-existing artefacts still validate.
SECTION_SLOTS = [
    ("## Overview",),
    ("## Functional Requirements",),
    ("## Non-Functional Requirements",),
    ("## Acceptance Criteria", "## Behavioural Requirements"),
]
REQUIRED_SECTIONS = [slot[0] for slot in SECTION_SLOTS]

SPEC_PROFILES_RE = re.compile(r'^SPEC_PROFILES:\s*(.+)$', re.MULTILINE)
SPEC_TOOLCHAIN_RE = re.compile(r'^SPEC_TOOLCHAIN:\s*(.+)$', re.MULTILINE)
REQUIREMENTS_MD_BLOCK = re.compile(
    r"```(?:requirements-md|markdown)\s*\n(.*?)```", re.DOTALL
)


def execute_requirements(state: SDLCPersistedState, config: SDLCConfig,
                         conversation_context: str = "",
                         profiles_override: Optional[list[str]] = None) -> SDLCPersistedState:
    try:
        profiles = _resolve_profiles(state, config, conversation_context, profiles_override)
    except ValueError as e:
        print(f"\n[requirements] ✗ {e}")
        state.stages["requirements"].status = "failed"
        state.current_stage = "requirements"
        return state

    profile_names = [p.name for p in profiles]
    state.spec_profiles = profile_names
    print(f"\n[requirements] Generating REQUIREMENTS.md with spec profile(s): "
          f"{', '.join(profile_names)}...")

    os.makedirs(REQUIREMENTS_DIR, exist_ok=True)

    prd_content = ""
    if os.path.exists("sdlc/planning/PRD.md"):
        with open("sdlc/planning/PRD.md") as f:
            prd_content = f.read()

    design_content = ""
    if os.path.exists("sdlc/ui-design/DESIGN.md"):
        with open("sdlc/ui-design/DESIGN.md") as f:
            design_content = f.read()

    arch_content = ""
    if os.path.exists("sdlc/architecture/ARCH.md"):
        with open("sdlc/architecture/ARCH.md") as f:
            arch_content = f.read()

    system_prompt = (
        "You are a requirements analyst. Generate a detailed requirements specification "
        "and machine-verifiable spec artifacts based on the project's PRD, UI design, "
        "and architecture. The solution may be a UI, a service, an API, an integration, "
        "or a data layer — specify whatever the input documents describe."
    )

    parts = [
        "# Input Documents\n",
    ]
    if prd_content:
        parts.append(f"## PRD\n{prd_content}\n")
    if design_content:
        parts.append(f"## UI Design\n{design_content}\n")
    if arch_content:
        parts.append(f"## Architecture\n{arch_content}\n")

    parts.append(
        "## Instructions\n\n"
        "Based on the input documents above and the conversation context, generate:\n\n"
        "### 1. REQUIREMENTS.md (written to the first output block below)\n"
        f"The REQUIREMENTS.md MUST contain these exact sections:\n"
        f"{', '.join(REQUIRED_SECTIONS)}\n\n"
        "- **## Overview**: 2-3 sentences summarizing the requirements scope\n"
        "- **## Functional Requirements**: Table with columns: ID, Description, Priority (High/Medium/Low)\n"
        "- **## Non-Functional Requirements**: Table with columns: ID, Description\n"
        "- **## Acceptance Criteria**: Table with columns: ID, Criterion, Verified By "
        "(which spec artifact/test verifies it)\n\n"
        "Requirements output format:\n"
        "```requirements-md\n"
        "[REQUIREMENTS.md content here]\n"
        "```\n"
    )

    for idx, profile in enumerate(profiles, start=2):
        parts.append(f"### {idx}. {profile.display_name} spec\n" + profile.spec_prompt_fragment())

    user_prompt = "\n".join(parts)

    try:
        content = call_llm(
            prompt=user_prompt,
            stage="requirements",
            config=config,
            system_prompt=system_prompt,
            conversation_context=conversation_context,
            pipeline_id=state.pipeline_id,
        )
    except RuntimeError as e:
        print(f"\n[requirements] ✗ LLM call failed: {e}")
        print("The stage produced no artefacts. Retry with: /requirements")
        state.stages["requirements"].status = "failed"
        state.current_stage = "requirements"
        return state

    valid, reason = validate_stage_output(content, "requirements")
    if not valid:
        print(f"\n[requirements] ✗ {reason}")
        print("Retry with: /requirements")
        state.stages["requirements"].status = "failed"
        state.current_stage = "requirements"
        return state

    _write_requirements_md(content)
    print(f"[requirements] ✓ REQUIREMENTS.md written to {REQUIREMENTS_PATH}")

    for profile in profiles:
        written = profile.parse_and_write(content)
        if written:
            print(f"[requirements] ✓ {profile.display_name} spec artifact(s):")
            for path in written:
                print(f"       {path}")

    _ensure_required_sections(REQUIREMENTS_PATH)

    gate_checks = [
        GateCheck("requirements_md_exists", "REQUIREMENTS.md exists",
                  lambda: check_file_exists(REQUIREMENTS_PATH)),
        GateCheck("requirements_schema_valid", "REQUIREMENTS.md schema valid",
                  lambda: _check_requirements_schema()),
    ]
    for profile in profiles:
        gate_checks.extend(profile.requirements_gate_checks())

    passed, messages = run_gate_checks("requirements", gate_checks, state)

    for msg in messages:
        print(msg)

    if passed:
        state.stages["requirements"].status = "complete"
        state.stages["requirements"].completed_at = datetime.now(timezone.utc).isoformat()
        state.stages["requirements"].artefact = REQUIREMENTS_PATH
        state.current_stage = "requirements"
        state.completed_stages.append("requirements")
        print(f"\n[requirements] ✓ Gate checks passed ({len(gate_checks)}/{len(gate_checks)})")
        print(f"\nReview {REQUIREMENTS_PATH} and spec artifacts, then run: /coding")
    else:
        print(f"\n[requirements] ✗ Gate checks failed")
        print("Retry with: /requirements")
        _cleanup_artefacts(profiles)
        state.stages["requirements"].status = "failed"
        state.current_stage = "requirements"

    return state


def _resolve_profiles(state: SDLCPersistedState, config: SDLCConfig,
                      conversation_context: str,
                      profiles_override: Optional[list[str]]):
    """Profile precedence: CLI override → context-file directive → state →
    classification recommendation → config default."""
    override = profiles_override
    if not override:
        override = _parse_context_profiles(conversation_context)
    _apply_context_toolchain(config, conversation_context)
    return get_profiles(state, config, override)


def _parse_context_profiles(conversation_context: str) -> Optional[list[str]]:
    if not conversation_context:
        return None
    match = SPEC_PROFILES_RE.search(conversation_context)
    if not match:
        return None
    names = [n.strip() for n in match.group(1).split(",") if n.strip()]
    if not names:
        return None
    error = validate_profile_names(names)
    if error:
        raise ValueError(f"Context file SPEC_PROFILES directive is invalid: {error}")
    return names


def _apply_context_toolchain(config: SDLCConfig, conversation_context: str):
    """SPEC_TOOLCHAIN: gherkin-bdd=behave; unit-tests=pytest — runner hints
    from the Q&A, applied in-memory unless the config already pins a runner."""
    if not conversation_context:
        return
    match = SPEC_TOOLCHAIN_RE.search(conversation_context)
    if not match:
        return
    for pair in match.group(1).split(";"):
        if "=" not in pair:
            continue
        profile_name, runner = (s.strip() for s in pair.split("=", 1))
        if not profile_name or not runner:
            continue
        existing = config.profiles.get(profile_name)
        if existing is None:
            config.profiles[profile_name] = ProfileConfig(runner=runner)
        elif not existing.runner:
            existing.runner = runner


def _cleanup_artefacts(profiles):
    if os.path.exists(REQUIREMENTS_PATH):
        os.remove(REQUIREMENTS_PATH)
    for profile in profiles:
        profile.cleanup_artifacts()
    print(f"[requirements] Removed incomplete artefacts from {REQUIREMENTS_DIR}/")


def _write_requirements_md(llm_content: str):
    match = REQUIREMENTS_MD_BLOCK.search(llm_content)
    if match:
        requirements_content = match.group(1).strip()
    else:
        # Fall back to everything before the first profile-specific block so a
        # formatting slip doesn't dump feature files into REQUIREMENTS.md.
        requirements_content = re.split(
            r'^---FEATURE_FILE:|^```(?:gherkin|test-cases-md|openapi-yaml)',
            llm_content, maxsplit=1, flags=re.MULTILINE,
        )[0].strip()
        if requirements_content.startswith("```"):
            requirements_content = requirements_content.split("\n", 1)[1] if "\n" in requirements_content else ""
        if requirements_content.endswith("```"):
            requirements_content = requirements_content[:-3].strip()
        if not requirements_content:
            requirements_content = llm_content

    with open(REQUIREMENTS_PATH, "w") as f:
        f.write(requirements_content)


def _ensure_required_sections(path: str):
    if not os.path.exists(path):
        return
    with open(path) as f:
        content = f.read()
    missing = [slot[0] for slot in SECTION_SLOTS
               if not any(alias in content for alias in slot)]
    if missing:
        with open(path, "a") as f:
            f.write("\n\n---\n\n")
            for section in missing:
                f.write(f"\n{section}\nTBD — see conversation context.\n\n")
        print(f"[requirements] ✗ Appended missing sections: {', '.join(missing)}")


def _check_requirements_schema() -> tuple[bool, str]:
    if not os.path.exists(REQUIREMENTS_PATH):
        return False, f"{REQUIREMENTS_PATH} does not exist"
    with open(REQUIREMENTS_PATH) as f:
        content = f.read()
    missing = [slot[0] for slot in SECTION_SLOTS
               if not any(alias in content for alias in slot)]
    if missing:
        sections_str = ", ".join(missing)
        return False, f"REQUIREMENTS.md is missing required section(s): {sections_str}"
    return True, "All required sections present"

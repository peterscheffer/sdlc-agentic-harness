from typing import Optional

STAGE_SECTIONS = {
    "planning": [
        "## Summary",
        "## Goals",
        "## Non-Goals",
        "## Tasks",
        "## Acceptance Criteria",
        "## Affected Files",
    ],
    "architecture": [
        "## Overview",
        "## Target Files",
        "## Design Decisions",
        "## PRINCIPLES Compliance",
        "## Risks",
    ],
    "ui-design": [
        "## Overview",
    ],
    "requirements": [
        "## Overview",
        "## Functional Requirements",
        "## Non-Functional Requirements",
        "## Behavioural Requirements",
    ],
    "review": [
        "## Change Summary",
        "## Recommendation",
    ],
    "coding": [],
    "testing": [],
    "pr": [],
}

OFF_SCRIPT_PREFIXES = [
    "Here are the complete",
    "Here's the complete",
    "Here is the complete implementation",
    "Here are the production-ready",
    "Here's the production-ready",
    "Below are the complete",
    "Below is the complete",
    "Below are all the files",
    "I have implemented",
    "I've implemented",
    "I have created the following files",
    "# File:",
]


def validate_stage_output(content: str, stage: str) -> tuple[bool, str]:
    if not content or not content.strip():
        return False, (
            f"LLM returned empty content for stage '{stage}'. "
            f"No artefacts were produced."
        )

    content_stripped = content.strip()

    if stage not in ("coding", "testing", "pr") and len(content_stripped) < 30:
        return False, (
            f"LLM response is too short ({len(content_stripped)} chars) "
            f"to be a valid {stage} specification. "
            f"The LLM likely failed to generate meaningful content."
        )

    for prefix in OFF_SCRIPT_PREFIXES:
        lower_content = content_stripped.lower()
        lower_prefix = prefix.lower()
        if lower_content.startswith(lower_prefix):
            return False, (
                f"LLM generated code files instead of a {stage} specification. "
                f"Response starts with: '{content_stripped[:120]}...'. "
                f"The LLM went off-script. Retry the stage."
            )

    required_sections = STAGE_SECTIONS.get(stage, [])
    if required_sections:
        found = any(s in content for s in required_sections)
        if not found:
            sections_str = ", ".join(required_sections)
            return False, (
                f"LLM response for stage '{stage}' does not contain any expected "
                f"section headings ({sections_str}). "
                f"The response appears off-topic. Retry the stage."
            )

    if stage == "ui-design":
        has_components = "## Components" in content
        has_screens = "## Screens" in content
        if not has_components and not has_screens:
            return False, (
                f"LLM response for stage 'ui-design' is missing both "
                f"'## Components' and '## Screens' sections. "
                f"At least one is required. Retry the stage."
            )

    return True, ""

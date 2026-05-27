import os
import re
from datetime import datetime, timezone

from utils.state import SDLCPersistedState
from utils.config import SDLCConfig
from utils.llm import call_llm

PRD_PATH = "sdlc/planning/PRD.md"
CODING_ARCH_PATH = "sdlc/architecture/ARCH.md"


def _get_stage_artefact_content(state: SDLCPersistedState, stage_id: str) -> str:
    stage_entry = state.stages.get(stage_id)
    if not stage_entry:
        return ""

    artefact_path = stage_entry.artefact
    if artefact_path and os.path.exists(artefact_path):
        with open(artefact_path) as f:
            return f.read()

    if stage_id == "coding":
        target_files = _parse_target_files(CODING_ARCH_PATH)
        existing = [f for f in target_files if os.path.exists(f)]
        if existing:
            lines = ["Generated / modified files during coding:"]
            for f in existing:
                try:
                    with open(f) as fh:
                        content = fh.read()
                    lines.append(f"\n### {f}\n```\n{content[:2000]}\n```")
                except Exception:
                    lines.append(f"\n- {f} (could not read)")
            return "\n".join(lines)

    return ""


def _parse_target_files(arch_path: str) -> list[str]:
    if not os.path.exists(arch_path):
        return []
    with open(arch_path) as f:
        content = f.read()
    files = []
    in_target = False
    for line in content.split("\n"):
        if line.startswith("## Target Files"):
            in_target = True
            continue
        if in_target and line.startswith("## "):
            break
        if in_target and "|" in line:
            parts = [p.strip() for p in line.split("|")]
            if len(parts) >= 3 and parts[1] and parts[1] not in ("File", "", "---") and not all(c == "-" for c in parts[1]):
                files.append(parts[1])
    return files


def _bump_prd_version(content: str) -> str:
    def _bump(match):
        major = match.group(1)
        minor = match.group(2)
        return f"| **Version** | {major}.{int(minor) + 1}.0-draft |"

    content = re.sub(
        r'\|\s*\*\*Version\*\*\s*\|\s*(\d+)\.(\d+)\.\d+-draft\s*\|',
        _bump,
        content,
    )

    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    content = re.sub(
        r'\|\s*\*\*Last Updated\*\*\s*\|\s*\S+\s*\|',
        f"| **Last Updated** | {today} |",
        content,
    )

    content = re.sub(
        r'\*End of document\.\s*Version\s*\[?[\w\.\-]+\]?\.?\*',
        f"*End of document. Version updated.*",
        content,
    )

    return content


def update_prd_if_needed(
    state: SDLCPersistedState,
    config: SDLCConfig,
    stage_id: str,
    conversation_context: str = "",
) -> bool:
    if not os.path.exists(PRD_PATH):
        return False

    with open(PRD_PATH) as f:
        current_prd = f.read()

    artefact_content = _get_stage_artefact_content(state, stage_id)

    if not artefact_content and not conversation_context:
        return False

    system_prompt = (
        "You are a product requirements document curator. "
        "Your job is to determine if new information from an SDLC stage "
        "should be incorporated into the PRD to keep it accurate and valuable."
    )

    parts = [
        "## Current PRD\n",
        current_prd,
        "\n\n## New Information from '" + stage_id + "' Stage\n",
        artefact_content or "(no artefacts produced)",
    ]
    if conversation_context:
        parts.extend([
            "\n\n## Conversation Context (discussion during this stage)\n",
            conversation_context,
        ])
    parts.extend([
        "\n\n## Instructions\n",
        "Review the current PRD against the new information above. ",
        "Determine if any of the new information adds valuable detail ",
        "that should be incorporated into the PRD. Consider:\n",
        "- New or refined requirements discovered during this stage\n",
        "- Architecture decisions, component breakdowns, or technical constraints\n",
        "- Data schemas, external integrations, or repository structure details\n",
        "- Changes to goals, non-goals, or scope\n",
        "- Clarifications to acceptance criteria or error handling\n\n",
        "If updating is valuable, produce the COMPLETE updated PRD document ",
        "with the new information integrated. Bump the minor version number.\n",
        "If no update is needed, respond with exactly: NO_UPDATE\n\n",
        "Your response MUST start with exactly one of:\n",
        "- 'UPDATE: yes' followed by the full updated PRD\n",
        "- 'NO_UPDATE' if the PRD does not need changes\n\n",
        "Do NOT include any text before the decision line.",
    ])
    user_prompt = "".join(parts)

    try:
        response = call_llm(
            prompt=user_prompt,
            stage=stage_id + "-prd-update",
            config=config,
            system_prompt=system_prompt,
            conversation_context=conversation_context,
        )
    except RuntimeError:
        print(f"[{stage_id}] PRD update check skipped (LLM error)")
        return False

    stripped = response.strip()
    if stripped.startswith("UPDATE: yes") or stripped.startswith("UPDATE:yes"):
        prd_content = stripped
        for prefix in ("UPDATE: yes", "UPDATE:yes"):
            if prd_content.startswith(prefix):
                prd_content = prd_content[len(prefix):].strip()
                break

        if prd_content:
            prd_content = _bump_prd_version(prd_content)
            with open(PRD_PATH, "w") as f:
                f.write(prd_content)
            print(f"[prd-update] PRD updated with insights from '{stage_id}' stage")
            return True

    return False

import os
import time
from datetime import datetime, timezone
from typing import Optional

from utils.config import SDLCConfig, get_stage_model

LOG_DIR = "sdlc/logs"
os.makedirs(LOG_DIR, exist_ok=True)


def _get_log_path(stage: str, iteration: Optional[int] = None) -> str:
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    if iteration is not None:
        return f"{LOG_DIR}/{stage}_iteration_{iteration}_{ts}.log"
    return f"{LOG_DIR}/{stage}_{ts}.log"


def call_llm(
    prompt: str,
    stage: str,
    config: SDLCConfig,
    system_prompt: Optional[str] = None,
    iteration: Optional[int] = None,
    conversation_context: str = "",
) -> str:
    log_path = _get_log_path(stage, iteration)
    model_name = get_stage_model(config, stage)

    effective_system_prompt = system_prompt or ""
    if conversation_context:
        context_block = (
            "\n\n### Prior Conversation Context\n"
            "The following is the conversation that took place in the OpenCode chat "
            "before this pipeline stage was invoked. Use it to understand the developer's "
            "intent, decisions, and requirements:\n\n"
            f"{conversation_context}"
        )
        effective_system_prompt += context_block

    log_entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "stage": stage,
        "model": model_name,
        "prompt_tokens": None,
        "completion_tokens": None,
        "system_prompt": effective_system_prompt,
        "prompt": prompt,
        "response": None,
        "iteration": iteration,
        "has_conversation_context": bool(conversation_context),
    }

    if effective_system_prompt:
        messages = [
            {"role": "system", "content": effective_system_prompt},
            {"role": "user", "content": prompt},
        ]
    else:
        messages = [
            {"role": "user", "content": prompt},
        ]

    use_mock = os.environ.get("SDLC_USE_MOCK_LLM", "").lower() in ("1", "true", "yes")

    if use_mock:
        content = _mock_llm_call(prompt, stage, iteration)
        log_entry["response"] = content
        log_entry["model"] = f"{model_name} (mock)"
        log_entry["mock_reason"] = "SDLC_USE_MOCK_LLM env var set"
        _write_log(log_path, log_entry)
        _redact_log(log_path)
        return content

    last_error = ""
    for attempt in range(3):
        try:
            from langchain_openai import ChatOpenAI

            llm = ChatOpenAI(
                model=model_name,
                temperature=0.3,
                timeout=config.timeouts.llm_call_seconds,
            )
            result = llm.invoke(messages)
            content = result.content
            log_entry["response"] = content
            if hasattr(result, "usage_metadata"):
                log_entry["prompt_tokens"] = result.usage_metadata.get("input_tokens")
                log_entry["completion_tokens"] = result.usage_metadata.get("output_tokens")
            _write_log(log_path, log_entry)
            _redact_log(log_path)
            return content

        except ImportError:
            raise RuntimeError(
                "langchain_openai is not installed. "
                "Install it with: pip install langchain-openai"
            )

        except Exception as e:
            err_msg = str(e)
            if "api_key" in err_msg.lower() or "apikey" in err_msg.lower() or "credentials" in err_msg.lower():
                base = os.environ.get("OPENAI_API_BASE", "http://localhost:11434/v1")
                raise RuntimeError(
                    f"AI model unavailable — check that Ollama is running at {base} "
                    f"and OPENAI_API_BASE / OPENAI_API_KEY are set correctly. "
                    f"Error: {err_msg[:200]}"
                )

            last_error = err_msg
            log_entry.setdefault("retries", []).append({
                "attempt": attempt + 1,
                "error": err_msg,
            })

            if attempt < 2:
                delay = 2 ** attempt
                time.sleep(delay)

    log_entry["error"] = f"LLM call failed after 3 retries. Last error: {last_error}"
    _write_log(log_path, log_entry)
    _redact_log(log_path)
    raise RuntimeError(
        f"LLM call failed for stage '{stage}' after 3 retries. "
        f"Last error: {last_error}"
    )


def _write_log(path: str, entry: dict):
    import json
    with open(path, "w") as f:
        json.dump(entry, f, indent=2)


def _redact_log(path: str):
    with open(path) as f:
        content = f.read()
    import re
    patterns = [
        r'(?i)(api[-_]?key|apikey|secret|token|password|auth)[=:]\s*\S+',
        r'(?i)(authorization|bearer)\s+\S+',
        r'(?i)(sk-[a-zA-Z0-9]{20,})',
    ]
    for pattern in patterns:
        content = re.sub(pattern, r'\1: [REDACTED]', content)
    with open(path, "w") as f:
        f.write(content)


def _mock_llm_call(prompt: str, stage: str, iteration: Optional[int] = None) -> str:
    if stage == "planning":
        return _generate_mock_prd(prompt)
    elif stage == "ui-design":
        return _generate_mock_design()
    elif stage == "architecture":
        return _generate_mock_arch(prompt)
    elif stage == "coding":
        return _generate_mock_code(prompt, iteration)
    elif stage == "review":
        return _generate_mock_review()
    elif stage == "pr":
        return "# PR body placeholder\n\nSummary of changes here."
    return f"# Mock output for stage: {stage}\n\n{prompt}"


def _generate_mock_prd(intent: str) -> str:
    lines = []
    lines.append("# Product Requirements Document\n")
    lines.append("## Summary")
    lines.append(f"Implement feature for: {intent[:100]}")
    lines.append("")
    lines.append("## Goals")
    lines.append("- Deliver the requested feature")
    lines.append("- Maintain existing functionality")
    lines.append("")
    lines.append("## Non-Goals")
    lines.append("- Performance optimization beyond requirements")
    lines.append("")
    lines.append("## Tasks")
    lines.append("- [ ] Design and implement the feature")
    lines.append("- [ ] Write tests")
    lines.append("- [ ] Update documentation")
    lines.append("")
    lines.append("## Acceptance Criteria")
    lines.append("- Feature works as described")
    lines.append("- All tests pass")
    lines.append("")
    lines.append("## Affected Files")
    lines.append("TBD \u2014 to be determined at architecture stage")
    return "\n".join(lines)


def _generate_mock_design() -> str:
    return """# UI Design Specification

## Overview
UI changes for a new component.

## Components
### MainComponent
- **Purpose**: Primary UI element
- **States**: loading, empty, error, success

## States
- **Loading**: Skeleton placeholder
- **Empty**: Friendly message
- **Error**: Error boundary
- **Success**: Normal display
"""


def _generate_mock_arch(intent: str) -> str:
    return f"""# Architecture Decision Record

## Overview
Architecture for the requested feature.

## Target Files
| File | Action | Description |
|------|--------|-------------|
| src/feature.py | CREATE | New feature module |

## Design Decisions
1. Modular design
2. Existing patterns followed

## PRINCIPLES Compliance
No PRINCIPLES.md found. Compliance checks skipped.

## Risks
None identified.
"""


def _generate_mock_code(prompt: str, iteration: Optional[int] = None) -> str:
    if iteration and iteration > 1:
        return (
            "# Fixed code after iteration feedback\n"
            "def hello():\n"
            '    return "Hello, World!"\n'
        )
    return (
        "# Generated code\n"
        "def hello():\n"
        '    return "Hello, World!"\n'
    )


def _generate_mock_review() -> str:
    return """## Change Summary
Files modified: src/feature.py (+10, -2)
Changes implement the requested feature.

## PRD Alignment
- [x] Task 1: Feature implemented
- [x] Task 2: Tests written
- [x] Acceptance criteria met

## PRINCIPLES Compliance
No violations found.

## Test Evidence
All tests passing. Coverage: 85%

## Recommendation
recommendation: PASS

## Notes
None
"""

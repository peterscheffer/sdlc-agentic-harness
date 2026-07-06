import os
import re
from datetime import datetime, timezone
from typing import Optional

from utils.state import SDLCPersistedState
from utils.config import SDLCConfig, get_max_iterations
from utils.llm import call_llm
from utils.output_validator import validate_stage_output
from gates.gate_runner import (
    GateCheck, run_gate_checks,
    check_file_exists, check_command_exits_ok,
)
from profiles import get_profiles


SEPARATOR_ROW_RE = re.compile(r'^[-:\s]+$')


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
            if len(parts) >= 3 and parts[1]:
                # Real LLM output commonly wraps table cells in backticks
                # (`app/main.py`) and uses variable-length dash separator
                # rows (|-------|--------|); both must be stripped/rejected
                # or every subsequent target-file match fails.
                candidate = parts[1].strip("`").strip()
                if candidate and candidate != "File" and not SEPARATOR_ROW_RE.match(candidate):
                    files.append(candidate)
    return files


def execute_coding(state: SDLCPersistedState, config: SDLCConfig, conversation_context: str = "") -> SDLCPersistedState:
    max_iter = get_max_iterations(config, "coding")
    last_failure_reason = None
    iteration_log = []

    print(f"\n[coding] Coding Loop started (max {max_iter} iterations)...")

    arch_path = "sdlc/architecture/ARCH.md"
    target_files = _parse_target_files(arch_path)

    arch_content = ""
    if os.path.exists(arch_path):
        with open(arch_path) as f:
            arch_content = f.read()

    state.stages["coding"].status = "in_progress"
    state.current_stage = "coding"

    try:
        spec_profiles = get_profiles(state, config)
    except ValueError as e:
        print(f"[coding] ✗ {e}")
        state.stages["coding"].status = "failed"
        state.stages["coding"].reason = str(e)
        return state

    # Fail before burning LLM iterations if any verifier can't run at all.
    for profile in spec_profiles:
        ok, message = profile.preflight()
        if not ok:
            print(f"[coding] ✗ {profile.display_name} preflight failed: {message}")
            state.stages["coding"].status = "failed"
            state.stages["coding"].reason = f"{profile.name} preflight failed: {message}"
            return state

    # Step definitions / test skeletons are first-class generation targets.
    for profile in spec_profiles:
        for scaffold in profile.coding_scaffold_targets(target_files):
            if scaffold not in target_files:
                target_files.append(scaffold)

    for iteration in range(1, max_iter + 1):
        print(f"\n[coding] Iteration {iteration} of {max_iter}...")

        context_parts = []
        context_parts.append(f"Architecture:\n{arch_content}")
        context_parts.append(f"Target files: {', '.join(target_files) if target_files else 'TBD'}")

        req_content = ""
        if os.path.exists("sdlc/requirements/REQUIREMENTS.md"):
            with open("sdlc/requirements/REQUIREMENTS.md") as f:
                req_content = f.read()
        if req_content:
            context_parts.append(f"Requirements:\n{req_content}")

        for profile in spec_profiles:
            spec_context = profile.coding_context()
            if spec_context:
                context_parts.append(spec_context)

        file_states = {}
        for tf in target_files:
            if os.path.exists(tf):
                with open(tf) as f:
                    file_states[tf] = f.read()
                    context_parts.append(f"Current state of {tf}:\n{file_states[tf]}")
            else:
                context_parts.append(f"{tf} does not exist yet (will be created)")

        if last_failure_reason:
            context_parts.append(
                f"Previous iteration failed. Fix this error and retry:\n"
                f"{last_failure_reason}\n\n"
                f"Current state of target files is provided above. "
                f"Regenerate to fix this specific error."
            )

        prompt = "\n\n".join(context_parts)

        system_prompt = (
            "You are a code generator. Generate or modify only the target files listed. "
            "For EACH file, output a line starting with `### ` followed by the EXACT target "
            "file path as listed (no backticks, no extra text on that line), then a fenced "
            "code block with that file's complete contents. Example:\n"
            "### app/main.py\n"
            "```python\n"
            "...\n"
            "```\n"
            "Do not combine multiple files into one code block, and do not add commentary "
            "or explanation outside the file blocks.\n"
            "IMPORTANT: The conversation context (below) contains the LATEST decisions "
            "and takes PRECEDENCE over any conflicting information in the PRD, architecture, "
            "or other artefacts."
        )
        profile_instructions = [p.coding_prompt_fragment() for p in spec_profiles
                                if p.coding_prompt_fragment()]
        if profile_instructions:
            system_prompt += "\n\nSpec verification requirements:\n- " + \
                "\n- ".join(profile_instructions)

        try:
            content = call_llm(
                prompt=prompt,
                stage="coding",
                config=config,
                system_prompt=system_prompt,
                iteration=iteration,
                conversation_context=conversation_context if iteration == 1 else "",
                pipeline_id=state.pipeline_id,
            )
        except RuntimeError as e:
            print(f"[coding] \u2717 LLM call failed: {e}")
            print("The stage produced no artefacts. Retry with: /coding")
            state.stages["coding"].status = "failed"
            state.stages["coding"].reason = str(e)
            state.stages["coding"].iterations = iteration
            _write_iterations_log(state, iteration_log)
            return state

        valid, reason = validate_stage_output(content, "coding")
        if not valid:
            print(f"[coding] \u2717 {reason}")
            state.stages["coding"].status = "failed"
            state.stages["coding"].reason = reason
            state.stages["coding"].iterations = iteration
            _write_iterations_log(state, iteration_log)
            return state

        _write_generated_files(target_files, content)

        generated = [tf for tf in target_files if os.path.exists(tf)]
        print(f"[coding] - Generated: {', '.join(generated) if generated else 'no files specified'}")

        gate_checks = []
        if config.commands.lint:
            gate_checks.append(
                GateCheck("linter_passed", "Linter command passes",
                          lambda c=config: check_command_exits_ok(
                              c.commands.lint, c.timeouts.command_seconds))
            )
        else:
            gate_checks.append(
                GateCheck("linter_passed", "Linter check (not configured)",
                          lambda: (True, "Linter not configured \u2014 skipped"))
            )

        if config.commands.build:
            gate_checks.append(
                GateCheck("build_passed", "Build command passes",
                          lambda c=config: check_command_exits_ok(
                              c.commands.build, c.timeouts.command_seconds))
            )
        else:
            gate_checks.append(
                GateCheck("build_passed", "Build check (not configured)",
                          lambda: (True, "Build not configured \u2014 skipped"))
            )

        gate_checks.append(
            GateCheck("target_files_exist", "Target files exist",
                      lambda fl=target_files: _check_target_files(fl))
        )

        # Spec verifiers run inside the iteration loop so runner failures
        # (unbound steps, failing assertions, contract mismatches) feed back
        # into the next iteration's prompt.
        for profile in spec_profiles:
            gate_checks.extend(profile.verification_gate_checks())

        passed, messages = run_gate_checks("coding", gate_checks, state)

        for msg in messages:
            print(msg)

        gate_results = state.stages["coding"].gate_results
        failed_details = [m.strip() for m in messages if "✗" in m]
        failure_reason = "\n".join(failed_details) if failed_details else None

        iteration_log.append({
            "iteration": iteration,
            "gates": {check.name: getattr(gate_results, check.name, None)
                      for check in gate_checks},
            "failure_reason": failure_reason,
        })

        if passed:
            state.stages["coding"].status = "complete"
            state.stages["coding"].completed_at = datetime.now(timezone.utc).isoformat()
            state.stages["coding"].iterations = iteration
            state.current_stage = "coding"
            if "coding" not in state.completed_stages:
                state.completed_stages.append("coding")
            # Write the iteration log on success too \u2014 otherwise a passing run
            # leaves behind a stale ITERATIONS.md from a prior failed attempt.
            _write_iterations_log(state, iteration_log)
            print(f"\n[coding] \u2713 Coding stage passed in {iteration} iteration(s).")
            return state

        last_failure_reason = failure_reason
        print(f"[coding] - Iteration {iteration} failed: {failure_reason}")
        if iteration < max_iter:
            print(f"[coding] - Retrying with fresh context (iteration {iteration + 1})...")
        else:
            print(f"[coding] - Maximum iterations ({max_iter}) reached. Cleaning up generated files...")

    state.stages["coding"].status = "failed"
    state.stages["coding"].iterations = max_iter
    state.stages["coding"].reason = (
        f"Maximum iterations ({max_iter}) reached without passing gate checks."
    )
    state.stages["coding"].artefact = "sdlc/coding/ITERATIONS.md"
    state.current_stage = "coding"

    _write_iterations_log(state, iteration_log)

    for tf in target_files:
        if os.path.exists(tf):
            os.remove(tf)
            print(f"[coding] Removed incomplete file: {tf}")

    print(f"\n[coding] \u2717 Coding stage failed after {max_iter} iterations.")
    if last_failure_reason:
        print(f"[coding] Last failure: {last_failure_reason}")
    print(f"No artefacts were left on disk.")
    print(f"Fix the issue manually or refine the PRD and retry: /coding")

    return state


FENCED_BLOCK_RE = re.compile(r'```[^\n]*\n(.*?)```', re.DOTALL)


def _write_file(filepath: str, content: str):
    os.makedirs(os.path.dirname(filepath) or ".", exist_ok=True)
    with open(filepath, "w") as f:
        f.write(content)


def _strip_fence(code: str) -> str:
    """Strip a leading opening ``` fence marker (with optional language tag)
    and truncate at the first subsequent line that is exactly a closing ```
    if the header-matched content happens to include one — a header line
    followed by a fenced block is common real-model output that the header
    regex alone doesn't unwrap. The closing fence is found by scanning
    (not assumed to be the last line): some models append trailing
    narration after the closing ``` (e.g. "*(Note: ...)*"), which must be
    discarded along with the marker rather than kept as file content."""
    lines = code.split("\n")
    if lines and lines[0].strip().startswith("```"):
        lines = lines[1:]
    for i, line in enumerate(lines):
        if line.strip() == "```":
            lines = lines[:i]
            break
    return "\n".join(lines).strip()


def _write_generated_files(target_files: list[str], llm_content: str):
    # Only treat a literal "### " markdown heading as a file delimiter — a
    # bare "word.word" fallback (no ### prefix) used to also count as a
    # boundary, but that pattern matches ordinary code too (attribute access,
    # method calls like "app.include_router(...)", decimals like "3.14"),
    # truncating a file's captured content the instant such code appeared.
    # Headerless models are handled separately by the order-based fallback
    # below, which only engages when NO "### " headers matched at all.
    file_pattern = re.compile(
        r'^###\s+`?([\w/\\\-\.]+\.\w+)`?\s*\n(.*?)(?=\n###\s|\Z)',
        re.DOTALL | re.MULTILINE
    )
    written = set()
    for match in file_pattern.finditer(llm_content):
        filepath = match.group(1).strip().strip("`")
        code = _strip_fence(match.group(2).strip())
        if filepath in target_files:
            _write_file(filepath, code)
            written.add(filepath)

    remaining = [tf for tf in target_files if tf not in written]
    if remaining and not written:
        # Some models (no explicit "### filename" headers) emit one fenced
        # code block per target file, in the same order as the target list.
        # Only trust this order-based mapping when NOTHING matched via
        # headers and the counts line up exactly.
        fenced_blocks = [m.group(1).strip() for m in FENCED_BLOCK_RE.finditer(llm_content)]
        if len(fenced_blocks) == len(remaining):
            for filepath, code in zip(remaining, fenced_blocks):
                _write_file(filepath, code)
                written.add(filepath)
        elif len(remaining) == 1:
            # Unambiguous: with a single target file there's nowhere else the
            # content could belong. But it may still be wrapped in its own
            # fence plus narration text, so extract the first (possibly
            # unclosed) fenced block rather than writing markers verbatim.
            single_fence = FENCED_BLOCK_RE.search(llm_content)
            content = single_fence.group(1).strip() if single_fence else _strip_fence(llm_content.strip())
            _write_file(remaining[0], content)
            written.add(remaining[0])
        # Otherwise: leave the remaining files missing so target_files_exist
        # reports them cleanly, rather than corrupting every one of them with
        # a duplicate copy of the same unparsed response.


def _check_target_files(file_list: list[str]) -> tuple[bool, str]:
    if not file_list:
        return True, "No target files specified in ARCH.md"
    missing = [f for f in file_list if not os.path.exists(f)]
    if not missing:
        return True, f"All {len(file_list)} target files exist"
    return False, f"Missing files: {', '.join(missing)}"


def _write_iterations_log(state: SDLCPersistedState, log: list[dict]):
    os.makedirs("sdlc/coding", exist_ok=True)
    path = "sdlc/coding/ITERATIONS.md"
    lines = []
    lines.append("# Coding Iteration Log\n")
    lines.append(f"**Pipeline ID:** {state.pipeline_id}")
    lines.append(f"**Max Iterations:** {state.stages['coding'].iterations or 'N/A'}")
    lines.append(f"**Result:** {state.stages['coding'].status}")
    lines.append("")
    gate_names = []
    for entry in log:
        for name in entry.get("gates", {}):
            if name not in gate_names:
                gate_names.append(name)

    header_cells = ["Iteration"] + gate_names + ["Failure Reason"]
    lines.append("| " + " | ".join(header_cells) + " |")
    lines.append("|" + "|".join(["---"] * len(header_cells)) + "|")
    for entry in log:
        cells = [str(entry["iteration"])]
        for name in gate_names:
            value = entry.get("gates", {}).get(name)
            cells.append("\u2713" if value else "\u2717" if value is False else "-")
        reason = (entry["failure_reason"] or "-").replace("\n", " / ").replace("|", "\\|")
        if len(reason) > 300:
            reason = reason[:300] + "\u2026"
        cells.append(reason)
        lines.append("| " + " | ".join(cells) + " |")
    lines.append("")
    lines.append(f"*Log generated at {datetime.now(timezone.utc).isoformat()}*")

    with open(path, "w") as f:
        f.write("\n".join(lines) + "\n")

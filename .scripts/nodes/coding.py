import os
import re
from datetime import datetime, timezone
from typing import Optional

from utils.state import SDLCPersistedState
from utils.config import SDLCConfig, get_max_iterations
from utils.llm import call_llm
from gates.gate_runner import (
    GateCheck, run_gate_checks,
    check_file_exists, check_command_exits_ok,
)


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
            if len(parts) >= 3 and parts[1] and parts[1] not in ("File", "", "---"):
                files.append(parts[1])
    return files


def execute_coding(state: SDLCPersistedState, config: SDLCConfig, conversation_context: str = "") -> SDLCPersistedState:
    max_iter = get_max_iterations(config, "coding")
    last_failure_reason = None
    iteration_log = []

    print(f"\n[coding] Ralph Loop started (max {max_iter} iterations)...")

    arch_path = "sdlc/architecture/ARCH.md"
    target_files = _parse_target_files(arch_path)

    arch_content = ""
    if os.path.exists(arch_path):
        with open(arch_path) as f:
            arch_content = f.read()

    state.stages["coding"].status = "in_progress"
    state.current_stage = "coding"

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

        import glob
        feature_files = sorted(glob.glob("sdlc/requirements/*.feature"))
        if feature_files:
            gherkin_parts = []
            for ff in feature_files:
                with open(ff) as f:
                    gherkin_parts.append(f"--- {os.path.basename(ff)} ---\n{f.read()}")
            context_parts.append("Gherkin Specs:\n" + "\n".join(gherkin_parts))

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
            "Output the complete file contents for each file, clearly delimited.\n"
            "IMPORTANT: The conversation context (below) contains the LATEST decisions "
            "and takes PRECEDENCE over any conflicting information in the PRD, architecture, "
            "or other artefacts."
        )

        try:
            content = call_llm(
                prompt=prompt,
                stage="coding",
                config=config,
                system_prompt=system_prompt,
                iteration=iteration,
                conversation_context=conversation_context if iteration == 1 else "",
            )
        except RuntimeError as e:
            print(f"[coding] \u2717 LLM call failed: {e}")
            print("The stage produced no artefacts. Retry with: /coding")
            state.stages["coding"].status = "failed"
            state.stages["coding"].reason = str(e)
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

        passed, messages = run_gate_checks("coding", gate_checks, state)

        for msg in messages:
            print(msg)

        failure_reason = None
        for check in gate_checks:
            if not getattr(state.stages["coding"].gate_results, check.name, True):
                failure_reason = f"{check.description} failed"

        iteration_log.append({
            "iteration": iteration,
            "linter": state.stages["coding"].gate_results.linter_passed,
            "build": state.stages["coding"].gate_results.build_passed,
            "files_exist": state.stages["coding"].gate_results.target_files_exist,
            "failure_reason": failure_reason,
        })

        if passed:
            state.stages["coding"].status = "complete"
            state.stages["coding"].completed_at = datetime.now(timezone.utc).isoformat()
            state.stages["coding"].iterations = iteration
            state.current_stage = "coding"
            if "coding" not in state.completed_stages:
                state.completed_stages.append("coding")
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


def _write_generated_files(target_files: list[str], llm_content: str):
    file_pattern = re.compile(
        r'(?:^###\s+)?(?:`?)([\w/\\\-\.]+\.\w+)(?:`?)\s*\n(.*?)(?=\n(?:###|`?\w+\.\w+)|\Z)',
        re.DOTALL | re.MULTILINE
    )
    written = set()
    for match in file_pattern.finditer(llm_content):
        filepath = match.group(1).strip()
        code = match.group(2).strip()
        if filepath in target_files:
            os.makedirs(os.path.dirname(filepath) or ".", exist_ok=True)
            with open(filepath, "w") as f:
                f.write(code)
            written.add(filepath)

    for tf in target_files:
        if tf not in written:
            os.makedirs(os.path.dirname(tf) or ".", exist_ok=True)
            with open(tf, "w") as f:
                f.write(llm_content)


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
    lines.append("| Iteration | Linter | Build | Files Exist | Failure Reason |")
    lines.append("|-----------|--------|-------|-------------|----------------|")
    for entry in log:
        linter_str = "\u2713" if entry["linter"] else "\u2717" if entry["linter"] is False else "-"
        build_str = "\u2713" if entry["build"] else "\u2717" if entry["build"] is False else "-"
        files_str = "\u2713" if entry["files_exist"] else "\u2717" if entry["files_exist"] is False else "-"
        reason = entry["failure_reason"] or "-"
        lines.append(f"| {entry['iteration']} | {linter_str} | {build_str} | {files_str} | {reason} |")
    lines.append("")
    lines.append(f"*Log generated at {datetime.now(timezone.utc).isoformat()}*")

    with open(path, "w") as f:
        f.write("\n".join(lines) + "\n")

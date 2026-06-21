import glob
import os
import subprocess
import re
from datetime import datetime, timezone
from typing import Optional

from utils.state import SDLCPersistedState
from utils.config import SDLCConfig
from utils.llm import call_llm
from gates.gate_runner import (
    GateCheck, run_gate_checks,
    check_file_exists, check_file_not_empty,
)

TEST_REPORT_PATH = "sdlc/testing/TEST_REPORT.md"


def execute_testing(state: SDLCPersistedState, config: SDLCConfig) -> SDLCPersistedState:
    print("\n[testing] Executing test suite...")

    os.makedirs("sdlc/testing", exist_ok=True)

    test_command = config.commands.test
    if not test_command:
        print("[testing] \u2717 Error: Test command not configured in sdlc.config.json.")
        print("  Add: commands.test: \"<your_test_command>\"")
        state.stages["testing"].status = "failed"
        state.current_stage = "testing"
        return state

    exit_code = -1
    stdout = ""
    stderr = ""
    timed_out = False

    try:
        result = subprocess.run(
            test_command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=config.timeouts.command_seconds,
        )
        exit_code = result.returncode
        stdout = result.stdout
        stderr = result.stderr
    except subprocess.TimeoutExpired:
        timed_out = True
        exit_code = -1
        print(f"[testing] \u2717 Test command timed out after {config.timeouts.command_seconds} seconds.")
    except Exception as e:
        stderr = str(e)
        print(f"[testing] \u2717 Test command failed to execute: {e}")

    test_passed = exit_code == 0

    pass_count, fail_count, skip_count = _parse_test_counts(stdout + stderr)
    coverage_percent = None
    if config.coverage.enabled:
        coverage_percent = _parse_coverage(stdout + stderr, config)

    _write_test_report(
        test_command=test_command,
        exit_code=exit_code,
        timed_out=timed_out,
        test_passed=test_passed,
        pass_count=pass_count,
        fail_count=fail_count,
        skip_count=skip_count,
        coverage_percent=coverage_percent,
        stdout=stdout,
        stderr=stderr,
        coverage_enabled=config.coverage.enabled,
        min_coverage=config.coverage.min_percentage,
    )

    state.stages["testing"].coverage_percent = coverage_percent

    if not test_passed:
        print(f"\n[testing] \u2717 Tests failed: test command exited with code {exit_code}")
        if fail_count is not None:
            print(f"[testing]   {fail_count} failure(s) detected")
        print(f"[testing] See {TEST_REPORT_PATH} for error details.")
        state.stages["testing"].status = "failed"
        state.current_stage = "testing"
        return state

    if config.coverage.enabled and coverage_percent is not None and not coverage_met:
        print(f"\n[testing] \u2717 Coverage {coverage_percent:.0f}% is below minimum {config.coverage.min_percentage}%.")
        print(f"[testing] Write additional tests and retry: /testing")
        state.stages["testing"].status = "failed"
        state.current_stage = "testing"
        return state

    gherkin_compliance_passed, gherkin_message = _check_gherkin_compliance(config)
    _append_gherkin_compliance_to_report(gherkin_compliance_passed, gherkin_message)

    gate_checks_list = [
        GateCheck("tests_passed", "Tests pass",
                  lambda: (test_passed, f"Test exited with code {exit_code}")),
        GateCheck("test_report_exists", "TEST_REPORT.md exists",
                  lambda: check_file_exists(TEST_REPORT_PATH)),
        GateCheck("report_not_empty", "TEST_REPORT.md not empty",
                  lambda: check_file_not_empty(TEST_REPORT_PATH)),
        GateCheck("gherkin_compliance", "Gherkin scenarios implemented",
                  lambda: (gherkin_compliance_passed, gherkin_message)),
    ]

    if config.coverage.enabled:
        gate_checks_list.append(
            GateCheck("coverage_threshold_met", "Coverage meets minimum",
                      lambda: _check_coverage(coverage_percent, config))
        )

    passed, messages = run_gate_checks("testing", gate_checks_list, state)

    for msg in messages:
        print(msg)

    if not gherkin_compliance_passed:
        print(f"\n[testing] \u2717 Gherkin compliance check failed: {gherkin_message}")
        state.stages["testing"].status = "failed"
        state.current_stage = "testing"
        return state

    if passed:
        state.stages["testing"].status = "complete"
        state.stages["testing"].completed_at = datetime.now(timezone.utc).isoformat()
        state.stages["testing"].artefact = TEST_REPORT_PATH
        state.current_stage = "testing"
        if "testing" not in state.completed_stages:
            state.completed_stages.append("testing")

        total_checks = len(gate_checks_list)
        pass_summary = f"{pass_count} passed, {fail_count} failed" if pass_count is not None else ""
        cov_summary = ""
        if config.coverage.enabled and coverage_percent is not None:
            cov_summary = f"\n[testing] \u2713 Coverage: {coverage_percent:.0f}% (exceeds {config.coverage.min_percentage}% minimum)"

        print(f"\n[testing] \u2713 Tests executed: {pass_summary}")
        if cov_summary:
            print(cov_summary)
        print(f"[testing] \u2713 Gate checks passed ({total_checks}/{total_checks})")
        print(f"See {TEST_REPORT_PATH} for details.")
        print(f"To review the changes, run: /review")
    else:
        print(f"\n[testing] \u2717 Gate checks failed")
        state.stages["testing"].status = "failed"
        state.current_stage = "testing"

    return state


def _parse_test_counts(output: str) -> tuple:
    pass_count = None
    fail_count = None
    skip_count = None

    passed = re.findall(r'(\d+)\s+passed', output, re.IGNORECASE)
    failed = re.findall(r'(\d+)\s+failed', output, re.IGNORECASE)
    skipped = re.findall(r'(\d+)\s+skipped', output, re.IGNORECASE)

    if passed:
        pass_count = sum(int(x) for x in passed)
    if failed:
        fail_count = sum(int(x) for x in failed)
    if skipped:
        skip_count = sum(int(x) for x in skipped)

    return pass_count, fail_count, skip_count


def _parse_coverage(output: str, config: SDLCConfig) -> Optional[float]:
    cov_report = config.commands.coverage_report
    if cov_report and os.path.exists(cov_report):
        import json
        try:
            with open(cov_report) as f:
                data = json.load(f)
            totals = data.get("totals", {})
            return totals.get("percent_covered")
        except (json.JSONDecodeError, KeyError, AttributeError):
            pass

    patterns = [
        r'coverage:\s*(\d+(?:\.\d+)?)%',
        r'Total coverage:\s*(\d+(?:\.\d+)?)%',
        r'Lines:\s*(\d+(?:\.\d+))%\s*',
    ]
    for pattern in patterns:
        match = re.search(pattern, output, re.IGNORECASE)
        if match:
            return float(match.group(1))
    return None


def _check_coverage(coverage_percent: Optional[float], config: SDLCConfig) -> tuple[bool, str]:
    if coverage_percent is None:
        return False, "Coverage data could not be parsed from test output"
    min_cov = config.coverage.min_percentage
    if coverage_percent >= min_cov:
        return True, f"Coverage {coverage_percent:.0f}% meets minimum {min_cov}%"
    return False, f"Coverage {coverage_percent:.0f}% is below minimum {min_cov}%"


def _write_test_report(
    test_command: str,
    exit_code: int,
    timed_out: bool,
    test_passed: bool,
    pass_count=None,
    fail_count=None,
    skip_count=None,
    coverage_percent=None,
    stdout="",
    stderr="",
    coverage_enabled=False,
    min_coverage=80,
):
    lines = []
    lines.append("# Test Report\n")
    lines.append(f"**Generated:** {datetime.now(timezone.utc).isoformat()}")
    lines.append(f"**Command:** `{test_command}`")
    lines.append(f"**Exit Code:** {exit_code}")
    lines.append(f"**Status:** {'PASSED' if test_passed else 'TIMEOUT' if timed_out else 'FAILED'}")
    lines.append("")

    if pass_count is not None:
        lines.append(f"**Tests Passed:** {pass_count}")
    if fail_count is not None:
        lines.append(f"**Tests Failed:** {fail_count}")
    if skip_count is not None:
        lines.append(f"**Tests Skipped:** {skip_count}")
    lines.append("")

    if coverage_enabled:
        if coverage_percent is not None:
            met = coverage_percent >= min_coverage
            lines.append(f"**Coverage:** {coverage_percent:.0f}% {'\u2713' if met else '\u2717'}")
            lines.append(f"**Minimum:** {min_coverage}%")
        else:
            lines.append("**Coverage:** Could not parse from output")
    else:
        lines.append("**Coverage validation:** Disabled")
    lines.append("")

    if stdout:
        lines.append("## Stdout (last 500 chars)")
        lines.append(f"```\n{stdout[-500:]}\n```\n")
    if stderr:
        lines.append("## Stderr (last 500 chars)")
        lines.append(f"```\n{stderr[-500:]}\n```\n")

    os.makedirs("sdlc/testing", exist_ok=True)
    with open(TEST_REPORT_PATH, "w") as f:
        f.write("\n".join(lines) + "\n")


def _check_gherkin_compliance(config: SDLCConfig) -> tuple[bool, str]:
    feature_files = sorted(glob.glob("sdlc/requirements/*.feature"))
    if not feature_files:
        return True, "No Gherkin feature files found — compliance check skipped"

    if not os.path.exists("sdlc/architecture/ARCH.md"):
        return True, "ARCH.md not found — compliance check skipped"

    with open("sdlc/architecture/ARCH.md") as f:
        arch_content = f.read()

    gherkin_specs = []
    for ff in feature_files:
        with open(ff) as f:
            gherkin_specs.append(f"--- {os.path.basename(ff)} ---\n{f.read()}")

    source_files = []
    in_target = False
    for line in arch_content.split("\n"):
        if line.startswith("## Target Files"):
            in_target = True
            continue
        if in_target and line.startswith("## "):
            break
        if in_target and "|" in line:
            parts = [p.strip() for p in line.split("|")]
            if len(parts) >= 3 and parts[1] and parts[1] not in ("File", "", "---") and not all(c == "-" for c in parts[1]):
                tf = parts[1]
                if os.path.exists(tf):
                    with open(tf) as f:
                        source_files.append(f"--- {tf} ---\n{f.read()}")
                else:
                    gherkin_specs.append(f"--- {tf} ---\n(not yet created)")

    prompt_parts = [
        "## Gherkin Specifications\n",
        "\n".join(gherkin_specs),
        "\n\n## Source Code\n",
        "\n".join(source_files) if source_files else "(no source files found)",
        "\n\n## Instructions\n",
        "Review the Gherkin feature files and the source code implementation. ",
        "Determine if ALL the Gherkin scenarios are adequately addressed in the code. ",
        "Respond with exactly one of:\n",
        "- 'GHERKIN_COMPLIANCE: pass' if all scenarios are implemented\n",
        "- 'GHERKIN_COMPLIANCE: fail' with a brief explanation of what is missing",
    ]
    user_prompt = "".join(prompt_parts)

    system_prompt = (
        "You are a quality assurance engineer. "
        "Verify that the implemented source code satisfies all Gherkin scenarios."
    )

    try:
        response = call_llm(
            prompt=user_prompt,
            stage="gherkin-compliance",
            config=config,
            system_prompt=system_prompt,
        )
    except RuntimeError as e:
        return False, f"LLM compliance check failed: {e}"

    stripped = response.strip()
    if stripped.startswith("GHERKIN_COMPLIANCE: pass"):
        return True, "All Gherkin scenarios are implemented"
    elif stripped.startswith("GHERKIN_COMPLIANCE: fail"):
        detail = stripped[len("GHERKIN_COMPLIANCE: fail"):].strip()
        return False, detail or "Gherkin compliance check failed"
    return False, f"Unexpected compliance response: {stripped[:200]}"


def _append_gherkin_compliance_to_report(passed: bool, message: str):
    if not os.path.exists(TEST_REPORT_PATH):
        return
    with open(TEST_REPORT_PATH, "a") as f:
        f.write("\n## Gherkin Compliance\n")
        icon = "\u2713" if passed else "\u2717"
        f.write(f"**Status:** {icon} {'PASSED' if passed else 'FAILED'}\n")
        f.write(f"**Message:** {message}\n")

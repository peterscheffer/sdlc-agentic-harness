import os
import subprocess
import time

from utils.config import SDLCConfig, ProfileConfig
from utils.toolchain import detect_language
from gates.gate_runner import GateCheck


class SpecProfile:
    """A pluggable spec format + deterministic verifier.

    Each profile owns:
      - a spec-generation prompt fragment and parser for the requirements stage
      - scaffold targets (step definitions / test skeletons) and prompt
        guidance for the coding stage
      - a preflight check and an exit-code verifier for the testing stage

    Verification must be deterministic: the gate is the verifier command's
    exit code, never an LLM judgment.
    """

    name = ""
    display_name = ""

    def __init__(self, config: SDLCConfig, project_root: str = "."):
        self.config = config
        self.project_root = project_root
        self.profile_config = config.profiles.get(self.name) or ProfileConfig()
        self.language = detect_language(project_root)

    # --- identifiers -----------------------------------------------------

    @property
    def gate_name(self) -> str:
        return f"profile_{self.name.replace('-', '_')}_verified"

    # --- requirements stage ----------------------------------------------

    def spec_prompt_fragment(self) -> str:
        raise NotImplementedError

    def parse_and_write(self, llm_content: str) -> list[str]:
        """Extract this profile's spec from the LLM output and write it.
        Returns the list of file paths written."""
        raise NotImplementedError

    def spec_artifacts(self) -> list[str]:
        """Paths of this profile's spec artifacts currently on disk."""
        raise NotImplementedError

    def requirements_gate_checks(self) -> list[GateCheck]:
        raise NotImplementedError

    def cleanup_artifacts(self):
        for path in self.spec_artifacts():
            if os.path.exists(path):
                os.remove(path)

    # --- coding stage ------------------------------------------------------

    def coding_context(self) -> str:
        parts = []
        for path in self.spec_artifacts():
            if os.path.exists(path):
                with open(path) as f:
                    parts.append(f"--- {path} ---\n{f.read()}")
        if not parts:
            return ""
        return f"{self.display_name} specs:\n" + "\n".join(parts)

    def coding_scaffold_targets(self, arch_targets: list[str]) -> list[str]:
        return []

    def coding_prompt_fragment(self) -> str:
        return ""

    # --- verification -------------------------------------------------------

    def resolve_command(self) -> str:
        """The verifier shell command (config override wins over the
        language-specific default)."""
        raise NotImplementedError

    def preflight(self) -> tuple[bool, str]:
        """Check the verifier can run at all (runner installed, config
        complete). Returns (ok, message); the message must be actionable."""
        return True, "No preflight requirements"

    def run_verifier(self) -> dict:
        """Run the verifier command and return
        {command, exit_code, output, duration_seconds, timed_out}."""
        command = self.resolve_command()
        return run_shell(command, self.config.timeouts.command_seconds)

    def verification_gate_checks(self, detail_chars: int = 2000) -> list[GateCheck]:
        def _check() -> tuple[bool, str]:
            result = self.run_verifier()
            if result["timed_out"]:
                return False, f"Verifier timed out: {result['command']}"
            if result["exit_code"] == 0:
                return True, f"Verifier exited 0: {result['command']}"
            tail = result["output"][-detail_chars:] if result["output"] else "(no output)"
            return False, (
                f"Verifier exited {result['exit_code']}: {result['command']}\n{tail}"
            )
        return [GateCheck(self.gate_name, f"{self.display_name} verifier passes", _check)]

    def report_section(self, result: dict) -> str:
        icon = "✓" if result["exit_code"] == 0 and not result["timed_out"] else "✗"
        status = "PASSED" if result["exit_code"] == 0 and not result["timed_out"] else \
                 "TIMEOUT" if result["timed_out"] else "FAILED"
        lines = [
            f"\n## Spec Verification: {self.display_name}",
            f"**Status:** {icon} {status}",
            f"**Command:** `{result['command']}`",
            f"**Exit Code:** {result['exit_code']}",
            f"**Duration:** {result['duration_seconds']:.1f}s",
        ]
        if result["output"]:
            lines.append(f"\n### Output (last 1000 chars)\n```\n{result['output'][-1000:]}\n```")
        return "\n".join(lines) + "\n"


def run_shell(command: str, timeout: int) -> dict:
    start = time.monotonic()
    try:
        result = subprocess.run(
            command, shell=True, capture_output=True, text=True, timeout=timeout
        )
        return {
            "command": command,
            "exit_code": result.returncode,
            "output": (result.stdout or "") + (result.stderr or ""),
            "duration_seconds": time.monotonic() - start,
            "timed_out": False,
        }
    except subprocess.TimeoutExpired:
        return {
            "command": command,
            "exit_code": -1,
            "output": f"Command timed out after {timeout} seconds",
            "duration_seconds": time.monotonic() - start,
            "timed_out": True,
        }
    except Exception as e:
        return {
            "command": command,
            "exit_code": -1,
            "output": str(e),
            "duration_seconds": time.monotonic() - start,
            "timed_out": False,
        }


def command_available(probe_command: str, timeout: int = 30) -> bool:
    result = run_shell(probe_command, timeout)
    return result["exit_code"] == 0

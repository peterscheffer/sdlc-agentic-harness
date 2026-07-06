import os
import re
import shlex
import signal
import subprocess
import time
import urllib.request

from gates.gate_runner import GateCheck
from profiles.base import SpecProfile, run_shell, command_available

OPENAPI_BLOCK = re.compile(r"```openapi-yaml\s*\n(.*?)```", re.DOTALL)
DEFAULT_SPEC_PATH = "sdlc/requirements/openapi.yaml"
SERVER_STARTUP_TIMEOUT = 60


class OpenApiContractProfile(SpecProfile):
    """Spec is an OpenAPI document; verified by running schemathesis
    contract tests against the running service."""

    name = "openapi-contract"
    display_name = "OpenAPI Contract"

    def spec_path(self) -> str:
        return self.profile_config.spec_path or DEFAULT_SPEC_PATH

    # --- requirements stage ----------------------------------------------

    def spec_prompt_fragment(self) -> str:
        return (
            "### OpenAPI Contract Specification\n"
            "Produce a complete OpenAPI 3.x document describing every endpoint of the "
            "solution's API surface.\n"
            "- Include `openapi`, `info`, and `paths` at minimum\n"
            "- Define request/response schemas precisely (types, required fields, "
            "status codes) — the implementation will be contract-tested against this "
            "document with schemathesis, so the schemas must be exact\n"
            "- Include error responses (4xx/5xx) where applicable\n\n"
            "OpenAPI output format:\n"
            "```openapi-yaml\n"
            "openapi: 3.0.3\n"
            "info:\n"
            "  title: ...\n"
            "  version: 1.0.0\n"
            "paths:\n"
            "  ...\n"
            "```\n"
        )

    def parse_and_write(self, llm_content: str) -> list[str]:
        match = OPENAPI_BLOCK.search(llm_content)
        if not match:
            return []
        path = self.spec_path()
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        with open(path, "w") as f:
            f.write(match.group(1).strip() + "\n")
        return [path]

    def spec_artifacts(self) -> list[str]:
        path = self.spec_path()
        return [path] if os.path.exists(path) else []

    def requirements_gate_checks(self) -> list[GateCheck]:
        def _check() -> tuple[bool, str]:
            path = self.spec_path()
            if not os.path.exists(path):
                return False, f"{path} does not exist"
            with open(path) as f:
                content = f.read()
            try:
                import yaml
                doc = yaml.safe_load(content)
                if not isinstance(doc, dict):
                    return False, f"{path} is not a YAML mapping"
                if "openapi" not in doc:
                    return False, f"{path} is missing the 'openapi' version key"
                if not doc.get("paths"):
                    return False, f"{path} has no 'paths' defined"
            except ImportError:
                # PyYAML unavailable — fall back to a textual sanity check.
                if "openapi" not in content or "paths" not in content:
                    return False, f"{path} is missing 'openapi' or 'paths' keys"
            except Exception as e:
                return False, f"{path} is not valid YAML: {e}"
            return True, f"{path} is a valid OpenAPI document"
        return [GateCheck("openapi_spec_valid", "OpenAPI document exists and parses", _check)]

    # --- coding stage ------------------------------------------------------

    def coding_prompt_fragment(self) -> str:
        return (
            f"Implement the API exactly as specified in {self.spec_path()}: every path, "
            "method, request schema, response schema, and status code. The running "
            "service will be contract-tested against that document with schemathesis, "
            "so any deviation (missing endpoint, wrong status code, schema mismatch) "
            "is a hard failure."
        )

    # --- verification -------------------------------------------------------

    def resolve_command(self) -> str:
        if self.profile_config.command:
            return self.profile_config.command
        base_url = self.profile_config.base_url or "http://127.0.0.1:8000"
        return f"schemathesis run {self.spec_path()} --url {base_url}"

    def preflight(self) -> tuple[bool, str]:
        if self.profile_config.command:
            return True, "Custom verifier command configured"
        if not command_available("schemathesis --version"):
            return False, (
                "schemathesis is not installed. Install with: pip install schemathesis, "
                "or set profiles.\"openapi-contract\".command in sdlc.config.json"
            )
        if not self.profile_config.server_command or not self.profile_config.base_url:
            return False, (
                "openapi-contract needs profiles.\"openapi-contract\".server_command and "
                "base_url in sdlc.config.json (how to start the service and where it "
                "listens), or a full profiles.\"openapi-contract\".command override."
            )
        return True, "schemathesis is available and server_command/base_url configured"

    def run_verifier(self) -> dict:
        # Full override runs verbatim — the user owns server lifecycle.
        if self.profile_config.command:
            return run_shell(self.profile_config.command, self.config.timeouts.command_seconds)

        start = time.monotonic()
        command = self.resolve_command()
        server = subprocess.Popen(
            self.profile_config.server_command,
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            start_new_session=True,
        )
        try:
            if not self._wait_for_server(server):
                return {
                    "command": command,
                    "exit_code": -1,
                    "output": (
                        f"Service did not become ready at {self._health_url()} within "
                        f"{SERVER_STARTUP_TIMEOUT}s (server command: "
                        f"{self.profile_config.server_command})"
                    ),
                    "duration_seconds": time.monotonic() - start,
                    "timed_out": True,
                }
            result = run_shell(command, self.config.timeouts.command_seconds)
            result["duration_seconds"] = time.monotonic() - start
            return result
        finally:
            self._stop_server(server)

    def _health_url(self) -> str:
        base = self.profile_config.base_url.rstrip("/")
        health = self.profile_config.health_path or "/"
        return base + "/" + health.lstrip("/")

    def _wait_for_server(self, server: subprocess.Popen) -> bool:
        deadline = time.monotonic() + SERVER_STARTUP_TIMEOUT
        url = self._health_url()
        while time.monotonic() < deadline:
            if server.poll() is not None:
                return False
            try:
                urllib.request.urlopen(url, timeout=2)
                return True
            except Exception:
                time.sleep(0.5)
        return False

    def _stop_server(self, server: subprocess.Popen):
        if server.poll() is not None:
            return
        try:
            os.killpg(os.getpgid(server.pid), signal.SIGTERM)
        except (ProcessLookupError, PermissionError, OSError):
            server.terminate()
        try:
            server.wait(timeout=10)
        except subprocess.TimeoutExpired:
            try:
                os.killpg(os.getpgid(server.pid), signal.SIGKILL)
            except (ProcessLookupError, PermissionError, OSError):
                server.kill()

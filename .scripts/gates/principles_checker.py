import os
import re
from typing import Optional

PRINCIPLES_PATH = "PRINCIPLES.md"


class PrinciplesRule:
    def __init__(self, rule_id: str, description: str, severity: str, check: str):
        self.rule_id = rule_id
        self.description = description
        self.severity = severity
        self.check = check


def load_principles() -> tuple[Optional[list[PrinciplesRule]], Optional[str]]:
    if not os.path.exists(PRINCIPLES_PATH):
        return None, "Warning: PRINCIPLES.md not found. Skipping PRINCIPLES compliance checks."

    with open(PRINCIPLES_PATH) as f:
        content = f.read()

    rules = _parse_principles(content)
    if not rules:
        return [], "PRINCIPLES.md has no rules defined."

    return rules, None


def _parse_principles(content: str) -> list[PrinciplesRule]:
    rules = []
    pattern = r'###\s+(\S+)\s*\n\s*description:\s*(.+?)\n\s*severity:\s*(error|warning)\s*\n\s*check:\s*(.+?)(?=\n###|\Z)'
    matches = re.findall(pattern, content, re.DOTALL)
    for match in matches:
        rule_id = match[0].strip()
        description = match[1].strip()
        severity = match[2].strip()
        check = match[3].strip()
        rules.append(PrinciplesRule(rule_id, description, severity, check))
    return rules


def validate_architecture(
    arch_md_path: str,
    rules: list[PrinciplesRule],
) -> tuple[list[dict], bool]:
    violations = []
    has_errors = False

    if not os.path.exists(arch_md_path):
        return violations, False

    with open(arch_md_path) as f:
        arch_content = f.read()

    for rule in rules:
        status = "PASS"
        violation_detail = None
        check_lower = rule.check.lower()

        if "no direct" in check_lower or "must not" in check_lower or "should not" in check_lower:
            if _check_forbidden_pattern(arch_content, rule.check):
                status = "FAIL" if rule.severity == "error" else "WARN"
                violation_detail = f"Possible violation of: {rule.check}"

        if "all exports" in check_lower and "typed" in check_lower:
            if _check_missing_type_hints(arch_content):
                status = "FAIL" if rule.severity == "error" else "WARN"
                violation_detail = f"Possible violation: {rule.check}"

        violations.append({
            "rule_id": rule.rule_id,
            "description": rule.description,
            "severity": rule.severity,
            "check": rule.check,
            "status": status,
            "detail": violation_detail,
        })

        if status == "FAIL":
            has_errors = True

    return violations, has_errors


def _check_forbidden_pattern(content: str, pattern: str) -> bool:
    return False


def _check_missing_type_hints(content: str) -> bool:
    return False

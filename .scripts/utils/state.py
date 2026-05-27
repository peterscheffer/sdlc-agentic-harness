import json
import os
import uuid
from datetime import datetime, timezone
from typing import Optional
from pydantic import BaseModel, Field

STATE_FILE = ".sdlc_state.json"

VALID_STAGES = [
    "planning", "ui-design", "architecture",
    "requirements", "coding", "testing", "review", "pr", "complete"
]

STAGE_ORDER = {
    "planning": 1,
    "ui-design": 2,
    "architecture": 3,
    "requirements": 4,
    "coding": 5,
    "testing": 6,
    "review": 7,
    "pr": 8,
    "complete": 9,
}


class GateResults(BaseModel):
    prd_exists: Optional[bool] = None
    prd_schema_valid: Optional[bool] = None
    tasks_defined: Optional[bool] = None
    design_md_exists: Optional[bool] = None
    design_schema_valid: Optional[bool] = None
    arch_exists: Optional[bool] = None
    arch_schema_valid: Optional[bool] = None
    principles_errors_zero: Optional[bool] = None
    requirements_md_exists: Optional[bool] = None
    requirements_schema_valid: Optional[bool] = None
    feature_files_exist: Optional[bool] = None
    linter_passed: Optional[bool] = None
    build_passed: Optional[bool] = None
    target_files_exist: Optional[bool] = None
    tests_passed: Optional[bool] = None
    test_report_exists: Optional[bool] = None
    report_not_empty: Optional[bool] = None
    coverage_threshold_met: Optional[bool] = None
    gherkin_compliance: Optional[bool] = None
    review_exists: Optional[bool] = None
    recommendation_present: Optional[bool] = None
    gh_authenticated: Optional[bool] = None
    not_on_base_branch: Optional[bool] = None
    pr_created: Optional[bool] = None


class StageEntry(BaseModel):
    status: str = "not_started"
    completed_at: Optional[str] = None
    artefact: Optional[str] = None
    reason: Optional[str] = None
    iterations: Optional[int] = None
    coverage_percent: Optional[float] = None
    recommendation: Optional[str] = None
    gate_results: GateResults = Field(default_factory=GateResults)


class SDLCPersistedState(BaseModel):
    pipeline_id: str = ""
    intent: str = ""
    branch: str = ""
    started_at: str = ""
    current_stage: str = "INIT"
    completed_stages: list[str] = []
    stages: dict[str, StageEntry] = Field(default_factory=lambda: {
        s: StageEntry() for s in VALID_STAGES
    })
    pr_url: Optional[str] = None


def load_state() -> SDLCPersistedState:
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE) as f:
                data = json.load(f)
            return SDLCPersistedState.model_validate(data)
        except (json.JSONDecodeError, ValueError, KeyError):
            raise ValueError(
                f"{STATE_FILE} is corrupted or unparseable. "
                "Run `/sdlc reset` to clear it."
            )
    return SDLCPersistedState()


def save_state(state: SDLCPersistedState):
    with open(STATE_FILE, "w") as f:
        f.write(state.model_dump_json(indent=2))


def init_state(intent: str = "", branch: str = "") -> SDLCPersistedState:
    now = datetime.now(timezone.utc).isoformat()
    state = SDLCPersistedState(
        pipeline_id=str(uuid.uuid4()),
        intent=intent,
        branch=branch,
        started_at=now,
        current_stage="planning",
    )
    state.stages["planning"].status = "in_progress"
    save_state(state)
    return state


def get_expected_next_stages(state: SDLCPersistedState) -> list[str]:
    completed = set(state.completed_stages)
    if "planning" not in completed:
        return ["planning"]
    if "ui-design" not in completed and "architecture" not in completed:
        return ["ui-design", "architecture"]
    if "architecture" not in completed:
        return ["architecture"]
    if "requirements" not in completed:
        return ["requirements"]
    if "coding" not in completed:
        return ["coding"]
    if "testing" not in completed:
        return ["testing"]
    if "review" not in completed:
        return ["review"]
    if "pr" not in completed:
        return ["pr"]
    return ["complete"]


def validate_stage_transition(state: SDLCPersistedState, target_stage: str) -> Optional[str]:
    if target_stage == "planning" and state.current_stage == "INIT":
        return None
    if target_stage in state.completed_stages:
        return None
    expected = get_expected_next_stages(state)
    if target_stage in expected:
        return None
    return (
        f"Error: Cannot advance to {target_stage}. "
        f"Completed stages: {state.completed_stages}. "
        f"Expected next stage: {expected[0] if expected else 'none'}."
    )

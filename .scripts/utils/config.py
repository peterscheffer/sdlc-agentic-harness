import json
import os
from typing import Optional
from pydantic import BaseModel, Field

CONFIG_PATH = "sdlc.config.json"


VALID_PROVIDERS = {"ollama", "openrouter", None}


class StageConfig(BaseModel):
    model: Optional[str] = None
    provider: Optional[str] = None
    max_iterations: Optional[int] = None


class CommandsConfig(BaseModel):
    lint: str = ""
    build: str = ""
    test: str = ""
    coverage_report: Optional[str] = None


class CoverageConfig(BaseModel):
    enabled: bool = False
    min_percentage: int = 80


class GithubConfig(BaseModel):
    base_branch: str = "main"


class TimeoutsConfig(BaseModel):
    llm_call_seconds: int = 120
    command_seconds: int = 300


class SDLCConfig(BaseModel):
    default_model: str
    provider: Optional[str] = None
    stages: dict[str, StageConfig] = {}
    commands: CommandsConfig = CommandsConfig()
    coverage: CoverageConfig = CoverageConfig()
    github: GithubConfig = GithubConfig()
    timeouts: TimeoutsConfig = TimeoutsConfig()


def load_config() -> SDLCConfig:
    if not os.path.exists(CONFIG_PATH):
        raise FileNotFoundError(
            f"{CONFIG_PATH} not found. Create this file at the project root. "
            "See PRINCIPLES.example.md for a template."
        )
    try:
        with open(CONFIG_PATH) as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON in {CONFIG_PATH}: {e}")

    return SDLCConfig.model_validate(data)


def get_stage_model(config: SDLCConfig, stage_id: str) -> str:
    stage_cfg = config.stages.get(stage_id)
    if stage_cfg and stage_cfg.model:
        return stage_cfg.model
    return config.default_model


def get_stage_provider(config: SDLCConfig, stage_id: str) -> Optional[str]:
    stage_cfg = config.stages.get(stage_id)
    if stage_cfg and stage_cfg.provider is not None:
        return stage_cfg.provider
    return config.provider


def get_max_iterations(config: SDLCConfig, stage_id: str) -> int:
    stage_cfg = config.stages.get(stage_id)
    if stage_cfg and stage_cfg.max_iterations is not None:
        return stage_cfg.max_iterations
    return 5

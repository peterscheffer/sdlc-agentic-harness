from typing import Optional

from utils.config import SDLCConfig
from utils.state import SDLCPersistedState
from profiles.base import SpecProfile
from profiles.gherkin_bdd import GherkinBddProfile
from profiles.var_spec import VarSpecProfile
from profiles.unit_tests import UnitTestsProfile
from profiles.openapi_contract import OpenApiContractProfile
from profiles.stitch_ui import StitchUiProfile

PROFILE_REGISTRY: dict[str, type[SpecProfile]] = {
    GherkinBddProfile.name: GherkinBddProfile,
    VarSpecProfile.name: VarSpecProfile,
    UnitTestsProfile.name: UnitTestsProfile,
    OpenApiContractProfile.name: OpenApiContractProfile,
    StitchUiProfile.name: StitchUiProfile,
}

LEGACY_DEFAULT = ["gherkin-bdd"]

# Recommended profile sets per solution classification; used when a
# classification exists but no explicit selection was made.
CLASSIFICATION_DEFAULTS = {
    "ui": ["stitch-ui", "gherkin-bdd", "unit-tests"],
    "mixed": ["stitch-ui", "gherkin-bdd", "unit-tests"],
    "api": ["openapi-contract", "unit-tests"],
    "service": ["unit-tests"],
    "integration": ["unit-tests"],
    "data": ["unit-tests"],
}


def validate_profile_names(names: list[str]) -> Optional[str]:
    unknown = [n for n in names if n not in PROFILE_REGISTRY]
    if unknown:
        return (
            f"Unknown spec profile(s): {', '.join(unknown)}. "
            f"Valid profiles: {', '.join(sorted(PROFILE_REGISTRY))}"
        )
    return None


def resolve_profile_names(
    state: SDLCPersistedState,
    config: SDLCConfig,
    override: Optional[list[str]] = None,
) -> list[str]:
    """Resolution order: explicit override → state → config default →
    legacy gherkin-bdd.

    The classification recommendation is deliberately NOT auto-applied here:
    it reaches state.spec_profiles only via user confirmation (skill Q&A) or
    auto-accept mode at planning."""
    for candidate in (override, state.spec_profiles):
        if candidate:
            error = validate_profile_names(candidate)
            if error:
                raise ValueError(error)
            return candidate
    if config.default_profiles:
        error = validate_profile_names(config.default_profiles)
        if error:
            raise ValueError(error)
        return config.default_profiles
    return LEGACY_DEFAULT


def get_profiles(
    state: SDLCPersistedState,
    config: SDLCConfig,
    override: Optional[list[str]] = None,
) -> list[SpecProfile]:
    names = resolve_profile_names(state, config, override)
    return [PROFILE_REGISTRY[name](config) for name in names]

"""
Skill-level based training targets.

This module centralizes the mapping from skill levels to survival step targets
so the same logic is used consistently across reward calculation and state
vector construction.
"""

from __future__ import annotations

from typing import Dict


# Explicit survival targets for the currently supported discrete skill levels
# as requested: 0.1 → 300 steps, 0.5 → 1000 steps, 1.0 → 1500 steps.
TARGET_SURVIVAL_STEPS: Dict[float, int] = {
    0.1: 300,
    0.5: 1000,
    1.0: 1500,
}


def _default_formula(skill_level: float) -> int:
    """Fallback target when a non-discrete skill level is used.

    We keep the previous behavior for out-of-scope skill levels to avoid
    surprising changes if a different script passes an arbitrary value.
    Previously used ranges were 200 ~ 1400.
    """
    return int(200 + (skill_level * 1200))


def get_survival_target_steps(skill_level: float) -> int:
    """Return the target survival steps for a given skill level.

    - For the currently supported discrete skills (0.1, 0.5, 1.0) return the
      exact requested targets: 300, 1000, 1500.
    - For other values, fall back to the historical formula to keep behavior
      stable outside the specified regime.
    """
    # Direct match with tolerance to guard against float representation noise
    for key in TARGET_SURVIVAL_STEPS.keys():
        if abs(skill_level - key) < 1e-9:
            return TARGET_SURVIVAL_STEPS[key]

    # Fallback for values outside the discrete set
    return _default_formula(skill_level)


from __future__ import annotations

from pathlib import Path
from typing import Any, List, Optional, Union

import yaml

from src.constants import GEO_REGIONS


def load_criteria(path: Optional[Union[str, Path]] = None) -> dict[str, Any]:
    if path is None:
        path = Path(__file__).resolve().parents[1] / "config" / "sourcing_criteria.yaml"
    path = Path(path)
    with path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def criteria_prompt_block(criteria: dict[str, Any]) -> str:
    mandate = criteria.get("mandate", {})
    sectors = mandate.get("sectors_primary", [])
    excluded = mandate.get("sectors_excluded", [])
    return (
        f"Mandate: {mandate.get('name', '')}\n"
        f"Preferred sub-sectors (examples): {', '.join(sectors)}\n"
        f"Avoid / exclude sectors: {', '.join(excluded)}\n"
        "(Geographic scope for this run is defined only by **Target regions** / **Allowed region codes** below — "
        "not by any static multi-region line in config files.)\n"
    )


def region_codes_for_prompt(selected_regions: List[str]) -> List[str]:
    """Empty selection means global → all supported codes may appear in JSON."""
    if not selected_regions:
        return list(GEO_REGIONS)
    return list(selected_regions)


def allowed_regions_instruction_line(codes: List[str]) -> str:
    joined = ", ".join(codes)
    return (
        f"**Allowed region codes for this run** (use only these literals in "
        f"`regions_relevant` / `regions_addressed` arrays): {joined}.\n"
    )


def regions_block(selected_regions: List[str]) -> str:
    if not selected_regions:
        return "Target regions: ALL (global).\n"
    return f"Target regions (must bias candidates to these): {', '.join(selected_regions)}\n"


def deal_band_block(min_m: float, max_m: float) -> str:
    return (
        f"Deal size focus (implied enterprise value / typical check, USD millions): "
        f"prefer companies that plausibly fall between ${min_m:.0f}M and ${max_m:.0f}M. "
        f"Avoid highlighting names that are clearly far below ${min_m:.0f}M unless strategically exceptional.\n"
    )

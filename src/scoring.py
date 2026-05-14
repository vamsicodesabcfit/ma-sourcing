from __future__ import annotations

from typing import Any, Optional

from src.criteria import load_criteria
from src.models import EnrichedTarget


def score_target(
    enriched: EnrichedTarget,
    criteria_path: Optional[str] = None,
) -> tuple[float, dict[str, float]]:
    criteria = load_criteria(criteria_path)
    weights: dict[str, float] = dict(criteria.get("scoring_weights") or {})
    vec = enriched.scoring_vector()
    total = 0.0
    parts: dict[str, float] = {}
    for k, w in weights.items():
        wv = float(w)
        xv = float(vec.get(k, 0.0))
        contrib = wv * xv
        parts[k] = contrib
        total += contrib
    return total, parts


def should_surface(
    total_score: float,
    enriched: EnrichedTarget,
    criteria_path: Optional[str] = None,
) -> bool:
    criteria = load_criteria(criteria_path)
    rules = criteria.get("surface_rules") or {}
    min_total = float(rules.get("min_total_score", 0.35))
    min_ev = float(rules.get("min_evidence_quality", 0.25))
    return total_score >= min_total and enriched.evidence_quality >= min_ev

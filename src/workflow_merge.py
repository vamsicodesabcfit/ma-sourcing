from __future__ import annotations

from typing import Dict, List

from src.models import EnrichedTarget


def merge_enrichment_preserving_workflow(
    fresh: List[EnrichedTarget],
    previous: List[EnrichedTarget],
) -> List[EnrichedTarget]:
    prev_by: Dict[str, EnrichedTarget] = {e.company_name: e for e in previous}
    out: List[EnrichedTarget] = []
    for e in fresh:
        old = prev_by.get(e.company_name)
        if old:
            e.workflow_status = old.workflow_status
            e.analyst_comment = old.analyst_comment
            e.watchlisted = old.watchlisted
        out.append(e)
    return out

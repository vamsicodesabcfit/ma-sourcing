from __future__ import annotations

from datetime import datetime, timezone
from typing import List

from src.models import EnrichedTarget
from src.scoring import score_target, should_surface


def prospect_to_markdown(e: EnrichedTarget, total: float, surface: bool) -> str:
    lines = [
        f"## {e.company_name}",
        f"- **Surface**: {surface} (total_score={total:.3f})",
        f"- **HQ**: {e.headquarters or e.hq_us_state_or_region or 'NA'}",
        f"- **Regions**: {', '.join(e.regions_addressed) or 'NA'}",
        f"- **Employees**: {e.employee_count or 'NA'}",
        f"- **Founded**: {e.year_founded or 'NA'}",
        f"- **CEO**: {e.ceo_name or 'NA'} | **Email**: {e.ceo_email or 'NA'}",
        f"- **Investors**: {', '.join(e.investors) if e.investors else 'NA'}",
        f"- **Last financing**: {e.last_financing_summary or 'NA'} ({e.last_financing_date or 'NA'})",
        f"- **Revenue (note)**: {e.revenue_note or 'NA'}",
        f"- **Profitability (note)**: {e.profitability_note or 'NA'}",
        f"- **Sub-sector**: {e.sub_sector or 'NA'} | **Ownership**: {e.ownership_signal} | **Scale**: {e.scale_signal}",
        f"- **Workflow**: {e.workflow_status} | **Watchlist**: {e.watchlisted}",
        f"- **Analyst comment**: {e.analyst_comment or '—'}",
        f"- **Diligence Q**: {'; '.join(e.diligence_questions[:5])}",
        f"- **Red flags**: {'; '.join(e.red_flags[:5])}",
        "",
    ]
    return "\n".join(lines)


def build_markdown_pack(enriched: List[EnrichedTarget], title: str = "ABC Fitness — M&A export") -> str:
    parts = [
        f"# {title}",
        f"_Generated {datetime.now(timezone.utc).isoformat()}_",
        "",
        "---",
        "",
    ]
    for e in sorted(enriched, key=lambda x: score_target(x)[0], reverse=True):
        total, _ = score_target(e)
        surf = should_surface(total, e)
        parts.append(prospect_to_markdown(e, total, surf))
        parts.append("---\n")
    return "\n".join(parts)

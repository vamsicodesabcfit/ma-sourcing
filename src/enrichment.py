from __future__ import annotations

from typing import Any, List, Optional, Tuple

from src.constants import DEAL_SIZE_MAX_M_USD, DEAL_SIZE_MIN_M_USD
from src.claude_client import complete_json
from src.criteria import (
    allowed_regions_instruction_line,
    criteria_prompt_block,
    deal_band_block,
    load_criteria,
    region_codes_for_prompt,
    regions_block,
)
from src.cursor_prompts import format_enrichment_instruction
from src.json_utils import extract_json_array, extract_json_object
from src.models import EnrichedTarget, enrich_from_dict
from src.tavily import tavily_search_sync

ENRICH_SYSTEM = """You are supporting ABC Fitness Corp Dev early-stage M&A sourcing.
Extract structured, comparable attributes for the target company. Follow region and deal-size context in the user message.

Rules:
- Cite sources in evidence when possible. evidence_quality reflects citation strength.
- All scores 0..1. No invented private financials; use revenue_note / profitability_note honestly.
- CEO email only if clearly published (company site / press). Otherwise null.
- Output ONLY valid JSON per schema in user message (no markdown).
"""


def _format_snippets(snippets: List[dict[str, Any]]) -> str:
    if not snippets:
        return "(none)"
    lines: List[str] = []
    for i, s in enumerate(snippets, 1):
        lines.append(
            f"[{i}] title={s.get('title')!r}\nurl={s.get('url')!r}\ncontent={s.get('content')!r}\n"
        )
    return "\n".join(lines)


def _tavily_for_company(
    company_name: str,
    regions: List[str],
    use_tavily: bool,
) -> List[dict[str, Any]]:
    if not use_tavily:
        return []
    geo = " ".join(regions) if regions else "global"
    q = f"{company_name} fitness wellness company headquarters employees funding CEO revenue {geo}"
    return tavily_search_sync(q, max_results=5)


def build_enrichment_prompt_markdown(
    companies: List[Tuple[str, Optional[str], Optional[str]]],
    regions: List[str],
    deal_min_m: float,
    deal_max_m: float,
    use_tavily: bool = True,
    criteria_path: Optional[str] = None,
) -> str:
    criteria = load_criteria(criteria_path)
    block = criteria_prompt_block(criteria)
    rb = regions_block(regions)
    db = deal_band_block(deal_min_m, deal_max_m)
    all_snips: List[dict[str, Any]] = []
    for name, web, _ in companies:
        all_snips.extend(_tavily_for_company(name, regions, use_tavily))
    snip_block = _format_snippets(all_snips[:25])
    return format_enrichment_instruction(
        companies=companies,
        regions=regions,
        deal_min_m=deal_min_m,
        deal_max_m=deal_max_m,
        criteria_block=block,
        regions_instruction=rb,
        deal_instruction=db,
        snippets_block=snip_block,
    )


def parse_enrichment_pasted_json(text: str) -> List[EnrichedTarget]:
    text = text.strip()
    if text.startswith("["):
        rows = extract_json_array(text)
        return [enrich_from_dict(r) for r in rows if isinstance(r, dict) and str(r.get("company_name", "")).strip()]
    data = extract_json_object(text)
    rows = data.get("enriched_targets")
    if rows is None and isinstance(data, list):
        rows = data
    if not isinstance(rows, list):
        raise ValueError("JSON must contain 'enriched_targets' array or be an array of targets.")
    return [enrich_from_dict(r) for r in rows if str(r.get("company_name", "")).strip()]


def run_enrichment_anthropic(
    company_name: str,
    website: Optional[str] = None,
    extra_notes: Optional[str] = None,
    regions: Optional[List[str]] = None,
    deal_min_m: float = float(DEAL_SIZE_MIN_M_USD),
    deal_max_m: float = float(DEAL_SIZE_MAX_M_USD),
    use_tavily: bool = True,
    criteria_path: Optional[str] = None,
) -> EnrichedTarget:
    if regions is None:
        regions = []
    criteria = load_criteria(criteria_path)
    block = criteria_prompt_block(criteria)
    rb = regions_block(regions)
    db = deal_band_block(deal_min_m, deal_max_m)
    codes = region_codes_for_prompt(regions)
    allowed_line = allowed_regions_instruction_line(codes)
    rrel_inner = ", ".join(f'"{c}"' for c in codes)
    snippets = _tavily_for_company(company_name, regions, use_tavily)

    user = f"""{block}
{rb}
{db}
{allowed_line}

Target:
- company_name: {company_name}
- website: {website or "null"}
- analyst notes: {extra_notes or "none"}

Web snippets:
{_format_snippets(snippets)}

Return JSON for this single company (same schema as one element of enriched_targets):
{{
  "company_name": "{company_name}",
  "website": null,
  "sub_sector": "",
  "hq_us_state_or_region": null,
  "headquarters": "",
  "regions_addressed": [{rrel_inner}],
  "employee_count": "",
  "last_financing_summary": "",
  "last_financing_date": "",
  "revenue_note": "",
  "profitability_note": "",
  "ceo_name": "",
  "ceo_email": null,
  "investors": [],
  "year_founded": null,
  "ownership_signal": "unknown",
  "scale_signal": "unknown",
  "b2b2c_distribution_relevant": 0.0,
  "software_or_data_component": 0.0,
  "fragmented_roll_up_potential": 0.0,
  "founder_led_or_tuck_in": 0.0,
  "scale_upside": 0.0,
  "low_integration_complexity": 0.0,
  "evidence_quality": 0.0,
  "diligence_questions": [],
  "red_flags": [],
  "evidence": [],
  "raw_notes": ""
}}
"""

    data = complete_json(ENRICH_SYSTEM, user)
    if not str(data.get("company_name", "")).strip():
        data["company_name"] = company_name
    return enrich_from_dict(data)


def run_enrichment(
    company_name: str,
    website: Optional[str] = None,
    extra_notes: Optional[str] = None,
    use_tavily: bool = True,
    criteria_path: Optional[str] = None,
) -> EnrichedTarget:
    return run_enrichment_anthropic(
        company_name,
        website=website,
        extra_notes=extra_notes,
        regions=["US"],
        deal_min_m=float(DEAL_SIZE_MIN_M_USD),
        deal_max_m=float(DEAL_SIZE_MAX_M_USD),
        use_tavily=use_tavily,
        criteria_path=criteria_path,
    )

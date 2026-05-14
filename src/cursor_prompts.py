from __future__ import annotations

from typing import List, Optional, Tuple

from src.criteria import allowed_regions_instruction_line, region_codes_for_prompt


def cursor_discovery_header() -> str:
    return """# Cursor task: M&A discovery (ABC Fitness)

You are the analysis engine. **Use web search / browsing as needed** (Crunchbase snippets, press, LinkedIn public, company sites). Return **only valid JSON** (no prose outside JSON) so the app can parse it.

**Ethics:** Do not fabricate private emails or financials. If unknown, use `null`, `"NA"`, or empty arrays. CEO email only if clearly published (site press kit, verified company domain). Never guess personal emails.

"""


def cursor_enrichment_header() -> str:
    return """# Cursor task: M&A enrichment batch (ABC Fitness)

Research each company. Return **only valid JSON** — one object with key `enriched_targets` (array). Use web sources; cite in `evidence` with `source_url` + short `quote` when possible.

**Ethics:** Revenue/profit for private cos often unknown — say so. Do not invent funding dates or investor names.

"""


def format_discovery_instruction(
    strategy_brief: str,
    regions: List[str],
    deal_min_m: float,
    deal_max_m: float,
    criteria_block: str,
    regions_instruction: str,
    deal_instruction: str,
    max_candidates: int,
) -> str:
    codes = region_codes_for_prompt(regions)
    allowed_line = allowed_regions_instruction_line(codes)
    rrel_inner = ", ".join(f'"{c}"' for c in codes)

    return f"""{cursor_discovery_header()}

## Inputs

{criteria_block}
{regions_instruction}
{deal_instruction}
{allowed_line}

### Strategy brief
\"\"\"{strategy_brief}\"\"\"

## Output JSON schema (exact keys)

```json
{{
  "candidates": [
    {{
      "company_name": "string",
      "headquarters": "City, Country or null",
      "hq_or_primary_us_state": "string or null (legacy short)",
      "regions_relevant": [{rrel_inner}],
      "website": "string or null",
      "sub_sector": "string",
      "ownership_signal": "founder-led|pe-backed|public|strategic-owned|unknown",
      "scale_signal": "micro|small|mid|large|unknown",
      "fit_rationale": "1-3 sentences",
      "risk_flags": ["string"],
      "confidence_0_1": 0.0,
      "suggested_next_step": "string",
      "estimated_ev_usd_millions_mid": null
    }}
  ],
  "search_queries_suggested": ["string"]
}}
```

- Provide up to **{max_candidates}** candidates biased to selected regions and deal band **${deal_min_m:.0f}M–${deal_max_m:.0f}M** where plausible.
- `estimated_ev_usd_millions_mid`: rough midpoint **only if** you have a defensible public hint; else `null`.

Return the JSON object now.
"""


def format_enrichment_instruction(
    companies: List[Tuple[str, Optional[str], Optional[str]]],
    regions: List[str],
    deal_min_m: float,
    deal_max_m: float,
    criteria_block: str,
    regions_instruction: str,
    deal_instruction: str,
    snippets_block: str,
) -> str:
    lines = []
    for name, web, notes in companies:
        lines.append(f"- company_name: {name} | website: {web or 'null'} | notes: {notes or 'none'}")
    company_block = "\n".join(lines)

    codes = region_codes_for_prompt(regions)
    allowed_line = allowed_regions_instruction_line(codes)
    rrel_inner = ", ".join(f'"{c}"' for c in codes)

    return f"""{cursor_enrichment_header()}

## Context

{criteria_block}
{regions_instruction}
{deal_instruction}
{allowed_line}

### Companies to enrich
{company_block}

### Optional web snippets (from app Tavily — may be empty)
{snippets_block}

## Output JSON schema

Return a single JSON object:

```json
{{
  "enriched_targets": [
    {{
      "company_name": "",
      "website": null,
      "sub_sector": "",
      "hq_us_state_or_region": null,
      "headquarters": "City, Country",
      "regions_addressed": [{rrel_inner}],
      "employee_count": "approx or NA",
      "last_financing_summary": "e.g. Series B PE — NA if unknown",
      "last_financing_date": "YYYY-MM or NA",
      "revenue_note": "qualitative / NA — do not invent precise $",
      "profitability_note": "NA or qualitative if public",
      "ceo_name": "",
      "ceo_email": "only if clearly public on company domain — else null",
      "investors": ["Name"],
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
      "evidence": [{{"claim":"","source_url":null,"quote":null}}],
      "raw_notes": ""
    }}
  ]
}}
```

Include one object per input company (same `company_name`). Return JSON only.
"""

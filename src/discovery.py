from __future__ import annotations

from typing import List, Optional

from src.claude_client import complete_json
from src.groq_client import complete_json_groq
from src.criteria import (
    allowed_regions_instruction_line,
    criteria_prompt_block,
    deal_band_block,
    load_criteria,
    region_codes_for_prompt,
    regions_block,
)
from src.constants import DEAL_SIZE_MAX_M_USD, DEAL_SIZE_MIN_M_USD
from src.cursor_prompts import format_discovery_instruction
from src.json_utils import extract_json_object
from src.models import DiscoveryResult, discovery_from_dict

DISCOVERY_SYSTEM = """You are an M&A sourcing analyst for global fitness / wellness / club software.
Propose acquisition target ideas (real companies). Respect region and deal-size instructions in the user message.

Rules:
- Do NOT invent precise revenue, EBITDA, or private emails.
- If uncertain, lower confidence and use unknown / null.
- Output ONLY valid JSON as described (no markdown outside JSON).
"""


def build_discovery_prompt_markdown(
    strategy_brief: str,
    regions: List[str],
    deal_min_m: float,
    deal_max_m: float,
    max_candidates: int = 15,
    criteria_path: Optional[str] = None,
) -> str:
    criteria = load_criteria(criteria_path)
    block = criteria_prompt_block(criteria)
    rb = regions_block(regions)
    db = deal_band_block(deal_min_m, deal_max_m)
    return format_discovery_instruction(
        strategy_brief=strategy_brief,
        regions=regions,
        deal_min_m=deal_min_m,
        deal_max_m=deal_max_m,
        criteria_block=block,
        regions_instruction=rb,
        deal_instruction=db,
        max_candidates=max_candidates,
    )


def parse_discovery_pasted_json(text: str) -> DiscoveryResult:
    data = extract_json_object(text)
    return discovery_from_dict(data)


def build_discovery_user_message(
    strategy_brief: str,
    regions: List[str],
    deal_min_m: float,
    deal_max_m: float,
    max_candidates: int = 15,
    criteria_path: Optional[str] = None,
) -> str:
    """User message shared by Anthropic, Groq, and Cursor prompt builders."""
    criteria = load_criteria(criteria_path)
    block = criteria_prompt_block(criteria)
    rb = regions_block(regions)
    db = deal_band_block(deal_min_m, deal_max_m)
    codes = region_codes_for_prompt(regions)
    allowed_line = allowed_regions_instruction_line(codes)
    rrel_inner = ", ".join(f'"{c}"' for c in codes)

    return f"""{block}
{rb}
{db}
{allowed_line}

Strategy / thesis:
\"\"\"{strategy_brief}\"\"\"

Return JSON:
{{
  "candidates": [
    {{
      "company_name": "string",
      "headquarters": "City, Country or null",
      "hq_or_primary_us_state": "string or null",
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

Up to {max_candidates} candidates. Bias to regions and ~${deal_min_m:.0f}M–${deal_max_m:.0f}M where plausible.
"""


def run_discovery_anthropic(
    strategy_brief: str,
    regions: List[str],
    deal_min_m: float,
    deal_max_m: float,
    max_candidates: int = 15,
    criteria_path: Optional[str] = None,
) -> DiscoveryResult:
    user = build_discovery_user_message(
        strategy_brief, regions, deal_min_m, deal_max_m, max_candidates, criteria_path
    )
    data = complete_json(DISCOVERY_SYSTEM, user)
    return discovery_from_dict(data)


def run_discovery_groq(
    strategy_brief: str,
    regions: List[str],
    deal_min_m: float,
    deal_max_m: float,
    max_candidates: int = 15,
    criteria_path: Optional[str] = None,
) -> DiscoveryResult:
    user = build_discovery_user_message(
        strategy_brief, regions, deal_min_m, deal_max_m, max_candidates, criteria_path
    )
    data = complete_json_groq(DISCOVERY_SYSTEM, user)
    return discovery_from_dict(data)


# Backwards-compatible name
def run_discovery(
    strategy_brief: str,
    max_candidates: int = 15,
    criteria_path: Optional[str] = None,
) -> DiscoveryResult:
    return run_discovery_anthropic(
        strategy_brief,
        regions=["US"],
        deal_min_m=float(DEAL_SIZE_MIN_M_USD),
        deal_max_m=float(DEAL_SIZE_MAX_M_USD),
        max_candidates=max_candidates,
        criteria_path=criteria_path,
    )

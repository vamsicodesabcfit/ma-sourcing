from __future__ import annotations

from typing import Any, List, Optional

from pydantic import BaseModel, ConfigDict, Field


class DiscoveryCandidate(BaseModel):
    model_config = ConfigDict(extra="ignore")

    company_name: str
    headquarters: Optional[str] = None
    hq_or_primary_us_state: Optional[str] = None  # legacy / short HQ hint
    regions_relevant: List[str] = Field(default_factory=list)
    website: Optional[str] = None
    sub_sector: Optional[str] = None
    ownership_signal: str = "unknown"
    scale_signal: str = "unknown"
    fit_rationale: str = ""
    risk_flags: List[str] = Field(default_factory=list)
    confidence_0_1: float = 0.5
    suggested_next_step: str = ""
    estimated_ev_usd_millions_mid: Optional[float] = None


class DiscoveryResult(BaseModel):
    candidates: List[DiscoveryCandidate]
    search_queries_suggested: List[str] = Field(default_factory=list)


class EvidenceItem(BaseModel):
    claim: str
    source_url: Optional[str] = None
    quote: Optional[str] = None


class EnrichedTarget(BaseModel):
    model_config = ConfigDict(extra="ignore")

    company_name: str
    website: Optional[str] = None
    sub_sector: Optional[str] = None
    hq_us_state_or_region: Optional[str] = None
    headquarters: Optional[str] = None
    regions_addressed: List[str] = Field(default_factory=list)
    employee_count: Optional[str] = None
    last_financing_summary: Optional[str] = None
    last_financing_date: Optional[str] = None
    revenue_note: Optional[str] = None
    profitability_note: Optional[str] = None
    ceo_name: Optional[str] = None
    ceo_email: Optional[str] = None
    investors: List[str] = Field(default_factory=list)
    year_founded: Optional[int] = None
    ownership_signal: str = "unknown"
    scale_signal: str = "unknown"
    b2b2c_distribution_relevant: float = 0.0
    software_or_data_component: float = 0.0
    fragmented_roll_up_potential: float = 0.0
    founder_led_or_tuck_in: float = 0.0
    scale_upside: float = 0.0
    low_integration_complexity: float = 0.0
    evidence_quality: float = 0.0
    diligence_questions: List[str] = Field(default_factory=list)
    red_flags: List[str] = Field(default_factory=list)
    evidence: List[EvidenceItem] = Field(default_factory=list)
    raw_notes: Optional[str] = None
    # Workflow fields (analyst UI)
    workflow_status: str = "draft"
    analyst_comment: str = ""
    watchlisted: bool = False

    def scoring_vector(self) -> dict[str, float]:
        return {
            "strategic_fit_b2b2c_distribution": self.b2b2c_distribution_relevant,
            "software_or_data_component": self.software_or_data_component,
            "fragmented_category_roll_up_potential": self.fragmented_roll_up_potential,
            "founder_led_or_tuck_in_friendly": self.founder_led_or_tuck_in,
            "scale_upside_locations_or_seats": self.scale_upside,
            "low_integration_complexity_vs_abc": self.low_integration_complexity,
            "evidence_quality": self.evidence_quality,
        }


def clamp01(x: Any) -> float:
    try:
        v = float(x)
    except (TypeError, ValueError):
        return 0.0
    return max(0.0, min(1.0, v))


def _parse_year(x: Any) -> Optional[int]:
    if x is None or x == "":
        return None
    try:
        return int(float(x))
    except (TypeError, ValueError):
        return None


def discovery_from_dict(data: dict[str, Any]) -> DiscoveryResult:
    cands = []
    for row in data.get("candidates", []):
        ev_mid = row.get("estimated_ev_usd_millions_mid")
        try:
            ev_mid_f = float(ev_mid) if ev_mid is not None else None
        except (TypeError, ValueError):
            ev_mid_f = None
        cands.append(
            DiscoveryCandidate(
                company_name=str(row.get("company_name", "")).strip(),
                headquarters=row.get("headquarters"),
                hq_or_primary_us_state=row.get("hq_or_primary_us_state"),
                regions_relevant=list(row.get("regions_relevant") or []),
                website=row.get("website"),
                sub_sector=row.get("sub_sector"),
                ownership_signal=str(row.get("ownership_signal", "unknown")),
                scale_signal=str(row.get("scale_signal", "unknown")),
                fit_rationale=str(row.get("fit_rationale", "")),
                risk_flags=list(row.get("risk_flags") or []),
                confidence_0_1=clamp01(row.get("confidence_0_1", 0.5)),
                suggested_next_step=str(row.get("suggested_next_step", "")),
                estimated_ev_usd_millions_mid=ev_mid_f,
            )
        )
    cands = [c for c in cands if c.company_name]
    return DiscoveryResult(
        candidates=cands,
        search_queries_suggested=list(data.get("search_queries_suggested") or []),
    )


def _evidence_items_from_raw(raw: Any) -> List[EvidenceItem]:
    """Groq/Cursor sometimes return a string or non-dict list item; normalize to EvidenceItem."""
    if raw is None:
        return []
    if isinstance(raw, str):
        s = raw.strip()
        return [EvidenceItem(claim=s, source_url=None, quote=None)] if s else []
    if not isinstance(raw, list):
        return []
    out: List[EvidenceItem] = []
    for e in raw:
        if isinstance(e, str):
            s = e.strip()
            if s:
                out.append(EvidenceItem(claim=s, source_url=None, quote=None))
        elif isinstance(e, dict):
            out.append(
                EvidenceItem(
                    claim=str(e.get("claim", "")),
                    source_url=e.get("source_url"),
                    quote=e.get("quote"),
                )
            )
    return out


def enrich_from_dict(row: dict[str, Any]) -> EnrichedTarget:
    evs = _evidence_items_from_raw(row.get("evidence"))
    inv = row.get("investors")
    if inv is None:
        investors: List[str] = []
    elif isinstance(inv, str):
        investors = [s.strip() for s in inv.split(",") if s.strip()]
    else:
        investors = [str(x).strip() for x in inv if str(x).strip()]

    hq = row.get("headquarters") or row.get("hq_us_state_or_region")

    return EnrichedTarget(
        company_name=str(row.get("company_name", "")).strip(),
        website=row.get("website"),
        sub_sector=row.get("sub_sector"),
        hq_us_state_or_region=row.get("hq_us_state_or_region") or hq,
        headquarters=hq,
        regions_addressed=list(row.get("regions_addressed") or []),
        employee_count=row.get("employee_count"),
        last_financing_summary=row.get("last_financing_summary"),
        last_financing_date=row.get("last_financing_date"),
        revenue_note=row.get("revenue_note"),
        profitability_note=row.get("profitability_note"),
        ceo_name=row.get("ceo_name"),
        ceo_email=row.get("ceo_email"),
        investors=investors,
        year_founded=_parse_year(row.get("year_founded")),
        ownership_signal=str(row.get("ownership_signal", "unknown")),
        scale_signal=str(row.get("scale_signal", "unknown")),
        b2b2c_distribution_relevant=clamp01(row.get("b2b2c_distribution_relevant", 0)),
        software_or_data_component=clamp01(row.get("software_or_data_component", 0)),
        fragmented_roll_up_potential=clamp01(row.get("fragmented_roll_up_potential", 0)),
        founder_led_or_tuck_in=clamp01(row.get("founder_led_or_tuck_in", 0)),
        scale_upside=clamp01(row.get("scale_upside", 0)),
        low_integration_complexity=clamp01(row.get("low_integration_complexity", 0)),
        evidence_quality=clamp01(row.get("evidence_quality", 0)),
        diligence_questions=list(row.get("diligence_questions") or []),
        red_flags=list(row.get("red_flags") or []),
        evidence=evs,
        raw_notes=row.get("raw_notes"),
        workflow_status=str(row.get("workflow_status", "draft")),
        analyst_comment=str(row.get("analyst_comment", "")),
        watchlisted=bool(row.get("watchlisted", False)),
    )

"""ABC Fitness — M&A proactive sourcing (Streamlit): Groq API (default), Cursor manual, Anthropic TBD."""

from __future__ import annotations

import base64
import json
import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

from src.constants import DEAL_SIZE_MAX_M_USD, DEAL_SIZE_MIN_M_USD, GEO_REGIONS
from src.criteria import load_criteria
from src.discovery import (
    build_discovery_prompt_markdown,
    parse_discovery_pasted_json,
    run_discovery_groq,
)
from src.enrichment import (
    build_enrichment_prompt_markdown,
    parse_enrichment_pasted_json,
    run_enrichment_groq,
)
from src.export_pack import build_markdown_pack
from src.models import DiscoveryCandidate, EnrichedTarget, discovery_from_dict, enrich_from_dict
from src.scoring import score_target, should_surface
from src.streamlit_theme import apply_streamlit_theme, render_app_hero
from src.user_feedback import maybe_render_error_dialog, notify_parse_error, queue_error_dialog
from src.workflow_merge import merge_enrichment_preserving_workflow

ROOT = Path(__file__).resolve().parent
CRITERIA_PATH = ROOT / "config" / "sourcing_criteria.yaml"
DOC_PATH = ROOT / "docs" / "USER_GUIDE.md"
LOGO_PNG = ROOT / "assets" / "abc_fitness_logo.png"
LOGO_SVG = ROOT / "assets" / "abc_fitness_logo.svg"


def _resolved_brand_logo() -> Optional[Path]:
    if LOGO_PNG.is_file():
        return LOGO_PNG
    if LOGO_SVG.is_file():
        return LOGO_SVG
    return None


# Workflow Status column: Glide data grid is canvas-based, so we use format_func for a visible ▼ affordance.
WORKFLOW_STATUS_OPTIONS: Tuple[str, ...] = ("draft", "submitted", "approved", "rejected", "deferred")


SCREENSHOTS: Tuple[Tuple[str, str], ...] = (
    ("discover-tab.png", "Discover: strategy, prompt panel (copy icon), paste JSON"),
    ("enrich-tab.png", "Enrich: source list, prompt panel, master table"),
    ("workflow-tab.png", "Workflow: data editor and session backup"),
    ("export-tab.png", "Export: Markdown pack and CSV downloads"),
)

# Mermaid source (ASCII only) — injected via JS to avoid raw `-->` in static HTML.
MERMAID_PIPELINE = """flowchart LR
  subgraph SB[Sidebar]
    A[Regions deal band provider]
  end
  subgraph DC[Discover]
    B[Strategy brief]
    C[Prompt or API]
    D[Candidates JSON]
  end
  subgraph EN[Enrich]
    E[Source list]
    F[Prompt or API]
    G[Enriched JSON]
    H[Master table CSV]
  end
  subgraph WF[Workflow]
    I[Statuses watchlist]
    J[Session backup]
  end
  subgraph XP[Export]
    K[Markdown and CSV]
  end
  A --> B --> C --> D --> E --> F --> G --> H --> I --> J --> K
"""


def _ev_lookup(candidates: List[DiscoveryCandidate]) -> Dict[str, Optional[float]]:
    return {c.company_name: c.estimated_ev_usd_millions_mid for c in candidates}


def load_frozen_demo() -> tuple[List[DiscoveryCandidate], List[EnrichedTarget]]:
    p = ROOT / "data" / "demo_frozen.json"
    with p.open(encoding="utf-8") as f:
        data = json.load(f)
    dr = discovery_from_dict(data.get("discovery") or {})
    enriched = [enrich_from_dict(row) for row in data.get("enriched_rows") or []]
    return dr.candidates, enriched


def _regions_from_ui(all_regions: bool, selected: List[str]) -> List[str]:
    if all_regions:
        return []
    return list(selected)


def _enriched_to_export_row(
    e: EnrichedTarget,
    discovery_ev_mid_m_usd: Optional[float] = None,
) -> Dict[str, Any]:
    """Flat row for UI + CSV. Decision columns first so triage is visible without horizontal scroll."""
    total, _ = score_target(e, CRITERIA_PATH)
    surf = should_surface(total, e, CRITERIA_PATH)
    return {
        # Identity (scan who this is)
        "company_name": e.company_name,
        "website": e.website,
        "headquarters": e.headquarters or e.hq_us_state_or_region,
        "regions_addressed": "; ".join(e.regions_addressed),
        "sub_sector": e.sub_sector,
        # Decision / scoring (YAML weights + surface gate)
        "total_score": round(total, 4),
        "surface": surf,
        "evidence_q": round(e.evidence_quality, 3),
        "n_evidence": len(e.evidence),
        "b2b2c": round(e.b2b2c_distribution_relevant, 3),
        "software": round(e.software_or_data_component, 3),
        "rollup": round(e.fragmented_roll_up_potential, 3),
        "founder_tuckin": round(e.founder_led_or_tuck_in, 3),
        "scale_upside": round(e.scale_upside, 3),
        "integration": round(e.low_integration_complexity, 3),
        "discovery_ev_mid_m_usd": discovery_ev_mid_m_usd,
        # Firmographics & signals
        "ownership": e.ownership_signal,
        "scale": e.scale_signal,
        "employee_count": e.employee_count,
        "year_founded": e.year_founded,
        "ceo_name": e.ceo_name,
        "ceo_email": e.ceo_email,
        "investors": "; ".join(e.investors),
        "last_financing_summary": e.last_financing_summary,
        "last_financing_date": e.last_financing_date,
        "revenue_note": e.revenue_note,
        "profitability_note": e.profitability_note,
        # Workflow
        "workflow_status": e.workflow_status,
        "watchlisted": e.watchlisted,
        "analyst_comment": e.analyst_comment,
        "diligence_q": " | ".join(e.diligence_questions[:5]),
        "red_flags": " | ".join(e.red_flags[:5]),
        "raw_notes": e.raw_notes,
    }


def _enrichment_results_column_config() -> Dict[str, Any]:
    """Highlight triage fields in the Enrich results table (read-only)."""
    return {
        "total_score": st.column_config.ProgressColumn(
            "Total score",
            help="Weighted sum of 0–1 fit dimensions (see sourcing_criteria.yaml scoring_weights).",
            format="%.3f",
            min_value=0.0,
            max_value=1.0,
        ),
        "evidence_q": st.column_config.ProgressColumn(
            "Evidence quality",
            help="Strength of sourcing for stated facts; used with total_score in the surface gate.",
            format="%.3f",
            min_value=0.0,
            max_value=1.0,
        ),
        "surface": st.column_config.CheckboxColumn(
            "Surface",
            help="True when total_score and evidence_q meet surface_rules thresholds.",
            disabled=True,
        ),
        "n_evidence": st.column_config.NumberColumn(
            "# Evidence",
            help="Count of structured evidence items attached to this target.",
            step=1,
            format="%d",
        ),
        "discovery_ev_mid_m_usd": st.column_config.NumberColumn(
            "Discovery EV (mid, $M)",
            help="Mid estimate from discovery JSON when available.",
            format="%.1f",
        ),
        "b2b2c": st.column_config.NumberColumn("B2B2C fit", format="%.2f", help="strategic_fit_b2b2c_distribution (0–1)."),
        "software": st.column_config.NumberColumn("Software / data", format="%.2f", help="software_or_data_component (0–1)."),
        "rollup": st.column_config.NumberColumn("Roll-up potential", format="%.2f", help="fragmented_category_roll_up_potential (0–1)."),
        "founder_tuckin": st.column_config.NumberColumn(
            "Founder / tuck-in", format="%.2f", help="founder_led_or_tuck_in_friendly (0–1)."
        ),
        "scale_upside": st.column_config.NumberColumn(
            "Scale upside", format="%.2f", help="scale_upside_locations_or_seats (0–1)."
        ),
        "integration": st.column_config.NumberColumn(
            "Low integration", format="%.2f", help="low_integration_complexity_vs_abc (0–1)."
        ),
    }


def _master_table_rows(
    enriched: List[EnrichedTarget],
    ev_by_name: Dict[str, Optional[float]],
) -> List[Dict[str, Any]]:
    rows = []
    for e in enriched:
        r = _enriched_to_export_row(e, ev_by_name.get(e.company_name))
        rows.append(r)
    return rows


def _discovery_results_json_bytes(
    candidates: List[DiscoveryCandidate],
    queries: List[str],
) -> bytes:
    """JSON shape compatible with **Apply pasted discovery JSON** on the Discover tab."""
    payload = {
        "candidates": [c.model_dump(mode="json") for c in candidates],
        "search_queries_suggested": list(queries or []),
    }
    return json.dumps(payload, indent=2).encode("utf-8")


def _enrichment_results_json_bytes(enriched: List[EnrichedTarget]) -> bytes:
    """JSON shape compatible with **Apply pasted enrichment JSON** (`enriched_targets` array)."""
    payload = {"enriched_targets": [e.model_dump(mode="json") for e in enriched]}
    return json.dumps(payload, indent=2).encode("utf-8")


# Pad Status labels with figure spaces so the chevron reads as a right-side affordance (Glide has no split layout).
_MAX_WORKFLOW_STATUS_LEN = max(len(x) for x in WORKFLOW_STATUS_OPTIONS)


def _workflow_status_display(value: object) -> str:
    """Cell + dropdown label: status text, then chevron toward the right (Streamlit SelectboxColumn format_func)."""
    if value is None or (isinstance(value, float) and pd.isna(value)):
        label = "—"
    else:
        label = str(value).strip()
    # +3 breathing room after longest option so short values (e.g. draft) still push ▼ rightward.
    n_pad = max(1, _MAX_WORKFLOW_STATUS_LEN + 3 - len(label))
    return label + ("\u2007" * min(n_pad, 18)) + "\u00b7\u200a\u25bc"


def _normalize_workflow_status_value(raw: object, fallback: str) -> str:
    """Map editor output back to a canonical workflow_status (handles decorated labels if needed)."""
    if raw is None or (isinstance(raw, float) and pd.isna(raw)):
        return fallback if fallback in WORKFLOW_STATUS_OPTIONS else "draft"
    s = str(raw).strip()
    if s in WORKFLOW_STATUS_OPTIONS:
        return s
    # Strip padded display from format_func (figure / thin spaces, optional ·, ▼/▾).
    stripped = re.sub(r"([\u2007\u00a0\u200a]|\s)*(\u00b7[\u200a]*)?[\u25bc\u25be]\s*$", "", s).strip()
    if stripped in WORKFLOW_STATUS_OPTIONS:
        return stripped
    return fallback if fallback in WORKFLOW_STATUS_OPTIONS else "draft"


def _apply_workflow_editor(edited_df: pd.DataFrame, enriched: List[EnrichedTarget]) -> List[EnrichedTarget]:
    """Update workflow fields on matching companies (subset or full table)."""
    if edited_df.empty or "company_name" not in edited_df.columns:
        return enriched
    by_name = {e.company_name: e for e in enriched}
    for _, row in edited_df.iterrows():
        name = str(row["company_name"])
        e = by_name.get(name)
        if not e:
            continue
        e.workflow_status = _normalize_workflow_status_value(
            row.get("workflow_status"),
            e.workflow_status,
        )
        e.analyst_comment = str(row.get("analyst_comment", e.analyst_comment))
        e.watchlisted = bool(row.get("watchlisted", e.watchlisted))
    return enriched


def _canonical_workflow_table(df: pd.DataFrame) -> pd.DataFrame:
    """Coerce types/labels so baseline vs editor compare matches Streamlit/Glide output (avoids spurious autosave)."""
    d = df.reset_index(drop=True).copy()
    if d.empty or "company_name" not in d.columns:
        return d
    d = d.sort_values("company_name").reset_index(drop=True)
    if "workflow_status" in d.columns:
        d["workflow_status"] = [_normalize_workflow_status_value(v, "draft") for v in d["workflow_status"]]
    if "watchlisted" in d.columns:
        d["watchlisted"] = d["watchlisted"].fillna(False).astype(bool)
    if "analyst_comment" in d.columns:
        d["analyst_comment"] = d["analyst_comment"].fillna("").map(lambda x: str(x))
    d["company_name"] = d["company_name"].map(lambda x: str(x))
    if "headquarters" in d.columns:
        d["headquarters"] = d["headquarters"].fillna("").map(lambda x: str(x))
    return d


def _render_pipeline_mermaid() -> None:
    """Render Mermaid in-browser (Streamlit markdown does not support Mermaid)."""
    b64 = base64.b64encode(MERMAID_PIPELINE.encode("utf-8")).decode("ascii")
    components.html(
        f"""
<!DOCTYPE html>
<html><head><meta charset="utf-8"/></head>
<body style="margin:0;padding:8px;background:linear-gradient(165deg,#f8fafc,#ecfdf5);">
<script src="https://cdn.jsdelivr.net/npm/mermaid@10.6.1/dist/mermaid.min.js"></script>
<div id="mgroot" class="mermaid"></div>
<script>
  (function() {{
    const b64 = "{b64}";
    const bin = atob(b64);
    const bytes = new Uint8Array(bin.length);
    for (let i = 0; i < bin.length; i++) bytes[i] = bin.charCodeAt(i);
    const txt = new TextDecoder("utf-8").decode(bytes);
    const el = document.getElementById("mgroot");
    el.textContent = txt;
    mermaid.initialize({{ startOnLoad: false, theme: "neutral", securityLevel: "loose" }});
    mermaid.run({{ nodes: [el] }}).catch(function() {{
      el.innerHTML = "<pre style='color:#b91c1c'>Could not render diagram.</pre>";
    }});
  }})();
</script>
</body></html>
        """,
        height=420,
    )


def _prompt_textarea_with_copy(
    prompt_text: str,
    height_px: int,
    component_id: str,
) -> None:
    """Read-only prompt in an iframe with a copy icon overlaid on the top-right."""
    b64 = base64.b64encode(prompt_text.encode("utf-8")).decode("ascii")
    h = max(120, int(height_px))
    components.html(
        f"""
<!DOCTYPE html>
<html><head><meta charset="utf-8">
<style>
  .wrap {{ position: relative; width: 100%; font-family: system-ui, -apple-system, sans-serif; }}
  .ta {{ width: 100%; height: {h}px; box-sizing: border-box; padding: 10px 42px 10px 10px;
        font-size: 13px; line-height: 1.45; border: 1px solid rgba(5,150,105,0.28); border-radius: 12px;
        resize: vertical; background: rgba(255,255,255,0.95); color: #0f172a; }}
  .copyb {{ position: absolute; top: 10px; right: 10px; z-index: 3; cursor: pointer; border: none;
          background: rgba(236,253,245,0.98); font-size: 18px; padding: 6px 10px; border-radius: 10px;
          box-shadow: 0 2px 8px rgba(5,150,105,0.18); line-height: 1; transition: transform 0.15s ease, box-shadow 0.15s ease; }}
  .copyb:hover {{ background: #d1fae5; transform: scale(1.03); }}
  .msg {{ font-size: 12px; margin-top: 6px; color: #475569; min-height: 18px; }}
</style></head><body>
<div class="wrap">
  <textarea class="ta" id="ta_{component_id}" readonly spellcheck="false" aria-label="Generated prompt"></textarea>
  <button type="button" class="copyb" id="btn_{component_id}" title="Copy prompt to clipboard" aria-label="Copy">📋</button>
</div>
<div class="msg" id="msg_{component_id}"></div>
<script>
  (function() {{
    const b64 = "{b64}";
    const ta = document.getElementById("ta_{component_id}");
    const bin = atob(b64);
    const bytes = new Uint8Array(bin.length);
    for (let i = 0; i < bin.length; i++) bytes[i] = bin.charCodeAt(i);
    ta.value = new TextDecoder("utf-8").decode(bytes);
    document.getElementById("btn_{component_id}").addEventListener("click", async function() {{
      const msg = document.getElementById("msg_{component_id}");
      try {{
        await navigator.clipboard.writeText(ta.value);
        msg.textContent = "Copied";
        msg.style.color = "#166534";
      }} catch (e) {{
        ta.focus();
        ta.select();
        msg.textContent = "Clipboard blocked — press ⌘A / Ctrl+A here, then copy; or use Download .md below.";
        msg.style.color = "#b91c1c";
      }}
    }});
  }})();
</script>
</body></html>
        """,
        height=h + 52,
    )


def _enrichment_targets_from_inputs(
    src: str,
    csv_file: Optional[Any],
) -> List[Tuple[str, Optional[str], Optional[str]]]:
    targets: List[Tuple[str, Optional[str], Optional[str]]] = []
    if src == "From discovery session":
        if "candidates" in st.session_state:
            for c in st.session_state["candidates"]:
                targets.append((c.company_name, c.website, None))
    elif csv_file is not None:
        df = pd.read_csv(csv_file)
        for _, r in df.iterrows():
            name = str(r.get("company_name", "")).strip()
            if not name:
                continue
            w = r.get("website")
            nts = r.get("notes")
            targets.append(
                (
                    name,
                    str(w) if pd.notna(w) and str(w).strip() else None,
                    str(nts) if pd.notna(nts) and str(nts).strip() else None,
                )
            )
    return targets


st.set_page_config(
    page_title="ABC Fitness — M&A Sourcing",
    page_icon="◎",
    layout="wide",
    initial_sidebar_state="expanded",
)

apply_streamlit_theme()
render_app_hero(logo_path=_resolved_brand_logo())

with st.sidebar:
    _logo = _resolved_brand_logo()
    if _logo is not None:
        st.image(str(_logo), use_container_width=True)
    st.markdown("#### Workspace")
    _criteria_sb = load_criteria(CRITERIA_PATH)

    with st.expander("Regions & deal size", expanded=True):
        all_geo = st.checkbox("All regions (global)", value=False, key="sb_all_geo")
        geo_sel = st.multiselect(
            "Regions",
            list(GEO_REGIONS),
            default=["US"],
            disabled=all_geo,
            key="sb_geo_sel",
        )
        deal_range = st.slider(
            "Deal band ($M implied EV)",
            min_value=int(DEAL_SIZE_MIN_M_USD),
            max_value=int(DEAL_SIZE_MAX_M_USD),
            value=(10, 120),
            help=f"Typical check / EV hint. Bounds {DEAL_SIZE_MIN_M_USD}M–{DEAL_SIZE_MAX_M_USD}M from config.",
            key="sb_deal_slider",
        )
        deal_min_m, deal_max_m = float(deal_range[0]), float(deal_range[1])
        if deal_min_m > deal_max_m:
            deal_min_m, deal_max_m = deal_max_m, deal_min_m

    with st.expander("Provider & integrations", expanded=True):
        if "sb_run_mode_widget" not in st.session_state and "run_mode" in st.session_state:
            st.session_state.sb_run_mode_widget = st.session_state["run_mode"]
        if "sb_run_mode_widget" not in st.session_state:
            st.session_state.sb_run_mode_widget = "groq"
        st.caption("How JSON is produced")
        st.radio(
            "Provider",
            ["groq", "cursor"],
            horizontal=True,
            key="sb_run_mode_widget",
            format_func=lambda x: "Groq — automatic" if x == "groq" else "Cursor — manual",
            label_visibility="visible",
        )
        st.button(
            "Anthropic (coming soon)",
            disabled=True,
            use_container_width=True,
            key="sb_btn_anthropic",
            help="Not available yet — Claude org API access is not configured for this build. Hover this button for details.",
        )
        run_mode = str(st.session_state.get("sb_run_mode_widget", "groq"))
        st.caption("Groq: set **MA_GROQ_KEY** or **GROQ_API_KEY** in the environment.")
        tv = st.text_input("Tavily API key (optional)", type="password", key="sb_tavily")
        if tv:
            os.environ["TAVILY_API_KEY"] = tv
        use_tavily = st.toggle(
            "Include Tavily snippets in enrichment prompts",
            value=bool(tv),
            key="sb_use_tavily",
        )

    with st.expander("Demo & mandate", expanded=False):
        demo = st.checkbox("Frozen demo dataset", value=False, key="sb_demo")
        st.caption("Mandate excerpt (`config/sourcing_criteria.yaml`)")
        st.json(_criteria_sb.get("mandate", {}))

regions_eff = _regions_from_ui(all_geo, geo_sel)

_scope_sig = (all_geo, tuple(geo_sel), float(deal_min_m), float(deal_max_m))
if st.session_state.get("_prompt_scope_sig") != _scope_sig:
    st.session_state.pop("_disc_prompt", None)
    st.session_state.pop("_enr_prompt", None)
    st.session_state["_prompt_scope_sig"] = _scope_sig

(
    tab_disc,
    tab_enr,
    tab_wf,
    tab_exp,
    tab_doc,
    tab_abt,
) = st.tabs(
    ["Discover", "Enrich", "Workflow", "Export", "Documentation", "About"]
)

with tab_disc:
    st.markdown("### Strategy brief")
    default_brief = (
        "Strengthen B2B2C distribution (clubs, employers, partners) with optional software/data angle; "
        "rollup-friendly or tuck-in tech in fitness / wellness."
    )
    brief = st.text_area("Mandate / thesis", value=default_brief, height=140)
    n_cand = st.slider("Max discovery candidates", 5, 30, 15)

    st.markdown("---")
    st.subheader("Discovery — long list")
    if run_mode == "cursor":
        if st.button("Generate discovery prompt for Cursor", type="primary", use_container_width=True):
            md = build_discovery_prompt_markdown(
                brief, regions_eff, deal_min_m, deal_max_m, n_cand, str(CRITERIA_PATH)
            )
            st.session_state["_disc_prompt"] = md
        if "_disc_prompt" in st.session_state:
            _disc = st.session_state["_disc_prompt"]
            st.caption("Generated prompt — use **📋** in the corner of the box to copy.")
            _prompt_textarea_with_copy(_disc, 320, "disc_prompt_box")
            st.download_button(
                label="Download prompt (.md)",
                data=_disc.encode("utf-8"),
                file_name="cursor_discovery_prompt.md",
                mime="text/markdown",
                type="secondary",
                use_container_width=True,
                key="dl_disc_prompt",
            )
        pasted_d = st.text_area("Paste discovery JSON here", height=160, key="paste_discovery")
        if st.button("Apply pasted discovery JSON", type="secondary", use_container_width=True):
            try:
                res = parse_discovery_pasted_json(pasted_d)
                st.session_state["candidates"] = res.candidates[:n_cand]
                st.session_state["queries"] = res.search_queries_suggested
                st.success(f"Loaded {len(st.session_state['candidates'])} candidates.")
            except Exception as ex:
                notify_parse_error("Discovery JSON", ex)
    else:
        if st.button("Run discovery (Groq)", type="primary", use_container_width=True):
            if demo:
                cands, _ = load_frozen_demo()
                st.session_state["candidates"] = cands[:n_cand]
                st.session_state["queries"] = []
                st.success("Loaded frozen demo.")
            else:
                with st.status("Discovery in progress", expanded=True) as status:
                    status.write(
                        "Sending your **mandate**, **regions**, and **deal band** to Groq. "
                        "This uses the same JSON contract as Cursor — without copy/paste."
                    )
                    try:
                        res = run_discovery_groq(
                            brief, regions_eff, deal_min_m, deal_max_m, n_cand, str(CRITERIA_PATH)
                        )
                        st.session_state["candidates"] = res.candidates
                        st.session_state["queries"] = res.search_queries_suggested
                        status.update(
                            label=f"Discovery complete — {len(res.candidates)} candidate(s)",
                            state="complete",
                            expanded=False,
                        )
                    except Exception as ex:
                        status.update(label="Discovery failed", state="error")
                        queue_error_dialog("Discovery", ex)

    if "candidates" in st.session_state:
        st.dataframe(
            pd.DataFrame([c.model_dump() for c in st.session_state["candidates"]]),
            use_container_width=True,
            hide_index=True,
        )
        st.markdown("##### Export results")
        _dc1, _dc2 = st.columns(2)
        with _dc1:
            st.download_button(
                "Download JSON",
                data=_discovery_results_json_bytes(
                    st.session_state["candidates"],
                    list(st.session_state.get("queries") or []),
                ),
                file_name="abc_ma_discovery.json",
                mime="application/json",
                type="secondary",
                use_container_width=True,
                key="dl_disc_json",
            )
        with _dc2:
            st.download_button(
                "Download CSV",
                data=pd.DataFrame([c.model_dump() for c in st.session_state["candidates"]])
                .to_csv(index=False)
                .encode("utf-8"),
                file_name="abc_ma_discovery.csv",
                mime="text/csv",
                type="secondary",
                use_container_width=True,
                key="dl_disc_csv",
            )
        if st.session_state.get("queries"):
            with st.expander("Suggested search ideas (optional)", expanded=False):
                st.caption(
                    "The discovery model returns **example web queries** so analysts can go deeper "
                    "(news, LinkedIn, niche databases). They are **not** run automatically by this app."
                )
                for q in st.session_state["queries"]:
                    st.write(f"- {q}")

with tab_enr:
    st.markdown("### Enrichment — firmographics + scores")
    src = st.radio("Source", ["From discovery session", "Upload CSV (company_name, website, notes)"])
    csv_up = None
    if src == "Upload CSV (company_name, website, notes)":
        csv_up = st.file_uploader("CSV", type=["csv"], key="enrich_csv")

    targets = _enrichment_targets_from_inputs(src, csv_up)
    if src == "From discovery session" and "candidates" not in st.session_state:
        st.warning("Run **Discover** first, or switch to CSV upload.")
    elif src == "Upload CSV (company_name, website, notes)" and csv_up is None:
        st.info("Upload a CSV to build the enrichment list.")

    if run_mode == "cursor":
        if st.button(
            "Generate enrichment prompt for Cursor",
            type="primary",
            disabled=not targets,
            use_container_width=True,
        ):
            md = build_enrichment_prompt_markdown(
                targets, regions_eff, deal_min_m, deal_max_m, use_tavily, str(CRITERIA_PATH)
            )
            st.session_state["_enr_prompt"] = md
        if "_enr_prompt" in st.session_state and targets:
            _enr = st.session_state["_enr_prompt"]
            st.caption("Generated prompt — use **📋** in the corner of the box to copy.")
            _prompt_textarea_with_copy(_enr, 380, "enr_prompt_box")
            st.download_button(
                label="Download prompt (.md)",
                data=_enr.encode("utf-8"),
                file_name="cursor_enrichment_prompt.md",
                mime="text/markdown",
                type="secondary",
                use_container_width=True,
                key="dl_enr_prompt",
            )
        pasted_e = st.text_area("Paste enrichment JSON here", height=200, key="paste_enrich")
        if st.button("Apply pasted enrichment JSON", type="primary", use_container_width=True):
            try:
                fresh = parse_enrichment_pasted_json(pasted_e)
                prev = st.session_state.get("enriched", [])
                st.session_state["enriched"] = merge_enrichment_preserving_workflow(fresh, prev)
                st.success(f"Loaded {len(fresh)} enriched targets.")
            except Exception as ex:
                notify_parse_error("Enrichment JSON", ex)
    else:
        if st.button("Enrich all (Groq)", type="primary", disabled=not targets, use_container_width=True):
            if demo:
                _, frozen_e = load_frozen_demo()
                st.session_state["enriched"] = frozen_e
                st.caption("Demo: loaded `data/demo_frozen.json`.")
            else:
                prev = st.session_state.get("enriched", [])
                out: List[EnrichedTarget] = []
                with st.status("Enrichment in progress", expanded=True) as status:
                    status.write(
                        f"Running **{len(targets)}** enrichment pass(es) via Groq — "
                        "firmographics, scores, and evidence use the **same schema** as Cursor JSON."
                    )
                    for i, (name, web, notes) in enumerate(targets):
                        status.write(f"**{i + 1} / {len(targets)}** — {name}")
                        try:
                            e = run_enrichment_groq(
                                name,
                                website=web,
                                extra_notes=notes,
                                regions=regions_eff,
                                deal_min_m=deal_min_m,
                                deal_max_m=deal_max_m,
                                use_tavily=use_tavily,
                                criteria_path=str(CRITERIA_PATH),
                            )
                            out.append(e)
                        except Exception as ex:
                            status.write(f"Skipped **{name}** — {ex}")
                    st.session_state["enriched"] = merge_enrichment_preserving_workflow(out, prev)
                    status.update(
                        label=f"Enrichment finished — {len(out)} / {len(targets)} row(s) merged",
                        state="complete",
                        expanded=False,
                    )
                if not out:
                    st.warning("No companies were enriched successfully in this pass. Check the status log above.")
                elif len(out) < len(targets):
                    st.info(f"Partial run: **{len(out)}** of **{len(targets)}** succeeded; others are noted in the status panel.")
                else:
                    st.success(f"All **{len(out)}** companies enriched and merged into the session.")

    if "enriched" in st.session_state and st.session_state["enriched"]:
        cands = st.session_state.get("candidates", [])
        ev_map = _ev_lookup(cands)
        rows = _master_table_rows(st.session_state["enriched"], ev_map)
        dfm = pd.DataFrame(rows).sort_values("total_score", ascending=False)
        st.caption(
            "**Triage first:** after company / sector, columns are **total score**, **surface** gate, **evidence** quality, "
            "**# evidence** items, score dimensions, then discovery EV — then firmographics and workflow."
        )
        _cfg = _enrichment_results_column_config()
        col_cfg = {k: v for k, v in _cfg.items() if k in dfm.columns}
        st.dataframe(dfm, use_container_width=True, hide_index=True, column_config=col_cfg)
        st.markdown("##### Export results")
        _ec1, _ec2 = st.columns(2)
        with _ec1:
            st.download_button(
                "Download JSON",
                data=_enrichment_results_json_bytes(st.session_state["enriched"]),
                file_name="abc_ma_enrichment.json",
                mime="application/json",
                type="secondary",
                use_container_width=True,
                key="dl_enr_json",
            )
        with _ec2:
            st.download_button(
                "Download CSV",
                data=dfm.to_csv(index=False).encode("utf-8"),
                file_name="abc_ma_master.csv",
                mime="text/csv",
                type="secondary",
                use_container_width=True,
                key="dl_enr_csv",
            )

with tab_wf:
    st.markdown("### Analyst workflow (approve / reject / watchlist)")
    if "enriched" not in st.session_state or not st.session_state["enriched"]:
        st.info("Complete enrichment on the **Enrich** tab first.")
    else:
        only_w = st.checkbox(
            "Show watchlisted only",
            value=False,
            key="wf_show_watchlisted_only",
            help="When turned on, your latest full-table edits are saved first, then only watchlisted rows are shown.",
        )
        prev = st.session_state.get("_wf_watchlist_filter_prev")
        _wf_applied_on_filter = False
        # Persist edits before changing which rows the grid shows (Streamlit order: checkbox updates before editor).
        if prev is not None and (not prev) and only_w:
            snap = st.session_state.get("_wf_editor_full_snapshot")
            if snap is not None and not snap.empty and "company_name" in snap.columns:
                st.session_state["enriched"] = _apply_workflow_editor(
                    _canonical_workflow_table(snap),
                    st.session_state["enriched"],
                )
                _wf_applied_on_filter = True
        elif prev is not None and prev and (not only_w):
            snap = st.session_state.get("_wf_last_edited_any")
            if snap is not None and not snap.empty and "company_name" in snap.columns:
                st.session_state["enriched"] = _apply_workflow_editor(
                    _canonical_workflow_table(snap),
                    st.session_state["enriched"],
                )
                _wf_applied_on_filter = True
        if _wf_applied_on_filter and hasattr(st, "toast"):
            st.toast("Workflow saved to session.", icon="✅")
        elif _wf_applied_on_filter:
            st.markdown(
                '<p class="abc-wf-autosave-note">Saved to session before updating the table view.</p>',
                unsafe_allow_html=True,
            )

        base = st.session_state["enriched"]
        if only_w:
            base = [e for e in base if e.watchlisted]
        wf_df = pd.DataFrame(
            [
                {
                    "company_name": e.company_name,
                    "headquarters": e.headquarters or e.hq_us_state_or_region,
                    "workflow_status": e.workflow_status,
                    "watchlisted": e.watchlisted,
                    "analyst_comment": e.analyst_comment,
                }
                for e in base
            ]
        )
        st.markdown(
            '<p class="abc-wf-table-hint">In <strong>Status</strong>, the label sits on the left and '
            "<strong>▼</strong> sits toward the right of the same cell (pick list). "
            "Click the cell to change "
            "<em>draft → submitted → approved / rejected / deferred</em>.</p>",
            unsafe_allow_html=True,
        )
        edited = st.data_editor(
            wf_df,
            use_container_width=True,
            hide_index=True,
            column_config={
                "workflow_status": st.column_config.SelectboxColumn(
                    "Status",
                    help="Pick list — click a cell; options use the same label + ▼ pattern.",
                    options=list(WORKFLOW_STATUS_OPTIONS),
                    format_func=_workflow_status_display,
                    required=True,
                    width="large",
                ),
                "watchlisted": st.column_config.CheckboxColumn("Watchlist"),
            },
            disabled=["company_name", "headquarters"],
            key="wf_editor",
        )
        st.session_state["_wf_last_edited_any"] = edited.copy()
        if not only_w:
            st.session_state["_wf_editor_full_snapshot"] = edited.copy()
        st.session_state["_wf_watchlist_filter_prev"] = only_w

        if st.button("Save workflow to session", type="primary", use_container_width=True, key="wf_save_explicit"):
            full = st.session_state["enriched"]
            st.session_state["enriched"] = _apply_workflow_editor(
                _canonical_workflow_table(edited),
                full,
            )
            if hasattr(st, "toast"):
                st.toast("Workflow saved to session.", icon="✅")
            else:
                st.success("Workflow saved to session.")
            st.rerun()
        st.caption(
            "Turning **Show watchlisted only** on or off saves pending grid edits first, then refreshes the rows shown. "
            "You can still use **Save workflow to session** anytime."
        )

        st.markdown("### Session backup (JSON)")
        snap = {
            "candidates": [c.model_dump(mode="json") for c in st.session_state.get("candidates", [])],
            "queries": st.session_state.get("queries", []),
            "enriched": [e.model_dump(mode="json") for e in st.session_state.get("enriched", [])],
            "regions": regions_eff,
            "deal_range": [deal_min_m, deal_max_m],
        }
        st.download_button(
            "Download session snapshot",
            data=json.dumps(snap, indent=2).encode("utf-8"),
            file_name="abc_ma_session.json",
            mime="application/json",
            type="secondary",
            use_container_width=True,
            key="dl_session_snap",
        )
        up_snap = st.file_uploader("Restore session JSON", type=["json"], key="snap_up")
        if up_snap and st.button("Apply snapshot restore", type="secondary", use_container_width=True):
            data = json.load(up_snap)
            st.session_state["candidates"] = [
                DiscoveryCandidate.model_validate(c) for c in data.get("candidates", [])
            ]
            st.session_state["queries"] = data.get("queries", [])
            st.session_state["enriched"] = [enrich_from_dict(x) for x in data.get("enriched", [])]
            st.success("Session restored.")
            st.rerun()

with tab_exp:
    st.markdown("### IC-style export pack")
    if "enriched" not in st.session_state or not st.session_state["enriched"]:
        st.info("Nothing to export yet.")
    else:
        md = build_markdown_pack(st.session_state["enriched"])
        st.download_button(
            "Download Markdown pack",
            data=md.encode("utf-8"),
            file_name="abc_ma_ic_pack.md",
            mime="text/markdown",
            type="secondary",
            use_container_width=True,
            key="dl_export_md",
        )
        full_rows = _master_table_rows(
            st.session_state["enriched"],
            _ev_lookup(st.session_state.get("candidates", [])),
        )
        st.download_button(
            "Download full CSV",
            data=pd.DataFrame(full_rows).to_csv(index=False).encode("utf-8"),
            file_name="abc_ma_export.csv",
            mime="text/csv",
            type="secondary",
            use_container_width=True,
            key="dl_export_csv",
        )

with tab_doc:
    st.markdown("## Product documentation")
    st.caption(
        "Pipeline overview (interactive diagram; Markdown in the guide below does not render Mermaid in Streamlit)."
    )
    _render_pipeline_mermaid()
    if DOC_PATH.is_file():
        st.markdown(DOC_PATH.read_text(encoding="utf-8"))
    else:
        st.error(f"Missing documentation file: `{DOC_PATH}`")

    st.divider()
    st.subheader("Screenshots (optional)")
    img_dir = ROOT / "docs" / "images"
    any_img = False
    for fname, caption in SCREENSHOTS:
        pth = img_dir / fname
        if pth.is_file():
            any_img = True
            st.image(str(pth), caption=caption)
    if not any_img:
        st.caption(
            f"No images found under `{img_dir}`. Add PNGs listed in `docs/images/README.md` "
            "to show UI flows here (e.g. after capturing from Streamlit)."
        )

with tab_abt:
    st.markdown(
        """
### About this build

Internal **early sourcing** tool for ABC Fitness Corp Dev. Full parameter reference, flows, and JSON contracts live in the **Documentation** tab (`docs/USER_GUIDE.md`).

### Compliance

Outputs are **triage**, not diligence. Do **not** use guessed personal emails for outreach. Use **NA** / null when facts are unknown.
        """
    )

maybe_render_error_dialog()

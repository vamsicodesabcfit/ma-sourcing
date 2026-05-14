"""ABC Fitness — M&A proactive sourcing (Streamlit): Cursor manual mode + optional Anthropic."""

from __future__ import annotations

import base64
import json
import os
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
    run_discovery_anthropic,
)
from src.enrichment import (
    build_enrichment_prompt_markdown,
    parse_enrichment_pasted_json,
    run_enrichment_anthropic,
)
from src.export_pack import build_markdown_pack
from src.models import DiscoveryCandidate, EnrichedTarget, discovery_from_dict, enrich_from_dict
from src.scoring import score_target, should_surface
from src.workflow_merge import merge_enrichment_preserving_workflow

ROOT = Path(__file__).resolve().parent
CRITERIA_PATH = ROOT / "config" / "sourcing_criteria.yaml"
DOC_PATH = ROOT / "docs" / "USER_GUIDE.md"
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


def _apply_workflow_editor(edited_df: pd.DataFrame, enriched: List[EnrichedTarget]) -> List[EnrichedTarget]:
    """Update workflow fields on matching companies (subset or full table)."""
    by_name = {e.company_name: e for e in enriched}
    for _, row in edited_df.iterrows():
        name = str(row["company_name"])
        e = by_name.get(name)
        if not e:
            continue
        e.workflow_status = str(row.get("workflow_status", e.workflow_status))
        e.analyst_comment = str(row.get("analyst_comment", e.analyst_comment))
        e.watchlisted = bool(row.get("watchlisted", e.watchlisted))
    return enriched


def _render_pipeline_mermaid() -> None:
    """Render Mermaid in-browser (Streamlit markdown does not support Mermaid)."""
    b64 = base64.b64encode(MERMAID_PIPELINE.encode("utf-8")).decode("ascii")
    components.html(
        f"""
<!DOCTYPE html>
<html><head><meta charset="utf-8"/></head>
<body style="margin:0;padding:8px;background:#fff;">
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
        font-size: 13px; line-height: 1.45; border: 1px solid #cbd5e1; border-radius: 8px;
        resize: vertical; background: #f8fafc; color: #1e293b; }}
  .copyb {{ position: absolute; top: 10px; right: 10px; z-index: 3; cursor: pointer; border: none;
          background: rgba(255,255,255,0.95); font-size: 18px; padding: 6px 10px; border-radius: 6px;
          box-shadow: 0 1px 4px rgba(15,23,42,0.12); line-height: 1; }}
  .copyb:hover {{ background: #e2e8f0; }}
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
)

st.title("ABC Fitness — Proactive M&A sourcing")
st.caption(
    "Multi-region mandate, deal-size band, firmographics, scoring, workflow, and exports. "
    "Default: **Cursor (manual)** — no Anthropic API required."
)

with st.sidebar:
    st.subheader("Scope")
    all_geo = st.checkbox("All regions (global)", value=False)
    geo_sel = st.multiselect(
        "Regions (multi-select)",
        list(GEO_REGIONS),
        default=["US"],
        disabled=all_geo,
    )
    deal_range = st.slider(
        "Deal size band (USD millions, implied EV / typical check)",
        min_value=int(DEAL_SIZE_MIN_M_USD),
        max_value=int(DEAL_SIZE_MAX_M_USD),
        value=(10, 120),
        help=f"Prefers ${DEAL_SIZE_MIN_M_USD}M–${DEAL_SIZE_MAX_M_USD}M; sub-${DEAL_SIZE_MIN_M_USD}M usually low impact.",
    )
    deal_min_m, deal_max_m = float(deal_range[0]), float(deal_range[1])
    if deal_min_m > deal_max_m:
        deal_min_m, deal_max_m = deal_max_m, deal_min_m

    st.subheader("Analysis engine")
    mode = st.radio(
        "Provider",
        ["Cursor (paste JSON)", "Anthropic API"],
        index=0,
        help="Cursor: copy prompt → run in Cursor with web → paste JSON.",
    )
    anthropic_key = st.text_input(
        "Anthropic API key (API mode only)",
        type="password",
        value=os.environ.get("ANTHROPIC_API_KEY", ""),
    )
    if anthropic_key:
        os.environ["ANTHROPIC_API_KEY"] = anthropic_key
    tv = st.text_input("Tavily API key (optional)", type="password")
    if tv:
        os.environ["TAVILY_API_KEY"] = tv
    use_tavily = st.toggle("Include Tavily snippets in enrichment prompts", value=bool(tv))

    demo = st.checkbox("Frozen demo dataset", value=False)
    criteria = load_criteria(CRITERIA_PATH)
    with st.expander("Mandate (YAML excerpt)"):
        st.json(criteria.get("mandate", {}))

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
    if mode == "Cursor (paste JSON)":
        if st.button("Generate discovery prompt for Cursor", type="primary"):
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
                key="dl_disc_prompt",
            )
        pasted_d = st.text_area("Paste discovery JSON here", height=160, key="paste_discovery")
        if st.button("Apply pasted discovery JSON"):
            try:
                res = parse_discovery_pasted_json(pasted_d)
                st.session_state["candidates"] = res.candidates[:n_cand]
                st.session_state["queries"] = res.search_queries_suggested
                st.success(f"Loaded {len(st.session_state['candidates'])} candidates.")
            except Exception as ex:
                st.error(f"Parse error: {ex}")
    else:
        if st.button("Run discovery (Anthropic)", type="primary"):
            if demo:
                cands, _ = load_frozen_demo()
                st.session_state["candidates"] = cands[:n_cand]
                st.session_state["queries"] = []
                st.success("Loaded frozen demo.")
            else:
                try:
                    with st.spinner("Calling Anthropic…"):
                        res = run_discovery_anthropic(
                            brief, regions_eff, deal_min_m, deal_max_m, n_cand, str(CRITERIA_PATH)
                        )
                    st.session_state["candidates"] = res.candidates
                    st.session_state["queries"] = res.search_queries_suggested
                    st.success(f"Discovered {len(res.candidates)} candidates.")
                except Exception as ex:
                    st.error(str(ex))
                    st.info("Set ANTHROPIC_API_KEY or switch to Cursor mode.")

    if "candidates" in st.session_state:
        st.dataframe(
            pd.DataFrame([c.model_dump() for c in st.session_state["candidates"]]),
            use_container_width=True,
            hide_index=True,
        )
        if st.session_state.get("queries"):
            st.markdown("**Suggested searches**")
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

    if mode == "Cursor (paste JSON)":
        if st.button("Generate enrichment prompt for Cursor", disabled=not targets):
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
                key="dl_enr_prompt",
            )
        pasted_e = st.text_area("Paste enrichment JSON here", height=200, key="paste_enrich")
        if st.button("Apply pasted enrichment JSON"):
            try:
                fresh = parse_enrichment_pasted_json(pasted_e)
                prev = st.session_state.get("enriched", [])
                st.session_state["enriched"] = merge_enrichment_preserving_workflow(fresh, prev)
                st.success(f"Loaded {len(fresh)} enriched targets.")
            except Exception as ex:
                st.error(f"Parse error: {ex}")
    else:
        if st.button("Enrich all (Anthropic)", type="primary", disabled=not targets):
            if demo:
                _, frozen_e = load_frozen_demo()
                st.session_state["enriched"] = frozen_e
                st.caption("Demo: loaded `data/demo_frozen.json`.")
            else:
                prev = st.session_state.get("enriched", [])
                out: List[EnrichedTarget] = []
                bar = st.progress(0.0)
                for i, (name, web, notes) in enumerate(targets):
                    try:
                        with st.spinner(f"Enriching {name}…"):
                            e = run_enrichment_anthropic(
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
                        st.warning(f"{name}: {ex}")
                    bar.progress((i + 1) / max(len(targets), 1))
                bar.empty()
                st.session_state["enriched"] = merge_enrichment_preserving_workflow(out, prev)

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
        st.download_button(
            "Download master CSV",
            data=dfm.to_csv(index=False).encode("utf-8"),
            file_name="abc_ma_master.csv",
            mime="text/csv",
        )

with tab_wf:
    st.markdown("### Analyst workflow (approve / reject / watchlist)")
    if "enriched" not in st.session_state or not st.session_state["enriched"]:
        st.info("Complete enrichment on the **Enrich** tab first.")
    else:
        only_w = st.checkbox("Show watchlisted only", value=False)
        base = st.session_state["enriched"]
        if only_w:
            base = [e for e in base if e.watchlisted]
        wf_df = pd.DataFrame(
            [
                {
                    "company_name": e.company_name,
                    "workflow_status": e.workflow_status,
                    "analyst_comment": e.analyst_comment,
                    "watchlisted": e.watchlisted,
                    "headquarters": e.headquarters or e.hq_us_state_or_region,
                }
                for e in base
            ]
        )
        edited = st.data_editor(
            wf_df,
            use_container_width=True,
            hide_index=True,
            column_config={
                "workflow_status": st.column_config.SelectboxColumn(
                    "Status",
                    options=["draft", "submitted", "approved", "rejected", "deferred"],
                    required=True,
                ),
                "watchlisted": st.column_config.CheckboxColumn("Watchlist"),
            },
            disabled=["company_name", "headquarters"],
            key="wf_editor",
        )
        if st.button("Save workflow changes to session"):
            full = st.session_state["enriched"]
            st.session_state["enriched"] = _apply_workflow_editor(edited, full)
            st.success("Workflow updated.")

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
        )
        up_snap = st.file_uploader("Restore session JSON", type=["json"], key="snap_up")
        if up_snap and st.button("Apply snapshot restore"):
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

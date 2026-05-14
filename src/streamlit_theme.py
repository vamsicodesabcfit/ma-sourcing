"""Streamlit UI layer: global CSS, hero header (ABC Fitness Corp Dev)."""

from __future__ import annotations

import html
import streamlit as st

# Inspired by modern deal / pipeline tools: airy layout, one strong accent, minimal chrome.
ABC_STREAMLIT_CSS = """
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:ital,opsz,wght@0,9..40,400;0,9..40,500;0,9..40,600;0,9..40,700;1,9..40,400&display=swap');

:root {
  --abc-navy: #0c4a6e;
  --abc-teal: #0f766e;
  --abc-emerald: #059669;
  --abc-emerald-soft: rgba(5, 150, 105, 0.14);
  --abc-slate: #0f172a;
  --abc-muted: #64748b;
}

.stApp {
  font-family: "DM Sans", ui-sans-serif, system-ui, -apple-system, "Segoe UI", sans-serif;
}

[data-testid="stAppViewContainer"] {
  background:
    radial-gradient(1200px 600px at 10% -10%, rgba(5, 150, 105, 0.09), transparent 55%),
    radial-gradient(900px 500px at 95% 0%, rgba(12, 74, 110, 0.08), transparent 50%),
    linear-gradient(165deg, #f8fafc 0%, #f1f5f9 45%, #ecfdf5 100%);
  background-attachment: fixed;
}

header[data-testid="stHeader"] {
  background: rgba(248, 250, 252, 0.72) !important;
  backdrop-filter: blur(10px);
  border-bottom: 1px solid rgba(15, 23, 42, 0.06);
}

section[data-testid="stSidebar"] {
  background: linear-gradient(180deg, #ffffff 0%, #f8fafc 100%) !important;
  border-right: 1px solid rgba(5, 150, 105, 0.2);
  box-shadow: 6px 0 32px rgba(15, 23, 42, 0.05);
}

section[data-testid="stSidebar"] h2,
section[data-testid="stSidebar"] h3 {
  color: var(--abc-navy) !important;
  font-weight: 600 !important;
  letter-spacing: -0.02em;
}

section[data-testid="stSidebar"] [data-testid="stMarkdown"] p,
section[data-testid="stSidebar"] label p {
  color: var(--abc-slate);
}

.main .block-container {
  padding-top: 1.25rem;
  padding-bottom: 3rem;
  max-width: 1200px;
}

@media (prefers-reduced-motion: no-preference) {
  .main .block-container {
    animation: abcmaFadeIn 0.4s cubic-bezier(0.22, 1, 0.36, 1) both;
  }
}

@keyframes abcmaFadeIn {
  from { opacity: 0; transform: translateY(10px); }
  to { opacity: 1; transform: translateY(0); }
}

.abc-hero {
  position: relative;
  overflow: hidden;
  border-radius: 16px;
  padding: 1.35rem 1.5rem 1.25rem;
  margin-bottom: 1.25rem;
  background: linear-gradient(125deg, rgba(255,255,255,0.92) 0%, rgba(236, 253, 245, 0.75) 100%);
  border: 1px solid rgba(5, 150, 105, 0.18);
  box-shadow:
    0 1px 2px rgba(15, 23, 42, 0.04),
    0 12px 40px -12px rgba(12, 74, 110, 0.15);
}

@media (prefers-reduced-motion: no-preference) {
  .abc-hero::after {
    content: "";
    position: absolute;
    inset: -40% -20% auto auto;
    width: 55%;
    height: 120%;
    background: radial-gradient(circle at 30% 30%, rgba(5, 150, 105, 0.12), transparent 62%);
    pointer-events: none;
    animation: abcmaShimmer 8s ease-in-out infinite alternate;
  }
}

@keyframes abcmaShimmer {
  from { opacity: 0.55; transform: translate(0, 0) rotate(0deg); }
  to { opacity: 1; transform: translate(-12px, 6px) rotate(3deg); }
}

.abc-hero-inner { position: relative; z-index: 1; }

.abc-hero-badge {
  display: inline-block;
  font-size: 0.72rem;
  font-weight: 600;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  color: var(--abc-teal);
  background: var(--abc-emerald-soft);
  border-radius: 999px;
  padding: 0.28rem 0.75rem;
  margin-bottom: 0.55rem;
}

.abc-hero-title {
  margin: 0 0 0.35rem 0;
  font-size: clamp(1.45rem, 2.6vw, 1.85rem);
  font-weight: 700;
  letter-spacing: -0.03em;
  color: var(--abc-slate);
  line-height: 1.2;
}

.abc-hero-sub {
  margin: 0 0 0.85rem 0;
  font-size: 0.98rem;
  color: var(--abc-muted);
  max-width: 52rem;
  line-height: 1.55;
}

.abc-hero-stats {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
}

.abc-pill {
  display: inline-flex;
  align-items: center;
  gap: 0.35rem;
  font-size: 0.82rem;
  color: var(--abc-navy);
  background: rgba(255, 255, 255, 0.85);
  border: 1px solid rgba(12, 74, 110, 0.12);
  border-radius: 999px;
  padding: 0.32rem 0.75rem;
  box-shadow: 0 1px 2px rgba(15, 23, 42, 0.04);
}

.abc-pill strong { color: var(--abc-emerald); font-weight: 700; }

div[data-testid="stTabs"] {
  margin-top: 0.25rem;
}

div[data-testid="stTabs"] [data-baseweb="tab-list"] {
  gap: 6px;
  background: rgba(255, 255, 255, 0.55);
  border-radius: 14px;
  padding: 6px 8px;
  border: 1px solid rgba(15, 23, 42, 0.06);
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.8);
}

div[data-testid="stTabs"] button[data-baseweb="tab"] {
  border-radius: 10px !important;
  padding: 0.45rem 0.85rem !important;
  font-weight: 500 !important;
  transition: background 0.2s ease, color 0.2s ease, box-shadow 0.2s ease;
}

div[data-testid="stTabs"] button[data-baseweb="tab"][aria-selected="true"] {
  background: linear-gradient(180deg, rgba(5, 150, 105, 0.16), rgba(5, 150, 105, 0.06)) !important;
  color: var(--abc-navy) !important;
  box-shadow: 0 1px 3px rgba(5, 150, 105, 0.2);
}

div[data-testid="stExpander"] details {
  border-radius: 12px !important;
  border: 1px solid rgba(15, 23, 42, 0.08) !important;
  background: rgba(255, 255, 255, 0.65) !important;
  box-shadow: 0 2px 10px rgba(15, 23, 42, 0.04);
}

[data-testid="stVerticalBlock"] > div {
  transition: opacity 0.2s ease;
}

button[kind="primary"] {
  transition: transform 0.15s ease, box-shadow 0.2s ease !important;
  border-radius: 10px !important;
  font-weight: 600 !important;
  min-height: 2.5rem;
}

/* Keep primary CTAs emerald (matches Streamlit theme); avoids washed-out primaries */
.main button[kind="primary"]:not(:disabled),
.main [data-testid="stDownloadButton"] button[kind="primary"]:not(:disabled) {
  background: linear-gradient(180deg, #10b981 0%, #059669 100%) !important;
  color: #ffffff !important;
  border: 1px solid rgba(15, 23, 42, 0.12) !important;
  border-radius: 10px !important;
  font-weight: 600 !important;
  min-height: 2.5rem !important;
}

/* Secondary = same visual weight as primary, alternate (navy) color — not the default ghost */
.main button[kind="secondary"]:not(:disabled),
.main [data-testid="stDownloadButton"] button[kind="secondary"]:not(:disabled) {
  border-radius: 10px !important;
  font-weight: 600 !important;
  min-height: 2.5rem !important;
  letter-spacing: 0.01em;
  background: rgba(255, 255, 255, 0.95) !important;
  color: var(--abc-navy) !important;
  border: 2px solid rgba(12, 74, 110, 0.55) !important;
  box-shadow: 0 1px 3px rgba(15, 23, 42, 0.06);
}

.main button[kind="secondary"]:not(:disabled):hover,
.main [data-testid="stDownloadButton"] button[kind="secondary"]:not(:disabled):hover {
  background: linear-gradient(180deg, #f0f9ff 0%, #e0f2fe 100%) !important;
  border-color: #0369a1 !important;
  color: #075985 !important;
  box-shadow: 0 4px 14px rgba(12, 74, 110, 0.12);
}

@media (prefers-reduced-motion: no-preference) {
  button[kind="primary"]:not(:disabled):hover {
    transform: translateY(-1px);
    box-shadow: 0 6px 20px rgba(5, 150, 105, 0.28) !important;
  }
  .main button[kind="secondary"]:not(:disabled):hover,
  .main [data-testid="stDownloadButton"] button[kind="secondary"]:not(:disabled):hover {
    transform: translateY(-1px);
  }
}

[data-testid="stMetric"] {
  background: rgba(255, 255, 255, 0.7);
  border: 1px solid rgba(15, 23, 42, 0.06);
  border-radius: 12px;
  padding: 0.5rem 0.75rem;
}

.stAlert {
  border-radius: 12px !important;
}

[data-testid="stDownloadButton"] button {
  border-radius: 10px !important;
  font-weight: 600 !important;
  letter-spacing: 0.01em;
}

hr {
  border: none;
  border-top: 1px solid rgba(15, 23, 42, 0.08);
  margin: 1.25rem 0;
}

/* Sidebar: calmer, more breathing room */
section[data-testid="stSidebar"] > div {
  padding-top: 0.35rem !important;
}
section[data-testid="stSidebar"] [data-testid="stSidebarContent"] {
  padding-top: 0.5rem !important;
  padding-bottom: 1.25rem !important;
}
section[data-testid="stSidebar"] .block-container {
  padding-top: 0.75rem !important;
  padding-bottom: 1rem !important;
  padding-left: 0.85rem !important;
  padding-right: 0.85rem !important;
}
section[data-testid="stSidebar"] h2,
section[data-testid="stSidebar"] h3,
section[data-testid="stSidebar"] h4 {
  margin-top: 0.15rem !important;
  margin-bottom: 0.45rem !important;
  font-size: 0.95rem !important;
  letter-spacing: -0.01em !important;
}
section[data-testid="stSidebar"] [data-testid="stExpander"] details {
  background: rgba(255, 255, 255, 0.55) !important;
  border: 1px solid rgba(15, 23, 42, 0.06) !important;
  border-radius: 12px !important;
  margin-bottom: 0.45rem !important;
}
section[data-testid="stSidebar"] [data-testid="stExpander"] summary {
  font-size: 0.88rem !important;
  font-weight: 600 !important;
  padding: 0.35rem 0.25rem !important;
}
section[data-testid="stSidebar"] [data-testid="stExpander"] summary span {
  opacity: 0.92;
}
section[data-testid="stSidebar"] .stMarkdown p,
section[data-testid="stSidebar"] [data-testid="stCaption"] {
  font-size: 0.82rem !important;
  line-height: 1.45 !important;
}
section[data-testid="stSidebar"] div[data-testid="stVerticalBlock"] > div {
  gap: 0.4rem !important;
}

@media (prefers-reduced-motion: reduce) {
  .main .block-container { animation: none !important; }
  .abc-hero::after { animation: none !important; }
  button[kind="primary"]:hover { transform: none !important; }
  .main button[kind="secondary"]:hover,
  .main [data-testid="stDownloadButton"] button[kind="secondary"]:hover {
    transform: none !important;
  }
}
"""


def apply_streamlit_theme() -> None:
    """Inject global CSS once per run (Streamlit re-executes script each interaction)."""
    st.markdown(f"<style>{ABC_STREAMLIT_CSS}</style>", unsafe_allow_html=True)


def render_app_hero() -> None:
    """Top-of-app hero: ABC Fitness positioning + live session counts."""
    n_cand = len(st.session_state.get("candidates") or [])
    n_enr = len(st.session_state.get("enriched") or [])
    sub = (
        "Multi-region mandate, deal-size band, firmographics, scoring, workflow, and exports. "
        "Default: <strong>Groq (API)</strong> for automatic discovery and enrichment; switch to "
        "<strong>Cursor</strong> for manual prompts and pasted JSON."
    )
    st.markdown(
        f"""
<div class="abc-hero">
  <div class="abc-hero-inner">
    <div class="abc-hero-badge">ABC Fitness · Corp Dev</div>
    <h1 class="abc-hero-title">Proactive M&amp;A sourcing</h1>
    <p class="abc-hero-sub">{sub}</p>
    <div class="abc-hero-stats">
      <span class="abc-pill"><strong>{html.escape(str(n_cand))}</strong> in discovery list</span>
      <span class="abc-pill"><strong>{html.escape(str(n_enr))}</strong> enriched targets</span>
    </div>
  </div>
</div>
        """,
        unsafe_allow_html=True,
    )

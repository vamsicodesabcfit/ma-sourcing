# ABC Fitness — M&A proactive sourcing (full build)

Internal tool for **early long-listing**: multi-region mandate, **$10M–$600M** deal band, firmographic enrichment, **weighted scoring**, **analyst workflow**, and **exports**—reducing reactive PitchBook-style browsing for first-pass triage.

## Analysis engine: Groq (default), Cursor, Anthropic (coming soon)

- **Groq (API, default):** same JSON schemas as Cursor mode; the app calls Groq directly—no copy/paste. Set **`MA_GROQ_KEY`** or **`GROQ_API_KEY`** in the environment that launches Streamlit (the UI does not store Groq keys).
- **Cursor:** generated **Markdown prompts**; run in Cursor with web search, then **paste JSON** back.
- **Anthropic (Claude):** **not enabled** in this build (org API access pending); UI shows “coming soon.”

Optional **`TAVILY_API_KEY`** pre-fetches snippets into enrichment prompts (Groq or Cursor).

Optional **`GROQ_MODEL`** overrides the default Groq model (`llama-3.3-70b-versatile`).

## Regions

Select **US, EU, India, AUS, LATAM, Japan** in any combination, or **All regions (global)**.

## Deal size band

Sidebar **range slider** (USD millions, implied EV / typical check): **$10M–$600M** bounds (`src/constants.py`); default band shown in UI is adjustable within that range.

## Firmographics (enrichment)

Per company the schema asks for:

- Headquarters  
- Employee count (approx / NA)  
- Last VC/PE financing + date (honest NA)  
- Revenue & profitability **notes** (no invented precision for privates)  
- CEO name; **email only if clearly public** (company domain / press)  
- Investors (list)  
- Year founded  

Plus existing **fit dimensions**, **evidence**, **diligence questions**, **red flags**.

## UI overview

Main tabs: **Discover** → **Enrich** → **Workflow** → **Export**, plus **Documentation** (full user guide, including a rendered pipeline diagram) and **About**.

| Tab | Features |
|-----|----------|
| **Discover** | Strategy brief → discovery prompt / API → candidates + suggested searches; **JSON/CSV download** |
| **Enrich** | Source list (session or CSV) → enrichment prompt / API → master table; **enrichment JSON + master CSV** |
| **Workflow** | Status, comments, watchlist editor; session JSON backup/restore |
| **Export** | Markdown IC pack + full CSV download |
| **Documentation** | Renders `docs/USER_GUIDE.md` + optional screenshots from `docs/images/` |
| **About** | Short compliance pointer |

Full detail: open **`docs/USER_GUIDE.md`** in-repo or use the **Documentation** tab in the app.

```bash
cd abc-fitness-ma-sourcing
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
streamlit run streamlit_app.py
```

Optional:

```bash
export MA_GROQ_KEY=...         # Groq API mode (or use GROQ_API_KEY)
export TAVILY_API_KEY=...      # Snippets in prompts
# export GROQ_MODEL=llama-3.3-70b-versatile   # optional
```

**Frozen demo:** enable in sidebar to load `data/demo_frozen.json` without any keys.

## Files

| Path | Role |
|------|------|
| `config/sourcing_criteria.yaml` | Mandate + scoring weights + surface thresholds |
| `src/constants.py` | Region list, deal bounds |
| `src/cursor_prompts.py` | Markdown + JSON schema text for Cursor |
| `src/discovery.py` | Discovery: Groq + Cursor parse + prompt builder |
| `src/enrichment.py` | Enrichment: Groq + Cursor parse + Tavily |
| `src/groq_client.py` | Groq chat completions → JSON |
| `src/json_utils.py` | Parse JSON from pasted chat |
| `src/export_pack.py` | Markdown IC pack |
| `src/workflow_merge.py` | Preserve workflow on re-import |
| `docs/USER_GUIDE.md` | Product documentation (TOC, parameters, flows) |
| `docs/images/` | Optional PNG screenshots for Documentation tab |
| `data/seed_targets.csv` | Example CSV |
| `data/demo_frozen.json` | Offline demo |

## Compliance

This is **triage**, not diligence. Do **not** use guessed personal emails for outreach. Human review before IC or external contact.

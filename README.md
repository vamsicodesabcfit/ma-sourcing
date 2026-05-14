# ABC Fitness — M&A proactive sourcing (full build)

Internal tool for **early long-listing**: multi-region mandate, **$10M–$600M** deal band, firmographic enrichment, **weighted scoring**, **analyst workflow**, and **exports**—reducing reactive PitchBook-style browsing for first-pass triage.

## Analysis engine: Cursor (default) or Anthropic

There is **no requirement** for `ANTHROPIC_API_KEY`.

- **Cursor (recommended):** the app generates **copy-paste prompts** (with JSON schema + ethics rules). You run them in **Cursor** with web search enabled, then **paste JSON** back into the app.
- **Anthropic API (optional):** same schemas; set `ANTHROPIC_API_KEY` and choose “Anthropic API” in the sidebar.

Optional **`TAVILY_API_KEY`** pre-fetches snippets into enrichment prompts (works with either mode).

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
| **Discover** | Strategy brief → discovery prompt / API → candidates + suggested searches |
| **Enrich** | Source list (session or CSV) → enrichment prompt / API → master table + CSV |
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
export ANTHROPIC_API_KEY=...   # API mode only
export TAVILY_API_KEY=...      # Snippets in prompts
```

**Frozen demo:** enable in sidebar to load `data/demo_frozen.json` without any keys.

## Files

| Path | Role |
|------|------|
| `config/sourcing_criteria.yaml` | Mandate + scoring weights + surface thresholds |
| `src/constants.py` | Region list, deal bounds |
| `src/cursor_prompts.py` | Markdown + JSON schema text for Cursor |
| `src/discovery.py` | Discovery: Anthropic + Cursor parse + prompt builder |
| `src/enrichment.py` | Enrichment: Anthropic + batch Cursor parse + Tavily |
| `src/json_utils.py` | Parse JSON from pasted chat |
| `src/export_pack.py` | Markdown IC pack |
| `src/workflow_merge.py` | Preserve workflow on re-import |
| `docs/USER_GUIDE.md` | Product documentation (TOC, parameters, flows) |
| `docs/images/` | Optional PNG screenshots for Documentation tab |
| `data/seed_targets.csv` | Example CSV |
| `data/demo_frozen.json` | Offline demo |

## Compliance

This is **triage**, not diligence. Do **not** use guessed personal emails for outreach. Human review before IC or external contact.

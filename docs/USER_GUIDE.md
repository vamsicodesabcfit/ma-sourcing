# ABC Fitness — M&A Proactive Sourcing User Guide

This document describes the **internal Streamlit application** for early M&A long-listing: discovery, enrichment, scoring, analyst workflow, and exports. It complements in-app labels and `config/sourcing_criteria.yaml`.

> **Interactive flowchart:** In the Streamlit app, open the **Documentation** tab — a **rendered pipeline diagram** appears at the top (Mermaid via the browser). Below is the same flow as **ASCII** for offline reading (GitHub, PDF export, etc.).

---

## Table of contents

1. [Overview](#1-overview)
2. [Why Discover, Enrich, and Workflow exist](#2-why-discover-enrich-and-workflow-exist)
3. [End-to-end flow](#3-end-to-end-flow)
4. [Sidebar parameters](#4-sidebar-parameters)
5. [Discover tab](#5-discover-tab)
6. [Enrich tab](#6-enrich-tab)
7. [Workflow tab](#7-workflow-tab)
8. [Export tab](#8-export-tab)
9. [Scoring and surface rules](#9-scoring-and-surface-rules)
10. [JSON contracts (Cursor / API)](#10-json-contracts-cursor--api)
11. [Documentation screenshots](#11-documentation-screenshots)
12. [Compliance and limitations](#12-compliance-and-limitations)
13. [Troubleshooting](#13-troubleshooting)

---

## 1. Overview

**Purpose:** Help Corp Dev build a **structured, comparable** list of acquisition targets (fitness / wellness / club-tech) with **evidence-backed** fields, **weighted fit scores**, and **analyst workflow**—without requiring paid databases for the first pass.

**Two analysis modes**

| Mode | When to use | What you do |
|------|-------------|-------------|
| **Cursor (paste JSON)** (default) | No `ANTHROPIC_API_KEY` | Generate a prompt → run in **Cursor** (with web) → paste JSON back. |
| **Anthropic API** | API key configured | Run discovery / enrichment inside the app via Claude. |

**Optional:** `TAVILY_API_KEY` pulls short web snippets into **enrichment** prompts (both modes).

---

## 2. Why Discover, Enrich, and Workflow exist

Corp dev teams rarely start with a clean spreadsheet of targets. They start with a **thesis** (“we want more B2B2C distribution in boutique fitness”) and then spend days in browsers and decks. This app splits that work into three deliberate steps:

### Discover — “Who might we even talk about?”

**Problem it solves:** You need a **repeatable long list** of company *names* aligned to geography, deal size, and strategy—not random Google results.

**What it does:** Takes your **mandate + regions + deal band** and produces a **structured list of candidates** (with websites, rough ownership/scale signals, rationale). Output is JSON you can re-run, diff, and share.

**Without this step:** You jump straight to deep research on a handful of names someone remembered, and you miss adjacencies (e.g. gym SaaS next to club operators).

### Enrich — “What do we know about each name, in comparable columns?”

**Problem it solves:** A list of names is not comparable. You need **firmographics** (HQ, employees, funding, CEO, etc.) and **fit scores** in one table for triage.

**What it does:** For each company, fills a **fixed schema** (headquarters, financing, revenue *notes*, scoring dimensions, evidence with URLs). That powers sorting, filtering, and exports.

**Without this step:** Everyone maintains their own notes; IC sees five different formats and no shared evidence trail.

### Workflow — “What did we decide, and what’s next?”

**Problem it solves:** Sourcing is iterative. You need **status**, **comments**, and **watchlists** without losing work when the browser refreshes.

**What it does:** Lets analysts mark rows **approved / rejected / deferred**, add comments, flag **watchlist**, and **save or restore** the whole session (candidates + enriched + sidebar scope) as JSON.

**Without this step:** Decisions live in Slack threads; you cannot reproduce what the team believed last Tuesday.

---

## 3. End-to-end flow

**ASCII view** (same pipeline as the diagram in the Streamlit Documentation tab):

```
  [ Sidebar: regions, deal band, provider, keys ]
                    |
                    v
  +----------+   +------------------+   +----------------+
  | Discover |-->| Paste candidates |-->| Enrich        |
  | (thesis)|   | JSON (or API)    |   | (firmographics|
  +----------+   +------------------+   | + scores)     |
                    |                    +--------+-------+
                    v                             |
             +-------------+                      v
             | Workflow    |<---------------------+
             | status/notes|
             +------+------+
                    |
                    v
             +-------------+
             | Export      |
             | MD + CSV    |
             +-------------+
```

**Figure reference:** Optional UI screenshots — [§11](#11-documentation-screenshots).

---

## 4. Sidebar parameters

| Control | Meaning | How it affects the product |
|--------|---------|----------------------------|
| **All regions (global)** | When checked, multiselect is disabled. | Prompts say **global** bias; allowed region codes in JSON include **all** supported regions (`US`, `EU`, `India`, `AUS`, `LATAM`, `Japan`). |
| **Regions (multi-select)** | One or more region codes. | **Target regions** and **Allowed region codes** in generated prompts match this list only. |
| **Deal size band** (slider, USD millions) | Min–max implied EV / check size. | Injected into prompts so research biases toward companies plausibly in band. Bounds from `src/constants.py` (e.g. **$10M–$600M** max). |
| **Provider** | Cursor vs Anthropic. | Chooses manual JSON workflow vs in-app API calls. |
| **Anthropic API key** | Optional secret. | Only if **Anthropic API** is selected. |
| **Tavily API key** | Optional. | When set + toggle on, enrichment prompts include **web snippets** for citations. |
| **Frozen demo dataset** | Loads canned JSON. | Skips live API; good for demos and training. |
| **Mandate (YAML excerpt)** | Read-only `sourcing_criteria.yaml`. | Sector preferences; **geography for the run** comes from sidebar regions. |

Changing **regions** or **deal band** clears cached Cursor prompts so you do not copy an outdated brief.

---

## 5. Discover tab

### Why it exists

See [§2](#2-why-discover-enrich-and-workflow-exist). Discover produces the **first structured artifact**: candidate names tied to your mandate.

### Inputs (with examples)

| Field | What it is | Example |
|-------|------------|---------|
| **Mandate / thesis** | Free-text strategy: geographies you care about *strategically*, channels (employers, insurers), product angles (SaaS, rollup), what to avoid. | *“Prioritize US + EU boutique operators and gym software with clear B2B2C path into clubs; avoid pure pharma. Tuck-in tech OK under $80M EV.”* |
| **Max discovery candidates** | Hard cap on how many names the model should return in one JSON response. | Set **15** for a weekly long-list; set **25** for a broader sweep (more noise, more review). |

**Example together:** Mandate as above + **Max 12** + regions **US, EU** + deal **$15M–$80M** tells Cursor/Claude to propose **up to 12** names biased to that story—not 50 random fitness apps.

### Cursor mode

1. Click **Generate discovery prompt for Cursor**.
2. Prompt panel: use **📋** (top-right) to copy, or **Download .md** if clipboard is blocked.
3. Paste returned JSON into **Paste discovery JSON here** → **Apply pasted discovery JSON**.

### Anthropic mode

- **Run discovery (Anthropic)** — fills the candidate table (requires key; demo uses frozen data).

### Outputs

- Candidate **table** (name, HQ, `regions_relevant`, website, rationale, etc.).
- **Suggested searches** (optional) from JSON for analysts to deepen manually.

---

## 6. Enrich tab

### Why it exists

See [§2](#2-why-discover-enrich-and-workflow-exist). Enrichment turns **names** into a **diligence-ready row** with evidence and scores.

### Source options (important)

| Source | When to use it | What it does |
|--------|----------------|--------------|
| **From discovery session** | You already ran **Discover** in this browser session. | Builds the enrichment list from **session candidates** (`company_name` + `website` from discovery JSON). No file upload. |
| **Upload CSV** | You have a list from elsewhere (banker, conference list, internal CRM export). | You upload a **CSV** file; each row becomes one company to enrich. **Does not** replace discovery output in session—you can use CSV even if discovery is empty. |

**CSV format (minimum):**

| company_name | website | notes |
|--------------|---------|-------|
| ExampleCo | https://example.com | Met at IHRSA; check franchisee count |
| OtherCo | | PE rumor — verify |

- **company_name** — required.  
- **website** — optional but improves research quality.  
- **notes** — optional; passed into the prompt as analyst hints (e.g. “competes with Mindbody”, “APAC expansion”).

**Example:** You export 8 names from an internal sheet → save as `targets.csv` with columns above → **Upload CSV** → **Generate enrichment prompt** → one batch JSON for all eight.

### Cursor mode

1. Non-empty company list (from session **or** CSV).
2. **Generate enrichment prompt for Cursor** → copy **📋** → paste JSON → **Apply pasted enrichment JSON**.

### Anthropic mode

- **Enrich all (Anthropic)** — one API call per company (slower for long lists).

### Outputs

- **Master table** + **Download master CSV**.

Re-importing enrichment **preserves** workflow fields when `company_name` matches.

---

## 7. Workflow tab

### Why it exists

See [§2](#2-why-discover-enrich-and-workflow-exist). This is your **system of record** for triage decisions inside the tool.

### Session backup (Download / Restore)

Streamlit keeps data in **browser session memory** until you refresh or close the tab. **Session backup** serializes everything important to one **JSON file**:

- `candidates` (discovery output)  
- `queries` (suggested searches)  
- `enriched` (full enriched objects including workflow fields)  
- `regions` and `deal_range` (sidebar scope at save time)

**Download session snapshot** — saves that JSON to disk for:

- **Handoff** to a teammate (“here is Tuesday’s book”).  
- **QA / audit** (“reproduce this exact state”).  
- **Checkpoint** before risky bulk paste operations.

**Restore session JSON** — loads a previously downloaded file back into the app (replaces current session lists). Use after a refresh or to merge work from another machine.

**Example:** Before you **Apply** a large enrichment paste, click **Download session snapshot** → filename `abc_ma_session.json`. If the paste breaks parsing, restore the JSON and try again.

### Editor controls

| Control | Meaning |
|---------|---------|
| **Show watchlisted only** | Filters the grid. |
| **workflow_status** | `draft`, `submitted`, `approved`, `rejected`, `deferred`. |
| **analyst_comment** | Free text (e.g. “needs legal on ToS”). |
| **watchlisted** | Short-list for weekly review. |
| **Save workflow changes to session** | Commits grid edits into memory. |

---

## 8. Export tab

Requires at least one **enriched** row.

| Export | Contents |
|--------|----------|
| **Download Markdown pack** | One section per company: HQ, financing, CEO, scores, diligence questions, red flags — suitable for email or attachment. |
| **Download full CSV** | Flat table for Excel / BI tools. |

---

## 9. Scoring and surface rules

### Where scores come from

During **Enrichment**, the model fills **seven dimensions** as numbers between **0** and **1** (plus evidence). Your `config/sourcing_criteria.yaml` lists **weights** for each dimension. The app computes:

**`total_score = Σ (weight_i × score_i)`**  
(sum over every key listed under `scoring_weights`).

**Example (illustrative numbers):**  
Suppose YAML contains:

```yaml
scoring_weights:
  strategic_fit_b2b2c_distribution: 0.22
  software_or_data_component: 0.18
  fragmented_category_roll_up_potential: 0.15
  founder_led_or_tuck_in_friendly: 0.12
  scale_upside_locations_or_seats: 0.13
  low_integration_complexity_vs_abc: 0.10
  evidence_quality: 0.10
```

For one company, imagine the model returns:

| Dimension key (YAML) | Model score | Weight | Contribution |
|------------------------|-------------|--------|----------------|
| strategic_fit_b2b2c_distribution | 0.80 | 0.22 | 0.176 |
| software_or_data_component | 0.90 | 0.18 | 0.162 |
| fragmented_category_roll_up_potential | 0.50 | 0.15 | 0.075 |
| founder_led_or_tuck_in_friendly | 0.40 | 0.12 | 0.048 |
| scale_upside_locations_or_seats | 0.70 | 0.13 | 0.091 |
| low_integration_complexity_vs_abc | 0.60 | 0.10 | 0.060 |
| evidence_quality | 0.55 | 0.10 | 0.055 |

**`total_score` = 0.667** (rounded in UI). Higher means stronger *fit to your weighted rubric*, not “better company” in absolute terms.

### What each dimension means (plain language)

| YAML key | What it captures | Example high score (1.0-ish) |
|----------|------------------|------------------------------|
| `strategic_fit_b2b2c_distribution` | Fit to paths where ABC touches members/employers/partners—not just “cool brand.” | B2B SaaS sold *through* clubs to members. |
| `software_or_data_component` | Product is partly **software, payments, data, APIs**. | Gym billing + scheduling platform. |
| `fragmented_category_roll_up_potential` | Many small operators → consolidation story. | Regional boutique franchise system. |
| `founder_led_or_tuck_in_friendly` | Smaller / founder-led / easier cultural fit. | Founder CEO, <50 employees, single geography. |
| `scale_upside_locations_or_seats` | Room to grow units, members, or seats. | 20 open studios + 40 sold but not built. |
| `low_integration_complexity_vs_abc` | Feels foldable into ABC without a multi-year war room. | Same tech stack assumptions as your clubs. |
| `evidence_quality` | Claims backed by URLs/quotes vs vague recall. | Three evidence items with press links. |

### Surface rule (“should we highlight this row?”)

**`surface`** is **True** only if **both**:

1. `total_score ≥ min_total_score` (default **0.35** in YAML `surface_rules`), and  
2. `evidence_quality ≥ min_evidence_quality` (default **0.25**).

**Example A — surfaces:** `total_score = 0.55`, `evidence_quality = 0.30` → **True** (both thresholds met).

**Example B — does not surface:** `total_score = 0.60`, `evidence_quality = 0.15` → **False** (evidence too weak—forces you to improve citations before treating as “high confidence”).

**Why two gates?** Prevents a model from scoring strategic fit aggressively on **vibes** without **sources**.

### Tuning weights (example)

If your current mandate favors **software tuck-ins**, raise `software_or_data_component` and optionally lower `fragmented_category_roll_up_potential`. If you only care about **rollup of physical locations**, do the opposite. **Always** keep weights as positive numbers; sums near **1.0** keep `total_score` interpretable on a ~0–1 scale.

---

## 10. JSON contracts (Cursor / API)

**Discovery response**

- Top-level: `candidates` (array), `search_queries_suggested` (array).
- Each candidate: `company_name`, `headquarters`, `regions_relevant` (subset of **allowed** region codes), `website`, etc.

**Enrichment response**

- Preferred: `{ "enriched_targets": [ { ... }, ... ] }`
- Alternative: a JSON **array** of company objects.

Firmographic fields include: `employee_count`, `last_financing_summary`, `last_financing_date`, `revenue_note`, `profitability_note`, `ceo_name`, `ceo_email` (null unless clearly public), `investors`, `year_founded`, `evidence` (claim + URL + quote).

---

## 11. Documentation screenshots

Place PNG files under `docs/images/` using the filenames in **`docs/images/README.md`**. The Streamlit **Documentation** tab displays each file that exists.

---

## 12. Compliance and limitations

- **Not diligence:** outputs are triage inputs; verify facts before IC or outreach.
- **CEO email:** do not invent; null unless published on a trustworthy source.
- **Revenue / profitability:** often `NA` for private companies; avoid false precision.
- **Third-party snippets** (Tavily) can be wrong or stale—cross-check.

---

## 13. Troubleshooting

| Issue | What to try |
|-------|-------------|
| Copy icon does nothing | Use **Download .md** or focus the prompt box and ⌘A / Ctrl+A, then copy. |
| Prompt still old after changing regions | Regenerate prompt (scope change clears cache). |
| JSON parse error | Ensure the model returned **only** JSON; strip to outermost `{...}` or `[...]`. |
| Empty enrichment from session | Run **Discover** first or use **Upload CSV**. |

---

## Related files

| Path | Role |
|------|------|
| `streamlit_app.py` | UI |
| `config/sourcing_criteria.yaml` | Mandate text, weights, surface thresholds |
| `src/constants.py` | Region list, deal bounds |
| `src/cursor_prompts.py` | Cursor markdown + schema text |
| `src/discovery.py` / `src/enrichment.py` | Prompt builders + parsers + optional API |

For setup and install, see the repository **README.md**.
